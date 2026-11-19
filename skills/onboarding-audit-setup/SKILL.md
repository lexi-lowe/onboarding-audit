---
name: onboarding-audit-setup
description: Set up an onboarding audit by interviewing the owner and writing onboarding-audit.config.json, covering the product, permission, activation goal, personas, test inbox, payment rules, ticket tracker, delivery by email or Slack, optional taste preferences and report styling. Use the first time someone wants to audit a signup or onboarding flow, or when they want to change personas, tracker, delivery or schedule.
license: MIT
compatibility: Works in any agent that can write a file. Reading the product's colours for the report theme needs a browser.
metadata:
  author: Lexi Cardia
  version: "0.1.1"
---

# Set up an onboarding audit

Ask the owner the questions below, a few at a time, and write their answers to `onboarding-audit.config.json` in the working folder. The full format and an example are in [../onboarding-audit/references/config.md](../onboarding-audit/references/config.md). Keep every answer in the owner's words; don't fill gaps with guesses.

1. **Product and permission.** What's the product and the URL a new user starts at? Do they run it, or do they have written permission from the company? If neither, stop: the audit isn't allowed.
2. **Activation.** What moment means a new user got value? Name the step ("first sync completes", "order placed", "book previewed"). The audit measures time to this step.
3. **Personas.** Who should the audit sign up as? Each persona needs a short label, an email type (work or personal), a device (desktop or mobile) and any traits that change the path (has a data warehouse, is buying a gift). You may suggest two or three based on the product, but the owner decides. Write only the ones they approve. No personas is fine: the audit then runs one generic path.
4. **Test inbox.** Which address pattern should the audit use, and how can the agent read it? A catch-all on the owner's own domain works best, because some products quietly reject personal email addresses. Gmail plus-addresses work for products that accept them.
5. **Payment.** Should runs stop at the pay button, or use a discount link? If a link, what total should the agent expect to see before paying?
6. **Tracker.** Where do tickets go: GitHub (repo), Linear (team key, optional) or Jira (site, project ID, issue type ID)? Or none.
7. **Delivery.** Email (to which address) or Slack (incoming webhook stored in an environment variable, or a channel the agent can post to)?
8. **Taste, optional.** Any preferences screens should meet beyond working correctly, in their own words ("plain, calm copy: no exclamation marks")? These are reported separately and never outrank something that blocks a user.
9. **Report.** Is the report for the owner's own team, or for another company? For another company, set `report.tracker_notice` and `report.auditor`, and offer to read the product's colours and font for `theme` (never its logo).
10. **Schedule.** How often should it run? If the agent's platform supports scheduled tasks, create one; otherwise tell the owner how to run it.

Read the config back to the owner in plain words and fix anything they correct. Then offer a first run with them watching, before any schedule starts: handoffs (verification links, sign-in approvals) need them anyway.
