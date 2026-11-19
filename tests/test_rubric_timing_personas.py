import json
from pathlib import Path
import pytest

from onboarding_audit.rubric import rate, rubric_markdown, OBSERVED
from onboarding_audit.timing import Step, Funnel, fmt_duration, K, P, B, M, READ_SCREEN
from onboarding_audit.findings import Audit, Finding, Persona

EX = Path(__file__).parent.parent / "examples"


# ---------- rubric ----------

@pytest.mark.parametrize("observed,sev", [("blocked", "High"), ("wrong-recipient", "High"), ("workaround", "Medium"),
                                          ("error", "Medium"), ("extra-effort", "Low"), ("polish", "Low")])
def test_severity_comes_from_what_happened(observed, sev):
    assert rate(observed).severity == sev


def test_guessing_never_high():
    r = rate("blocked", confidence="Guessing")
    assert r.severity == "Medium" and any("verified" in n for n in r.notes)


def test_accessibility_low_unless_it_blocks():
    assert rate("error", category="accessibility").severity == "Low"
    assert rate("blocked", category="accessibility").severity == "High"


def test_taste_capped_at_medium():
    assert rate("blocked", category="taste").severity == "Medium"


@pytest.mark.parametrize("bad", [dict(observed="annoying"), dict(observed="polish", category="vibes")])
def test_rate_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        rate(**bad)


def test_rubric_doc_has_no_estimates():
    md = rubric_markdown()
    assert all(f"`{k}`" in md for k in OBSERVED) and "Never guessed" in md and "reach" not in md.lower()


# ---------- findings ----------

def test_finding_derives_severity_from_observed():
    f = Finding(key="x", confidence="Certain", title="t", steps="", expected="", actual="", observed="workaround")
    assert f.severity == "Medium"
    with pytest.raises(ValueError, match="observed"):
        Finding(key="y", confidence="Certain", title="t", steps="", expected="", actual="")


def test_affected_needs_a_source():
    ok = Finding(key="a", confidence="Certain", title="t", steps="", expected="", actual="", observed="blocked",
                 affected={"share": "38% of trials", "source": "Amplitude, Oct 2026"})
    assert ok.severity == "High"   # owner data is shown, never changes severity
    with pytest.raises(ValueError, match="source"):
        Finding(key="b", confidence="Certain", title="t", steps="", expected="", actual="", observed="blocked", affected={"share": "38%"})


def test_taste_finding_must_cite_a_preference():
    with pytest.raises(ValueError, match="preference"):
        Finding(key="z", confidence="Certain", title="t", steps="", expected="", actual="", observed="polish", category="taste")


# ---------- timing ----------

def test_effort_uses_klm_constants():
    s = Step(name="x", screens=1, clicks=2, fields=1, chars=10, choices=1)
    expected = READ_SCREEN + 2 * (M + P + B) + (M + P + B) + 10 * K + M
    assert s.effort_s == round(expected, 1)


def test_funnel_stops_at_first_block_and_reports_no_ttv():
    a = Audit.load(EX / "audit-pipewell-2026-11.json")
    by = {p.id: s for p, s in a.funnels()}
    assert by["personal-email"]["stopped_at"] == "Verify email"
    assert by["work-email"]["stopped_at"] == "Choose destination"
    assert by["work-email"]["time_to_value_s"] is None
    assert by["work-email"]["handoffs"] == 2
    assert by["work-email"]["system_wait_s"] == 50


def test_funnel_reaches_activation():
    f = Funnel(steps=[Step(name="a", clicks=1), Step(name="First sync", system_wait_s=120)], activation_step="First sync")
    s = f.summary()
    assert s["reached_activation"] and s["time_to_value_s"] == round(s["effort_s"] + 120, 1)


def test_bad_step_rejected():
    with pytest.raises(ValueError):
        Step(name="x", outcome="meh")
    with pytest.raises(ValueError):
        Step(name="x", clicks=-1)


@pytest.mark.parametrize("s,txt", [(9.4, "9 s"), (60, "1 min"), (125, "2 min 5 s"), (64800, "18 h 0 min"), (None, "not reached")])
def test_fmt_duration(s, txt):
    assert fmt_duration(s) == txt


# ---------- personas and merging ----------

def test_merge_keeps_worst_and_lists_personas(tmp_path):
    d = json.loads((EX / "audit-pipewell-2026-11.json").read_text())
    shared = {"key": "slow-page", "confidence": "Certain", "title": "Slow", "steps": "", "expected": "", "actual": ""}
    d["runs"][0]["findings"].append({**shared, "observed": "extra-effort"})
    d["runs"][1]["findings"].append({**shared, "observed": "error"})
    p = tmp_path / "a.json"; p.write_text(json.dumps(d))
    m = {f.key: f for f in Audit.load(p).merged()}
    assert m["slow-page"].severity == "Medium" and m["slow-page"].personas == ["personal-email", "work-email"]


def test_merged_order_high_first_taste_last():
    m = Audit.load(EX / "audit-pipewell-2026-11.json").merged()
    sev = [f.severity for f in m if f.category != "taste"]
    assert sev == sorted(sev, key=["High", "Medium", "Low"].index)
    assert [f.category for f in m][-2:] == ["taste", "taste"]


def test_counts_exclude_taste():
    c = Audit.load(EX / "audit-pipewell-2026-11.json").counts()
    assert c == {"High": 2, "Medium": 2, "Low": 3}


def test_taste_must_match_owner_list(tmp_path):
    d = json.loads((EX / "audit-pipewell-2026-11.json").read_text())
    d["taste"] = ["Something else"]
    p = tmp_path / "a.json"; p.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="taste list"):
        Audit.load(p)


def test_duplicate_persona_rejected(tmp_path):
    d = json.loads((EX / "audit-pipewell-2026-11.json").read_text())
    d["runs"][1]["persona"]["id"] = "personal-email"
    p = tmp_path / "a.json"; p.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="different persona"):
        Audit.load(p)


def test_single_run_file_still_loads():
    a = Audit.load(EX / "run-2026-11.json")
    assert len(a.runs) == 1 and len(a.merged()) == 7


def test_persona_validation():
    with pytest.raises(ValueError):
        Persona(id="Bad Id", label="x")
    with pytest.raises(ValueError):
        Persona(id="ok", label="x", device="tablet")


# ---------- personas come from the owner ----------

def test_persona_must_be_in_owner_config():
    cfg = json.loads((EX / "config.pipewell-example.json").read_text())
    a = Audit.load(EX / "audit-pipewell-2026-11.json", cfg)
    assert [r.persona.id for r in a.runs] == ["personal-email", "work-email"]
    cfg["personas"] = cfg["personas"][:1]
    with pytest.raises(ValueError, match="owner"):
        Audit.load(EX / "audit-pipewell-2026-11.json", cfg)


def test_no_owner_personas_means_generic_run(tmp_path):
    d = json.loads((EX / "run-2026-11.json").read_text())
    p = tmp_path / "r.json"; p.write_text(json.dumps(d))
    a = Audit.load(p, {"personas": []})
    assert a.runs[0].persona is None


def test_example_configs_ship_without_invented_personas():
    for name in ("github", "linear", "jira"):
        assert json.loads((EX / f"config.{name}.json").read_text())["personas"] == []


def test_taste_defaults_from_config():
    cfg = json.loads((EX / "config.pipewell-example.json").read_text())
    d = json.loads((EX / "audit-pipewell-2026-11.json").read_text())
    assert Audit.load(EX / "audit-pipewell-2026-11.json", cfg).taste == d["taste"]
