"""Prefilled "new issue" links for GitHub, Linear and Jira.

No API tokens: each link opens the tracker's own create page with fields filled in,
and the person reviews and submits. That keeps a human between the agent and the backlog.
"""
from __future__ import annotations

from urllib.parse import quote, urlencode

from .findings import Finding, key_line

MAX_URL = 2000  # safe across browsers, mail clients and Slack; GitHub allows more


def _q(params: list[tuple[str, str]]) -> str:
    return urlencode(params, quote_via=lambda s, *_: quote(s, safe=""))


# ---------- issue body, per markup ----------

def _sections(f: Finding, run_month: str, report_url: str, level: int) -> list[tuple[str, str]]:
    """level 0 = everything; higher levels drop detail to fit the URL limit."""
    link = f"{report_url}#{f.report_anchor}" if f.report_anchor else report_url
    s = [("Steps", f.steps), ("Expected", f.expected), ("Actual", f.actual)]
    if f.fix and level < 1:
        s.append(("Fix idea", f.fix))
    if level >= 2:
        s = [("Actual", f.actual)]
    if level >= 3:
        s = []
    return s, link


def markdown_body(f: Finding, run_month: str, report_url: str, level: int = 0, related: str = "") -> str:
    sections, link = _sections(f, run_month, report_url, level)
    out = [
        f"**Severity:** {f.severity} · **Confidence:** {f.confidence}",
        f"**Found by:** signup audit, {run_month} ([report with screenshot]({link}))",
    ]
    for name, text in sections:
        out += ["", f"**{name}**", text]
    if level >= 3:
        out += ["", "Details and screenshot are in the report."]
    if related:
        out += ["", f"Related: {related}"]
    out += ["", key_line(f.key)]
    return "\n".join(out)


def jira_body(f: Finding, run_month: str, report_url: str, level: int = 0) -> str:
    """Jira wiki markup. HTML comments would show as text, so the key is a footer line."""
    sections, link = _sections(f, run_month, report_url, level)
    out = [
        f"*Severity:* {f.severity} | *Confidence:* {f.confidence}",
        f"*Found by:* signup audit, {run_month} ([report with screenshot|{link}])",
    ]
    for name, text in sections:
        out += ["", f"*{name}*", text]
    if level >= 3:
        out += ["", "Details and screenshot are in the report."]
    out += ["", f"signup-audit-key: {f.key}"]
    return "\n".join(out)


def _fit(build) -> str:
    """Try full detail first, then shed sections until the URL fits."""
    for level in range(4):
        url = build(level)
        if len(url) <= MAX_URL:
            return url
    raise ValueError(f"URL still over {MAX_URL} chars after trimming; shorten the title")


# ---------- trackers ----------

def github_url(f: Finding, run_month: str, report_url: str, cfg: dict) -> str:
    """cfg: repo ("owner/name"), labels (list), related (optional, e.g. "#39")."""
    labels = ",".join(cfg.get("labels", ["bug", "signup-audit"]))

    def build(level):
        body = markdown_body(f, run_month, report_url, level, cfg.get("related", ""))
        return f"https://github.com/{cfg['repo']}/issues/new?" + _q(
            [("title", f"[Audit] {f.title}"), ("body", body), ("labels", labels)]
        )

    return _fit(build)


LINEAR_PRIORITY = {"High": "High", "Medium": "Medium", "Low": "Low"}


def linear_url(f: Finding, run_month: str, report_url: str, cfg: dict) -> str:
    """cfg: team (key like "ENG", optional), labels (list), project (optional)."""
    base = f"https://linear.app/team/{cfg['team']}/new" if cfg.get("team") else "https://linear.new"
    link = f"{report_url}#{f.report_anchor}" if f.report_anchor else report_url

    def build(level):
        params = [
            ("title", f"[Audit] {f.title}"),
            ("description", markdown_body(f, run_month, report_url, level, cfg.get("related", ""))),
            ("labels", ",".join(cfg.get("labels", ["Bug", "signup-audit"]))),
            ("priority", LINEAR_PRIORITY[f.severity]),
            ("links", f"{link}|Signup audit report"),
        ]
        if cfg.get("project"):
            params.append(("project", cfg["project"]))
        return base + "?" + _q(params)

    return _fit(build)


def jira_url(f: Finding, run_month: str, report_url: str, cfg: dict) -> str:
    """cfg: base_url (https://you.atlassian.net), project_id (numeric pid),
    issuetype_id (numeric), labels (list, no spaces).
    Uses CreateIssueDetails!init.jspa, the documented prefill route. Reliable on
    Jira Server/Data Center; Jira Cloud is retiring legacy create pages, so test there."""
    for k in ("base_url", "project_id", "issuetype_id"):
        if not cfg.get(k):
            raise ValueError(f"jira config needs {k}")
    labels = [l for l in cfg.get("labels", ["signup-audit"]) if " " not in l]
    base = cfg["base_url"].rstrip("/") + "/secure/CreateIssueDetails!init.jspa?"

    def build(level):
        params = [
            ("pid", str(cfg["project_id"])),
            ("issuetype", str(cfg["issuetype_id"])),
            ("summary", f"[Audit] {f.title}"),
            ("description", jira_body(f, run_month, report_url, level)),
        ] + [("labels", l) for l in labels]
        return base + _q(params)

    return _fit(build)


BUILDERS = {"github": github_url, "linear": linear_url, "jira": jira_url}
NAMES = {"github": "GitHub", "linear": "Linear", "jira": "Jira"}


def file_url(f: Finding, run_month: str, report_url: str, tracker: dict) -> str:
    kind = tracker["type"]
    if kind not in BUILDERS:
        raise ValueError(f"tracker type must be one of {list(BUILDERS)}")
    return BUILDERS[kind](f, run_month, report_url, tracker)


def button_label(tracker: dict) -> str:
    return f"File in {NAMES[tracker['type']]}"
