# Audit file format

One audit file per product per month. It holds one run per persona; findings from all runs are merged by `key` in the report.

```json
{
  "product": "Acme Analytics",
  "month": "Dec 2026",
  "report_url": "https://where.the/report/lives",
  "summary": "One paragraph on what the audit found, in plain language.",
  "worked": ["Signup asks for one field."],
  "notes": [["Cleanup", "Delete the audit+work-email-202612 account."]],
  "taste": [],
  "runs": [
    {
      "persona": {"id": "work-email", "label": "Team lead, work email", "email": "work", "device": "desktop"},
      "funnel": {
        "activation_step": "First dashboard",
        "steps": [
          {"name": "Sign up", "screens": 2, "clicks": 3, "fields": 2, "chars": 34},
          {"name": "Verify email", "screens": 1, "system_wait_s": 12, "handoff": true},
          {"name": "Connect data", "screens": 3, "clicks": 7, "choices": 2, "outcome": "workaround", "note": "Error on first try"},
          {"name": "First dashboard", "screens": 1, "system_wait_s": 95}
        ]
      },
      "findings": [
        {
          "key": "connect-data-first-try-error",
          "observed": "error",
          "confidence": "Certain",
          "title": "Connecting data fails on the first try",
          "steps": "Sign up, verify, choose Postgres, click Test.",
          "expected": "The test passes or explains what to fix.",
          "actual": "'Unknown error' with no detail; the second try passed.",
          "fix": "Show the real error and what to change.",
          "screenshot": "shots/05-connect-error.jpg",
          "caption": "The error after the first Test click."
        }
      ]
    }
  ]
}
```

## Steps

Record what each step asked of the person, not how long you took: an agent's clock measures its own thinking and retries.

| Field | Meaning |
| --- | --- |
| `screens` | New screens the person had to read |
| `clicks` | Clicks or taps |
| `fields`, `chars` | Text fields typed into, and total characters typed |
| `choices` | Decisions between options |
| `system_wait_s` | Measured time waiting on the product: an email arriving, a test running, a sync finishing |
| `handoff` | `true` when the account owner had to act (open a link, approve a sign-in) |
| `outcome` | `ok`, `workaround`, or `blocked` (the run stopped here) |

Hands-on time is estimated from these with keystroke-level model averages (Card, Moran and Newell) and labelled as an estimate in the report. Waits are measured.

## Findings

| Field | Meaning |
| --- | --- |
| `key` | Stable kebab-case id; reuse it for the same problem next month |
| `observed` | `blocked`, `wrong-recipient`, `workaround`, `error`, `extra-effort` or `polish`; sets severity (see rubric.md) |
| `confidence` | `Certain`, `Likely` or `Guessing` |
| `category` | `friction` (default), `accessibility` or `taste` |
| `preference` | Taste findings only: the owner's preference it goes against, word for word |
| `affected` | Only from the owner's own data: `{"share": "...", "source": "..."}` |
| `title`, `steps`, `expected`, `actual`, `fix` | Plain language |
| `screenshot`, `caption` | Path under the report folder, and a one-line caption |
