# Severity rubric

Severity comes from what happened in the run, never from an estimate. Each level is something a screenshot can show.

| Severity | What happened | Code |
| --- | --- | --- |
| High | The run could not go further on that path | `blocked` |
| High | Data, money or an email went to the wrong person | `wrong-recipient` |
| Medium | The run only continued after a workaround | `workaround` |
| Medium | The run hit an error and had to recover | `error` |
| Low | Extra steps, fields or decisions; nothing broke | `extra-effort` |
| Low | Copy, consistency or visual issue; nothing broke | `polish` |

## How many users are affected

Never guessed. Each finding lists which of the owner's personas hit it. If the owner supplies real numbers with a source, the report shows them next to the finding; they don't change the severity.

## Rules

- A finding tagged Guessing can't be High until it's checked.
- Accessibility findings are Low unless they block someone.
- Taste findings come only from the owner's taste preferences, are capped at Medium, and are reported separately.
- Confidence is shown on every finding: Certain (seen), Likely (strong inference), Guessing (filling a gap).

## Personas

Personas come only from the owner's config. A run can't use a persona that isn't listed there. With no personas, the audit runs one generic new-user path and the report says so.

