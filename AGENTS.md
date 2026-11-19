# Working on this repo

- The plugin is two Agent Skills in `skills/`. Keep each SKILL.md under 500 lines and put detail in `references/`.
- Frontmatter allows only name, description, license, compatibility, metadata and allowed-tools. `name` must match the folder.
- Keep `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and `skills/*/SKILL.md` versions in step.
- Python lives in `skills/onboarding-audit/scripts/onboarding_audit` and uses only the standard library.
- Any change under `skills/` or to a manifest needs a version bump in all five places, or installed users never see it. CI enforces this.
- Before a commit: `pytest -q` and `python -c "from skills_ref.cli import main; main()" validate skills/<name>` for each skill.
- Writing: no em dashes. Plain, short sentences.
- Examples use the fictional product Pipewell. Never commit real findings about a company you don't own.
