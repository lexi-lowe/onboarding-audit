# Config: onboarding-audit.config.json

The owner's answers from setup. The audit reads nothing else about what to test.

| Field | Required | What it holds |
| --- | --- | --- |
| `product`, `start_url` | Yes | The product name and where a new user starts. |
| `permission.confirmed` | Yes | `true` only if the owner runs the product or has written permission. |
| `activation.step`, `activation.description` | Yes | The step that counts as getting value, and what it means. |
| `test_identity.email_pattern` | Yes | Address pattern; `{persona}` and `{yyyymm}` are filled in per run. |
| `test_identity.inbox` | Yes | How the agent reads verification emails. |
| `payment.mode` | Yes | `stop` (go no further than the pay button) or `promo-link`. |
| `payment.promo_url`, `payment.expected_total` | With `promo-link` | The discount link and the exact total to expect before paying. |
| `personas` | No | The owner's personas: `id` (kebab-case), `label`, `email` (`work` or `personal`), `device` (`desktop` or `mobile`), optional `goal` and `traits`. Empty means one generic run. |
| `runs_per_persona` | No | Default 1. Raise it to catch flaky steps. |
| `taste` | No | The owner's taste preferences, in their words. |
| `tracker` | No | `{"type": "github", "repo": "owner/name"}`, `{"type": "linear", "team": "ENG"}` or `{"type": "jira", "base_url": "...", "project_id": 10000, "issuetype_id": 10004}`; optional `labels`. |
| `delivery` | Yes | `{"type": "email", "to": "..."}` or `{"type": "slack", "webhook_env": "SLACK_WEBHOOK_URL"}` / `{"type": "slack", "channel": "#growth"}`. |
| `report.tracker_notice` | No | `true` for a report shared with another company: readers connect their own tracker. |
| `report.auditor`, `report.permission_note` | No | Shown in the header and footer of shared reports. |
| `theme` | No | Colours and font for the report: `font`, `ink`, `muted`, `bg`, `card`, `line`, `accent`, `accent_dark`, `tint`, `header`, `header_ink`, `radius`. |

## Example

```json
{
  "product": "Acme Analytics",
  "start_url": "https://acme.example/signup",
  "permission": {
    "confirmed": true,
    "note": "We run this product"
  },
  "activation": {
    "step": "First dashboard",
    "description": "A new user sees their own data in a dashboard"
  },
  "test_identity": {
    "email_pattern": "audit+{persona}-{yyyymm}@yourdomain.com",
    "inbox": "Catch-all on yourdomain.com forwarding to a mailbox the agent can read"
  },
  "payment": {
    "mode": "stop"
  },
  "personas": [
    {
      "id": "work-email",
      "label": "Team lead, work email",
      "email": "work",
      "device": "desktop"
    },
    {
      "id": "mobile-personal",
      "label": "Founder on a phone, Gmail",
      "email": "personal",
      "device": "mobile"
    }
  ],
  "runs_per_persona": 1,
  "taste": [],
  "tracker": {
    "type": "github",
    "repo": "acme/app",
    "labels": [
      "bug",
      "signup-audit"
    ]
  },
  "delivery": {
    "type": "email",
    "to": "you@yourdomain.com"
  },
  "report": {
    "tracker_notice": false,
    "auditor": "",
    "permission_note": ""
  },
  "theme": {}
}
```
