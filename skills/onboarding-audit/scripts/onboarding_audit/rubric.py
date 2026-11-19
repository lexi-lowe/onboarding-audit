"""Severity comes from what actually happened in the run, never from an estimate.

Every level is something the run can show with a screenshot:

  High    blocked           the run could not go further on that path
          wrong-recipient   data, money or an email went to the wrong person
  Medium  workaround        the run only continued after a workaround
          error             the run hit an error and had to recover
  Low     extra-effort      it cost extra steps, fields or decisions; nothing broke
          polish            copy, consistency or visual issues; nothing broke

How many users a problem affects is never guessed. The report lists which of the
owner's personas hit it. If the owner supplies real numbers (with a source), they
are shown next to the finding and do not change its severity.

Rules on top:
  - A finding tagged Guessing can't be High until it's checked.
  - Accessibility findings are Low unless they block someone (then use blocked).
  - Taste findings come only from the owner's taste preferences, are capped at
    Medium, and are reported in their own section.
"""
from __future__ import annotations

from dataclasses import dataclass

OBSERVED = {
    "blocked": ("High", "The run could not go further on that path"),
    "wrong-recipient": ("High", "Data, money or an email went to the wrong person"),
    "workaround": ("Medium", "The run only continued after a workaround"),
    "error": ("Medium", "The run hit an error and had to recover"),
    "extra-effort": ("Low", "Extra steps, fields or decisions; nothing broke"),
    "polish": ("Low", "Copy, consistency or visual issue; nothing broke"),
}

CATEGORIES = ("friction", "accessibility", "taste")


@dataclass(frozen=True)
class Rating:
    observed: str
    severity: str
    notes: tuple[str, ...]


def rate(observed: str, *, category: str = "friction", confidence: str = "Certain") -> Rating:
    if observed not in OBSERVED:
        raise ValueError(f"observed must be one of {list(OBSERVED)}: {observed!r}")
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}: {category!r}")
    severity = OBSERVED[observed][0]
    notes = []
    if category == "accessibility" and observed != "blocked" and severity != "Low":
        severity = "Low"
        notes.append("accessibility issue that didn't block anyone: Low")
    if category == "taste" and severity == "High":
        severity = "Medium"
        notes.append("taste preference: capped at Medium")
    if confidence == "Guessing" and severity == "High":
        severity = "Medium"
        notes.append("not yet verified: capped at Medium until checked")
    return Rating(observed, severity, tuple(notes))


def rubric_markdown() -> str:
    lines = ["# Severity rubric", "",
             "Severity comes from what happened in the run, never from an estimate. Each level is something a screenshot can show.", "",
             "| Severity | What happened | Code |", "| --- | --- | --- |"]
    lines += [f"| {sev} | {desc} | `{code}` |" for code, (sev, desc) in OBSERVED.items()]
    lines += ["", "## How many users are affected", "",
              "Never guessed. Each finding lists which of the owner's personas hit it. If the owner supplies real numbers with a source, the report shows them next to the finding; they don't change the severity.",
              "", "## Rules", "",
              "- A finding tagged Guessing can't be High until it's checked.",
              "- Accessibility findings are Low unless they block someone.",
              "- Taste findings come only from the owner's taste preferences, are capped at Medium, and are reported separately.",
              "- Confidence is shown on every finding: Certain (seen), Likely (strong inference), Guessing (filling a gap).",
              "", "## Personas", "",
              "Personas come only from the owner's config. A run can't use a persona that isn't listed there. With no personas, the audit runs one generic new-user path and the report says so."]
    return "\n".join(lines) + "\n"
