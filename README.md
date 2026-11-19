# Onboarding Audit

An agent plugin that signs up for your product as a brand-new user, once a month or whenever you ask, and reports where people get stuck. It runs each persona you define, from signup through activation, and checks the emails along the way. You get back a report with screenshots, measured waits, estimated hands-on time, and a prefilled ticket for each finding in GitHub, Linear or Jira.

Severity comes only from what happened in the run. A step that blocked the signup or sent something to the wrong person is High. A step that needed a workaround or showed an error is Medium. Extra effort and polish are Low. Numbers of affected users appear only when you supply your own data.

## What it will not do

It never types a password, one-time code or card number, and it never opens a verification link or approves an OAuth screen. Each of those is a handoff to you, and it is timed separately. It stops before payment unless you give it a discount link with a set amount. It never files a ticket itself: each button opens a prefilled ticket for you to review and submit. Only audit products you run or have written permission to test.

## Install

The skills follow the open [Agent Skills](https://agentskills.io) format, and the repo is packaged as a portable [Agent Plugin](https://agent-plugins.org), so the same folder works across tools.

| Tool | How |
|---|---|
| OpenAI Codex and ChatGPT | Add this repo as a plugin source. `plugin.json` holds the portable manifest, with Codex settings under `extensions.com.openai`, and `.agents/plugins/marketplace.json` lists it. |
| Claude Code | `/plugin marketplace add lexi-lowe/onboarding-audit`, then `/plugin install onboarding-audit@onboarding-audit` |
| Claude apps | Upload `skills/onboarding-audit` and `skills/onboarding-audit-setup` as skills, or add the repo as a plugin. |
| Any other Agent Skills client | Copy the two folders in `skills/` into the client's skills folder. |

## Use it

1. Say "set up an onboarding audit". The setup skill asks about your product, permission, activation goal, personas, test inbox, payment, tracker, delivery and report styling, then writes `onboarding-audit.config.json`.
2. Say "run an onboarding audit of my product". Schedule it monthly in whatever scheduler your tool offers.
3. Render the report from a run:

```sh
cd skills/onboarding-audit/scripts
python -m onboarding_audit render ../../../examples/audit-pipewell-2026-11.json \
  --config ../../../examples/config.pipewell-example.json --out ../../../out
```

This writes `report.html`, `email.html`, `slack.json`, `slack.txt`, `subject.txt` and `links.json`. Add `--dedupe` to mark findings already filed in your tracker, and `--send-slack` to post with `SLACK_WEBHOOK_URL`.

## Repo layout

```
plugin.json                      portable manifest (OpenAI settings under extensions.com.openai)
.agents/plugins/marketplace.json repo marketplace for Codex
.claude-plugin/                  Claude Code manifest and marketplace
skills/onboarding-audit/         the run: SKILL.md, references, scripts, tracker.js
skills/onboarding-audit-setup/   the owner interview that writes the config
examples/                        configs and sample runs (Pipewell is fictional)
tests/                           pytest suite
```

## Develop

```sh
pip install pytest skills-ref
pytest -q
python -c "from skills_ref.cli import main; main()" validate skills/onboarding-audit
```

## What it runs and sends

The skills drive a browser on the signup flow you name and read the test inbox you set up. The bundled Python renders the report locally and needs no network, with two opt-in exceptions. `--dedupe` reads your tracker's existing issues to avoid duplicates: GitHub's REST API (with `GITHUB_TOKEN` if the repo is private), Linear's API with `LINEAR_API_KEY`, or Jira's API with `JIRA_EMAIL` and `JIRA_API_TOKEN`. It only reads. `--send-slack` posts the summary to the webhook in `SLACK_WEBHOOK_URL`. Each credential goes only to its own service. The report's ticket buttons open a prefilled new-issue page in your tracker; nothing is filed until you submit it.

## Updates

Installed copies update only when the version number goes up. For each release, raise `version` in `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and both `SKILL.md` files, then merge to `main`. CI fails a pull request that changes the plugin without raising the version. For the ChatGPT and Codex directory, build a new ZIP with `python tools/package_codex.py` and upload it to the existing plugin; each upload is reviewed again. People who installed in Claude Code straight from this repo can turn on auto-update in `/plugin` under Marketplaces, or run `/plugin marketplace update onboarding-audit`.

## License

MIT
