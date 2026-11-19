"""Every manifest and skill must carry the same version, or installed users won't get updates."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def versions():
    out = {
        "plugin.json": json.loads((ROOT / "plugin.json").read_text())["version"],
        ".claude-plugin/plugin.json": json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"],
    }
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        m = re.search(r'^\s+version:\s*"?([^"\n]+)"?\s*$', skill.read_text(), re.M)
        out[str(skill.relative_to(ROOT))] = m.group(1) if m else None
    return out


def test_versions_match():
    v = versions()
    assert len(set(v.values())) == 1, f"Versions differ: {v}"
