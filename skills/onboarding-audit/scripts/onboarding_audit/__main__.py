"""python -m onboarding_audit render AUDIT.json --config CONFIG.json --out DIR [--dedupe] [--send-slack]

Writes report.html, email.html, slack.json, slack.txt, subject.txt and links.json.
AUDIT.json holds one or more runs (one per persona); a single-run file also works.
"""
import argparse
import json
import os
from pathlib import Path

from .dedupe import mark_filed
from .findings import Audit
from .notify import email_html, post_slack_webhook, slack_blocks, slack_text, subject
from .report import render_html
from .trackers import file_url


def main():
    ap = argparse.ArgumentParser(prog="onboarding_audit")
    ap.add_argument("cmd", choices=["render", "rubric"])
    ap.add_argument("audit", nargs="?")
    ap.add_argument("--config")
    ap.add_argument("--out")
    ap.add_argument("--dedupe", action="store_true", help="check the tracker for already-filed findings (read only)")
    ap.add_argument("--send-slack", action="store_true", help="post the summary to the webhook in config.delivery.webhook_env")
    a = ap.parse_args()
    if a.cmd == "rubric":
        from .rubric import rubric_markdown
        print(rubric_markdown())
        return
    if not (a.audit and a.config and a.out):
        ap.error("render needs AUDIT, --config and --out")
    cfg = json.loads(Path(a.config).read_text())
    audit = Audit.load(a.audit, cfg)
    tracker = cfg.get("tracker")
    merged = audit.merged()
    note = mark_filed(merged, tracker) if (a.dedupe and tracker) else ""
    by_key = {f.key: f for f in merged}
    for r in audit.runs:                       # carry filed state onto each run's findings
        for f in r.findings:
            f.filed = by_key[f.key].filed
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text(render_html(audit, cfg, note))
    if tracker:
        (out / "links.json").write_text(json.dumps(
            [{"key": f.key, "url": file_url(f, audit.month, audit.report_url, tracker), "filed": f.filed} for f in audit.merged()], indent=1))
        (out / "email.html").write_text(email_html(audit, tracker, note))
        (out / "slack.json").write_text(json.dumps(slack_blocks(audit, tracker, note), indent=1))
        (out / "slack.txt").write_text(slack_text(audit, tracker, note))
    (out / "subject.txt").write_text(subject(audit))
    delivery = cfg.get("delivery", {"type": "email"})
    if a.send_slack:
        post_slack_webhook(os.environ[delivery.get("webhook_env", "SLACK_WEBHOOK_URL")], slack_blocks(audit, tracker, note))
    print(f"Wrote {out}: {subject(audit)}. {note}".strip())


if __name__ == "__main__":
    main()
