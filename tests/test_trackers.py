import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import pytest

from onboarding_audit.findings import Run, Finding, extract_key
from onboarding_audit import trackers
from onboarding_audit.trackers import github_url, linear_url, jira_url, MAX_URL

EX = Path(__file__).parent.parent / "examples"
RUN = Run.load(EX / "run-2026-11.json")
GH = json.loads((EX / "config.github.json").read_text())["tracker"]
LN = json.loads((EX / "config.linear.json").read_text())["tracker"]
JR = json.loads((EX / "config.jira.json").read_text())["tracker"]


def q(url):
    p = urlsplit(url)
    return p, parse_qs(p.query, keep_blank_values=True)


@pytest.mark.parametrize("f", RUN.findings, ids=lambda f: f.key)
def test_github_roundtrip(f):
    url = github_url(f, RUN.month, RUN.report_url, GH)
    p, qs = q(url)
    assert (p.scheme, p.netloc, p.path) == ("https", "github.com", "/lexi-lowe/bigroots/issues/new")
    assert qs["title"] == [f"[Audit] {f.title}"]
    assert qs["labels"] == ["bug,signup-audit"]
    body = qs["body"][0]
    assert f.actual in body and "Related: #39" in body
    assert extract_key(body) == f.key
    assert f"{RUN.report_url}#{f.report_anchor}" in body
    assert len(url) <= MAX_URL


@pytest.mark.parametrize("f", RUN.findings, ids=lambda f: f.key)
def test_linear_roundtrip(f):
    url = linear_url(f, RUN.month, RUN.report_url, LN)
    p, qs = q(url)
    assert (p.netloc, p.path) == ("linear.app", "/team/ENG/new")
    assert qs["title"] == [f"[Audit] {f.title}"]
    assert qs["labels"] == ["Bug,signup-audit"]
    assert qs["priority"] == [f.severity]            # Linear takes High/Medium/Low
    link, label = qs["links"][0].split("|")
    assert link == f"{RUN.report_url}#{f.report_anchor}" and label == "Signup audit report"
    assert extract_key(qs["description"][0]) == f.key
    assert len(url) <= MAX_URL


def test_linear_without_team_uses_linear_new():
    p, _ = q(linear_url(RUN.findings[0], RUN.month, RUN.report_url, {"type": "linear"}))
    assert (p.netloc, p.path) == ("linear.new", "")


@pytest.mark.parametrize("f", RUN.findings, ids=lambda f: f.key)
def test_jira_roundtrip(f):
    url = jira_url(f, RUN.month, RUN.report_url, JR)
    p, qs = q(url)
    assert p.path == "/secure/CreateIssueDetails!init.jspa"
    assert qs["pid"] == ["10000"] and qs["issuetype"] == ["10004"]
    assert qs["summary"] == [f"[Audit] {f.title}"]
    assert qs["labels"] == ["signup-audit"]
    desc = qs["description"][0]
    assert "<!--" not in desc                         # Jira would show HTML comments as text
    assert f"[report with screenshot|{RUN.report_url}#{f.report_anchor}]" in desc
    assert extract_key(desc) == f.key
    assert len(url) <= MAX_URL


def test_jira_requires_ids():
    with pytest.raises(ValueError, match="project_id"):
        jira_url(RUN.findings[0], RUN.month, RUN.report_url, {"type": "jira", "base_url": "https://x.atlassian.net"})


def test_jira_drops_labels_with_spaces():
    cfg = {**JR, "labels": ["signup-audit", "has space"]}
    _, qs = q(jira_url(RUN.findings[0], RUN.month, RUN.report_url, cfg))
    assert qs["labels"] == ["signup-audit"]


@pytest.mark.parametrize("build,cfg", [(github_url, GH), (linear_url, LN), (jira_url, JR)])
def test_long_finding_is_trimmed_not_broken(build, cfg):
    long = Finding(key="very-long", severity="High", confidence="Likely", title="Checkout loops",
                   steps="Click pay. " * 120, expected="Order placed. " * 60, actual="It loops. " * 60, fix="Fix it. " * 60,
                   report_anchor="finding-9")
    url = build(long, RUN.month, RUN.report_url, cfg)
    assert len(url) <= MAX_URL
    _, qs = q(url)
    text = (qs.get("body") or qs.get("description"))[0]
    assert "report" in text and extract_key(text) == "very-long"


def test_special_characters_survive():
    f = Finding(key="amp-test", severity="Low", confidence="Certain", title='Price shows "$58 & up" #1 + 50% <off>',
                steps="a&b=c?d#e", expected="ü é 漢字", actual="line1\nline2", report_anchor="finding-1")
    for build, cfg, field in [(github_url, GH, "body"), (linear_url, LN, "description"), (jira_url, JR, "description")]:
        _, qs = q(build(f, RUN.month, RUN.report_url, cfg))
        assert qs.get("title", qs.get("summary"))[0] == f"[Audit] {f.title}"
        assert "a&b=c?d#e" in qs[field][0] and "漢字" in qs[field][0] and "line1\nline2" in qs[field][0]


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        Finding(key="Bad Key", severity="High", confidence="Certain", title="t", steps="", expected="", actual="")
    with pytest.raises(ValueError):
        Finding(key="ok", severity="Critical", confidence="Certain", title="t", steps="", expected="", actual="")
    with pytest.raises(ValueError, match="tracker type"):
        trackers.file_url(RUN.findings[0], RUN.month, RUN.report_url, {"type": "asana"})
