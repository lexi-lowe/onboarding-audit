import copy
import json
from pathlib import Path

from onboarding_audit.findings import Run
from onboarding_audit.dedupe import mark_filed
from onboarding_audit.notify import slack_blocks, slack_text, email_html, subject

EX = Path(__file__).parent.parent / "examples"
GH = json.loads((EX / "config.github.json").read_text())["tracker"]
LN = json.loads((EX / "config.linear.json").read_text())["tracker"]
JR = json.loads((EX / "config.jira.json").read_text())["tracker"]


def run():
    return Run.load(EX / "run-2026-11.json")


# ---------- dedupe ----------

def gh_fixture(url, headers, body):
    assert "labels=signup-audit" in url and body is None
    return [
        {"number": 50, "state": "open", "html_url": "https://github.com/lexi-lowe/bigroots/issues/50",
         "body": "x\n<!-- signup-audit-key: gift-forme-carryover -->"},
        {"number": 51, "state": "closed", "html_url": "https://github.com/lexi-lowe/bigroots/issues/51",
         "body": "<!-- signup-audit-key: page-count-mismatch -->"},
        {"number": 52, "state": "open", "html_url": "...", "pull_request": {}, "body": "<!-- signup-audit-key: forme-gift-copy -->"},
        {"number": 53, "state": "open", "html_url": "...", "body": "filed by hand, no key"},
    ]


def test_github_dedupe_marks_open_and_returned():
    r = run()
    note = mark_filed(r.findings, GH, gh_fixture)
    by = {f.key: f.filed for f in r.findings}
    assert by["gift-forme-carryover"]["id"] == "#50" and not by["gift-forme-carryover"].get("returned")
    assert by["page-count-mismatch"]["returned"] is True
    assert by["forme-gift-copy"] is None          # pull requests are ignored
    assert note == "Duplicate check: 1 already filed, 1 came back after being closed, 5 new."


def test_linear_dedupe_parses_graphql():
    def fx(url, headers, body):
        assert url == "https://api.linear.app/graphql" and b"signup-audit" in body
        return {"data": {"issues": {"nodes": [
            {"identifier": "ENG-12", "url": "https://linear.app/x/issue/ENG-12", "description": "<!-- signup-audit-key: mobile-pay-before-preview -->", "state": {"type": "started"}},
            {"identifier": "ENG-9", "url": "https://linear.app/x/issue/ENG-9", "description": "<!-- signup-audit-key: gift-never-built -->", "state": {"type": "canceled"}},
        ]}}}
    r = run()
    mark_filed(r.findings, LN, fx)
    by = {f.key: f.filed for f in r.findings}
    assert by["mobile-pay-before-preview"]["id"] == "ENG-12"
    assert by["gift-never-built"]["returned"] is True


def test_jira_dedupe_reads_cloud_rich_text():
    adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "signup-audit-key: gift-date-no-default"}]}]}
    def fx(url, headers, body):
        assert url.endswith("/rest/api/3/search/jql") and headers["Authorization"].startswith("Basic ")
        return {"issues": [{"key": "BR-7", "fields": {"description": adf, "status": {"statusCategory": {"key": "indeterminate"}}}}]}
    r = run()
    mark_filed(r.findings, JR, fx)
    f = next(f for f in r.findings if f.key == "gift-date-no-default")
    assert f.filed == {"id": "BR-7", "url": "https://your-site.atlassian.net/browse/BR-7", "state": "open"}


def test_dedupe_failure_keeps_buttons():
    def boom(*a):
        raise OSError("no network")
    r = run()
    note = mark_filed(r.findings, GH, boom)
    assert "skipped" in note and all(f.filed is None for f in r.findings)


# ---------- delivery ----------

def test_slack_blocks_shape_and_limits():
    r = run()
    mark_filed(r.findings, GH, gh_fixture)
    p = slack_blocks(r, GH, "Duplicate check: 1 already filed.")
    assert p["text"] == subject(r)                   # notification fallback
    assert len(p["blocks"]) <= 50
    secs = [b for b in p["blocks"] if b["type"] == "section"]
    assert all(len(b["text"]["text"]) <= 3000 for b in secs)
    first = secs[0]["text"]["text"]
    assert "Already filed #50" in first and "File in GitHub" not in first
    returned = next(b["text"]["text"] for b in secs if "Two page counts" in b["text"]["text"])
    assert "came back after #51" in returned and "<https://github.com/lexi-lowe/bigroots/issues/new?" in returned
    assert p["blocks"][0]["type"] == "header" and len(p["blocks"][0]["text"]["text"]) <= 150


def test_slack_escapes_titles_but_not_links():
    r = run()
    r.findings[0].title = "A <b> & B"
    t = slack_text(r, LN)
    assert "A &lt;b&gt; &amp; B" in t and "<https://linear.app/team/ENG/new?" in t and "|File in Linear>" in t


def test_slack_caps_many_findings():
    r = run()
    r.findings = [copy.deepcopy(r.findings[0]) for _ in range(80)]
    assert len(slack_blocks(r, JR)["blocks"]) <= 50


def test_email_has_one_button_per_unfiled_finding():
    r = run()
    mark_filed(r.findings, GH, gh_fixture)
    h = email_html(r, GH)
    assert h.count(">File in GitHub<") == 6 and "Already filed #50" in h


def test_email_button_label_follows_tracker():
    assert ">File in Jira<" in email_html(run(), JR) and ">File in Linear<" in email_html(run(), LN)
