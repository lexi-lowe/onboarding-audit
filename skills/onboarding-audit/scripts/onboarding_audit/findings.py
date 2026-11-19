"""Findings, personas and runs.

One audit = one product, one month, one or more runs. Each run follows one persona
(a kind of new user) through signup to activation. Findings from all runs are merged
by key, so a problem several personas hit appears once, listing who hit it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .rubric import CATEGORIES, rate
from .timing import Funnel, Step

SEVERITIES = ("High", "Medium", "Low")
CONFIDENCES = ("Certain", "Likely", "Guessing")
_KEY = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Finding:
    key: str            # stable kebab-case id, reused month to month for dedupe
    confidence: str     # Certain | Likely | Guessing
    title: str
    steps: str
    expected: str
    actual: str
    severity: str = ""  # derived from `observed` when given
    fix: str = ""
    observed: str = ""            # what happened in the run, see rubric.OBSERVED
    affected: dict | None = None  # owner-supplied only: {"share": "38% of trials", "source": "Amplitude, Oct 2026"}
    category: str = "friction"    # friction | accessibility | taste
    preference: str = ""          # taste findings: the owner's preference it goes against
    personas: list[str] = field(default_factory=list)
    screenshot: str = ""          # path relative to the report, e.g. "shots/03-verify.jpg"
    caption: str = ""
    report_anchor: str = ""       # e.g. "finding-1"
    filed: dict | None = None     # {"id": "#42", "url": "...", "state": "open"}
    score_notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.confidence not in CONFIDENCES:
            raise ValueError(f"confidence must be one of {CONFIDENCES}: {self.confidence!r}")
        if not _KEY.match(self.key or ""):
            raise ValueError(f"key must be kebab-case: {self.key!r}")
        if self.category not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}: {self.category!r}")
        if self.category == "taste" and not self.preference:
            raise ValueError(f"taste finding {self.key!r} must name the preference it goes against")
        if self.observed:
            r = rate(self.observed, category=self.category, confidence=self.confidence)
            self.severity, self.score_notes = r.severity, list(r.notes)
        if self.affected is not None and not (self.affected.get("share") and self.affected.get("source")):
            raise ValueError(f"{self.key}: affected needs both a share and its source")
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.key}: give what was observed, or a severity of {SEVERITIES}")


@dataclass
class Persona:
    id: str
    label: str
    email: str = "work"        # work | personal
    device: str = "desktop"    # desktop | mobile
    goal: str = ""
    traits: dict = field(default_factory=dict)  # e.g. {"has_warehouse": false}

    def __post_init__(self):
        if not _KEY.match(self.id):
            raise ValueError(f"persona id must be kebab-case: {self.id!r}")
        if self.email not in ("work", "personal"):
            raise ValueError("persona email must be work or personal")
        if self.device not in ("desktop", "mobile"):
            raise ValueError("persona device must be desktop or mobile")


@dataclass
class Run:
    product: str
    month: str          # "Nov 2026"
    report_url: str
    findings: list[Finding]
    persona: Persona | None = None
    funnel: Funnel | None = None

    @classmethod
    def from_dict(cls, data: dict, product=None, month=None, report_url=None) -> "Run":
        funnel = None
        if data.get("funnel"):
            fd = data["funnel"]
            funnel = Funnel(steps=[Step(**s) for s in fd.get("steps", [])], activation_step=fd.get("activation_step"))
        return cls(
            product=data.get("product", product),
            month=data.get("month", month),
            report_url=data.get("report_url", report_url),
            findings=[Finding(**f) for f in data.get("findings", [])],
            persona=Persona(**data["persona"]) if data.get("persona") else None,
            funnel=funnel,
        )

    @classmethod
    def load(cls, path: str | Path) -> "Run":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def counts(self) -> dict[str, int]:
        return {s: sum(f.severity == s for f in self.findings if f.category != "taste") for s in SEVERITIES}


SEV_ORDER = {"High": 0, "Medium": 1, "Low": 2}


@dataclass
class Audit:
    """Several runs of the same product in the same month, one per persona."""
    product: str
    month: str
    report_url: str
    runs: list[Run]
    taste: list[str] = field(default_factory=list)   # owner's optional taste preferences
    summary: str = ""                                # the agent's plain-text summary of the whole audit
    worked: list[str] = field(default_factory=list)  # what worked well
    notes: list[list[str]] = field(default_factory=list)  # run notes: [item, note]

    @classmethod
    def load(cls, path: str | Path, config: dict | None = None) -> "Audit":
        """config: the owner's config. When given, every run's persona must be one the owner listed."""
        data = json.loads(Path(path).read_text())
        if "runs" not in data:   # a single-run file still works
            data = {**data, "runs": [data]}
        runs = [Run.from_dict(r, data["product"], data["month"], data["report_url"]) for r in data["runs"]]
        ids = [r.persona.id for r in runs if r.persona]
        if len(ids) != len(set(ids)):
            raise ValueError("each run needs a different persona id")
        if config is not None:
            allowed = {p["id"] for p in config.get("personas", [])}
            for r in runs:
                if r.persona and r.persona.id not in allowed:
                    raise ValueError(f"persona {r.persona.id!r} isn't in the owner's config; personas come only from the owner")
                if not r.persona and allowed:
                    raise ValueError("the owner listed personas, so every run must name one")
            data.setdefault("taste", config.get("taste", []))
        audit = cls(data["product"], data["month"], data["report_url"], runs, data.get("taste", []),
                    data.get("summary", ""), data.get("worked", []), data.get("notes", []))
        prefs = set(audit.taste)
        for r in runs:
            for f in r.findings:
                if f.category == "taste" and f.preference not in prefs:
                    raise ValueError(f"taste finding {f.key!r} cites a preference that isn't in the taste list")
        return audit

    def merged(self) -> list[Finding]:
        """One finding per key across runs, keeping the worst severity and listing every persona that hit it."""
        by_key: dict[str, Finding] = {}
        for r in self.runs:
            pid = r.persona.id if r.persona else ""
            for f in r.findings:
                cur = by_key.get(f.key)
                if cur is None:
                    cur = by_key[f.key] = Finding(**{**f.__dict__, "personas": list(f.personas)})
                elif SEV_ORDER[f.severity] < SEV_ORDER[cur.severity]:
                    keep = cur.personas
                    cur = by_key[f.key] = Finding(**{**f.__dict__, "personas": keep})
                if pid and pid not in cur.personas:
                    cur.personas.append(pid)
        return sorted(by_key.values(), key=lambda f: (f.category == "taste", SEV_ORDER[f.severity], f.key))

    def counts(self) -> dict[str, int]:
        m = [f for f in self.merged() if f.category != "taste"]
        return {s: sum(f.severity == s for f in m) for s in SEVERITIES}

    def funnels(self) -> list[tuple[Persona | None, dict]]:
        return [(r.persona, r.funnel.summary()) for r in self.runs if r.funnel]


KEY_MARKER = "signup-audit-key"


def key_line(key: str) -> str:
    """Hidden marker the next run searches for. HTML comments are invisible in GitHub
    and Linear Markdown. Jira shows them as text, so Jira gets a plain footer line."""
    return f"<!-- {KEY_MARKER}: {key} -->"


def extract_key(body: str) -> str | None:
    m = re.search(KEY_MARKER + r":\s*([a-z0-9-]+)", body or "")
    return m.group(1) if m else None
