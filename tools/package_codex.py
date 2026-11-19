"""Build the ZIP for the ChatGPT and Codex plugin directory: one top-level folder with only the plugin files."""
import json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["plugin.json", ".codex-plugin/plugin.json", "assets", "skills", "README.md", "LICENSE"]
SKIP = {"__pycache__", ".pytest_cache", ".DS_Store"}


def main():
    version = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"]
    out = ROOT / "dist" / f"onboarding-audit-{version}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            p = ROOT / item
            files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
            for f in files:
                if not SKIP.intersection(f.relative_to(ROOT).parts):
                    z.write(f, "onboarding-audit/" + str(f.relative_to(ROOT)))
    print(out)


if __name__ == "__main__":
    main()
