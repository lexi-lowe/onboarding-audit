"""Deliver the run summary by email or Slack. Same content, two formats.

Slack uses link text, not Block Kit buttons: URL buttons from a plain incoming
webhook make Slack expect an interactivity endpoint, and without one users can
see an error badge after clicking. Links open cleanly everywhere.
"""
from __future__ import annotations

import html
import json
import urllib.request

from .findings import Run
from .trackers import button_label, file_url

SEV_COLOR = {"High": "#b4442f", "Medium": "#b8862c", "Low": "#6b7f70"}
SEV_EMOJI = {"High": ":red_circle:", "Medium": ":large_orange_circle:", "Low": ":white_circle:"}


def _findings(run):
    """An Audit merges its runs; a single Run lists its own findings. Taste findings go last."""
    fs = run.merged() if hasattr(run, "merged") else run.findings
    return [f for f in fs if f.category != "taste"] + [f for f in fs if f.category == "taste"]


def subject(run: Run) -> str:
    c = run.counts()
    return f"{run.product} signup audit, {run.month}: {c['High']} high, {c['Medium']} medium, {c['Low']} low"


def _action(f, run: Run, tracker: dict) -> tuple[str, str, str]:
    """(kind, label, url): kind is 'file' or 'filed'."""
    if f.filed and not f.filed.get("returned"):
        return "filed", f"Already filed {f.filed['id']}", f.filed["url"]
    label = button_label(tracker)
    return "file", label, file_url(f, run.month, run.report_url, tracker)


# ---------- email ----------

def email_html(run: Run, tracker: dict, note: str = "") -> str:
    rows = []
    for f in _findings(run):
        kind, label, url = _action(f, run, tracker)
        came_back = f' <span style="color:#b4442f;font-size:12px">came back after {html.escape(f.filed["id"])} was closed</span>' if f.filed and f.filed.get("returned") else ""
        if kind == "file":
            act = (f'<a href="{html.escape(url)}" style="display:inline-block;background-color:#2f4a35;color:#ffffff;'
                   f'text-decoration:none;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;padding:7px 12px;border-radius:6px">{html.escape(label)}</a>')
        else:
            act = f'<a href="{html.escape(url)}" style="font-family:Arial,sans-serif;font-size:13px;color:#2f4a35">{html.escape(label)}</a>'
        rows.append(
            '<tr><td style="padding:10px 0;border-bottom:1px solid #e2dccb;font-family:Arial,sans-serif;font-size:14px;color:#1f2b22">'
            f'<span style="background:{SEV_COLOR[f.severity]};color:#ffffff;font-size:11px;font-weight:bold;padding:2px 8px;border-radius:10px">{f.severity.upper()}</span> '
            f'{html.escape(f.title)}{came_back}</td>'
            f'<td style="padding:10px 0 10px 12px;border-bottom:1px solid #e2dccb;text-align:right;white-space:nowrap">{act}</td></tr>'
        )
    p = 'style="font-family:Arial,sans-serif;font-size:14px;color:#1f2b22"'
    return (
        f'<p {p}>Each button opens a prefilled issue. Review it, then submit.</p>'
        f'<table cellpadding="0" cellspacing="0" style="width:100%;max-width:640px;border-collapse:collapse">{"".join(rows)}</table>'
        + (f'<p {p}>{html.escape(note)}</p>' if note else "")
        + f'<p {p}><a href="{html.escape(run.report_url)}">Full report with screenshots</a></p>'
    )


# ---------- slack ----------

def _esc(s: str) -> str:
    # Slack mrkdwn needs only &, <, > escaped
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slack_line(f, run: Run, tracker: dict) -> str:
    kind, label, url = _action(f, run, tracker)
    tail = f"<{url}|{label}>" if kind == "file" else f"_<{url}|{label}>_"
    back = f" _(came back after {f.filed['id']} was closed)_" if f.filed and f.filed.get("returned") else ""
    return f"{SEV_EMOJI[f.severity]} *{f.severity}:* {_esc(f.title)}{back}\n{tail}"


def slack_blocks(run: Run, tracker: dict, note: str = "") -> dict:
    """Payload for an incoming webhook (chat.postMessage takes the same blocks)."""
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{run.product} signup audit, {run.month}"[:150]}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": _esc(subject(run).split(": ", 1)[1])}]},
    ]
    for f in _findings(run):
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": _slack_line(f, run, tracker)[:3000]}})
    tail = (_esc(note) + "\n" if note else "") + f"<{run.report_url}|Full report with screenshots>"
    blocks += [{"type": "divider"}, {"type": "section", "text": {"type": "mrkdwn", "text": tail}}]
    if len(blocks) > 50:  # Slack's per-message limit
        blocks = blocks[:48] + [{"type": "section", "text": {"type": "mrkdwn", "text": f"More in the <{run.report_url}|report>."}}] + blocks[-1:]
    return {"text": subject(run), "blocks": blocks, "unfurl_links": False}


def slack_text(run: Run, tracker: dict, note: str = "") -> str:
    """Plain mrkdwn for posting through a Slack connector that takes a text message."""
    lines = [f"*{_esc(subject(run))}*", ""]
    lines += [_slack_line(f, run, tracker) for f in _findings(run)]
    if note:
        lines += ["", _esc(note)]
    lines += ["", f"<{run.report_url}|Full report with screenshots>"]
    return "\n".join(lines)


def post_slack_webhook(webhook_url: str, payload: dict) -> None:
    req = urllib.request.Request(webhook_url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        if r.read().decode().strip() != "ok":
            raise RuntimeError("Slack webhook did not return ok")
