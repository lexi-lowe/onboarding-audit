import json
import subprocess
import sys
from pathlib import Path

from onboarding_audit.findings import Audit
from onboarding_audit.report import render_html

ROOT = Path(__file__).parent.parent
EX = ROOT / "examples"
SCRIPTS = ROOT / "skills" / "onboarding-audit" / "scripts"


def cfg(name="pipewell-example"):
    return json.loads((EX / f"config.{name}.json").read_text())


def test_owner_mode_has_buttons_and_no_notice():
    c = cfg()
    h = render_html(Audit.load(EX / "audit-pipewell-2026-11.json", c), c)
    assert h.count('class="file"') == 9 and 'id="connect"' not in h
    assert "How far each signup got" in h and "Against your taste preferences" in h
    assert h.index("Gmail signups") < h.index("Exclamation marks")       # high before taste
    assert "Not a publication of Pipewell" in h and "<script>" not in h


def test_notice_mode_for_a_shared_report():
    c = cfg(); c["report"] = {"tracker_notice": True, "auditor": "Lexi Cardia", "permission_note": "run with permission"}
    h = render_html(Audit.load(EX / "audit-pipewell-2026-11.json", c), c)
    assert 'id="connect"' in h and 'class="file"' not in h and "var FINDINGS=" in h and "AuditTracker" in h
    assert "Independent audit by Lexi Cardia" in h and "run with permission" in h


def test_filed_findings_link_to_issue():
    c = cfg(); a = Audit.load(EX / "audit-pipewell-2026-11.json", c)
    for r in a.runs:
        for f in r.findings:
            if f.key == "gmail-no-verification-email":
                f.filed = {"id": "GRO-7", "url": "https://example.atlassian.net/browse/GRO-7", "state": "open"}
    h = render_html(a, c)
    assert "Filed as GRO-7" in h and h.count('class="file"') == 8


def test_html_is_escaped():
    c = cfg(); a = Audit.load(EX / "audit-pipewell-2026-11.json", c)
    a.runs[0].findings[0].title = '<img src=x onerror=alert(1)>'
    assert "<img src=x" not in render_html(a, c)


def test_theme_override():
    c = cfg(); c["theme"] = {"accent": "#ff5500", "font": "Karla"}
    h = render_html(Audit.load(EX / "audit-pipewell-2026-11.json", c), c)
    assert "--accent:#ff5500" in h and "family=Karla" in h


def test_cli_end_to_end(tmp_path):
    r = subprocess.run([sys.executable, "-m", "onboarding_audit", "render", str(EX / "audit-pipewell-2026-11.json"),
                        "--config", str(EX / "config.pipewell-example.json"), "--out", str(tmp_path)],
                       cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for name in ("report.html", "email.html", "slack.json", "slack.txt", "subject.txt", "links.json"):
        assert (tmp_path / name).exists(), name
    assert "2 high, 2 medium, 3 low" in (tmp_path / "subject.txt").read_text()


def test_documented_examples_are_valid(tmp_path):
    import re
    doc = (ROOT / "skills" / "onboarding-audit" / "references" / "run-format.md").read_text()
    sample = json.loads(re.search(r"```json\n(.*?)\n```", doc, re.S).group(1))
    p = tmp_path / "a.json"; p.write_text(json.dumps(sample))
    a = Audit.load(p, json.loads((EX / "onboarding-audit.config.example.json").read_text()))
    assert a.merged()[0].severity == "Medium" and a.funnels()[0][1]["reached_activation"]
    cdoc = (ROOT / "skills" / "onboarding-audit" / "references" / "config.md").read_text()
    assert json.loads(re.search(r"```json\n(.*?)\n```", cdoc, re.S).group(1)) == json.loads((EX / "onboarding-audit.config.example.json").read_text())
