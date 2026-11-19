"""Time to value, measured honestly.

An agent's own wall-clock time says nothing about a person's: agents pause to think,
retry and wait on handoffs. So a run records two different things per step:

  measured  system waits the person would also sit through: an email arriving,
            a page loading, a connection test, a first sync. Timed from the trigger
            to the moment the result appeared.
  estimated hands-on effort, from what the step asks of the person: screens read,
            clicks, fields typed, choices made. Converted to seconds with
            keystroke-level model constants (Card, Moran and Newell), which are
            averages for a practiced user, so real first-timers will be slower.

Handoffs (steps the account owner had to do, like approving Google sign-in) are
counted separately, because each one is a place a real user can stall.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Keystroke-level model operators, seconds
K = 0.28   # one keystroke, average typist
P = 1.1    # point at a target
B = 0.1    # mouse button press
M = 1.35   # mental preparation before an action
READ_SCREEN = 3.0  # skim a new screen to find the next action (not a KLM operator; a stated assumption)

OUTCOMES = ("ok", "workaround", "blocked")


@dataclass
class Step:
    name: str
    screens: int = 1
    clicks: int = 0
    fields: int = 0          # text fields typed into
    chars: int = 0           # total characters typed
    choices: int = 0         # decisions between options (survey answers, pick a source)
    system_wait_s: float = 0.0   # measured
    handoff: bool = False    # needed the account owner
    outcome: str = "ok"
    note: str = ""

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}: {self.outcome!r}")
        for name in ("screens", "clicks", "fields", "chars", "choices"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} can't be negative")
        if self.system_wait_s < 0:
            raise ValueError("system_wait_s can't be negative")

    @property
    def effort_s(self) -> float:
        return round(
            self.screens * READ_SCREEN
            + self.clicks * (M + P + B)
            + self.fields * (M + P + B)          # move to the field
            + self.chars * K
            + self.choices * M,                  # extra thinking per decision
            1)

    @property
    def total_s(self) -> float:
        return round(self.effort_s + self.system_wait_s, 1)


@dataclass
class Funnel:
    steps: list[Step] = field(default_factory=list)
    activation_step: str | None = None   # name of the step that counts as activation

    def reached_activation(self) -> bool:
        if not self.activation_step:
            return False
        for s in self.steps:
            if s.outcome == "blocked":
                return False
            if s.name == self.activation_step:
                return True
        return False

    def until_stop(self) -> list[Step]:
        """Steps up to activation, or up to and including the first blocked step."""
        out = []
        for s in self.steps:
            out.append(s)
            if s.outcome == "blocked" or s.name == self.activation_step:
                break
        return out

    def summary(self) -> dict:
        steps = self.until_stop()
        effort = round(sum(s.effort_s for s in steps), 1)
        wait = round(sum(s.system_wait_s for s in steps), 1)
        blocked = next((s.name for s in steps if s.outcome == "blocked"), None)
        return {
            "reached_activation": self.reached_activation(),
            "stopped_at": blocked,
            "time_to_value_s": round(effort + wait, 1) if self.reached_activation() else None,
            "time_until_stop_s": round(effort + wait, 1),
            "effort_s": effort,
            "system_wait_s": wait,
            "screens": sum(s.screens for s in steps),
            "clicks": sum(s.clicks for s in steps),
            "fields": sum(s.fields for s in steps),
            "choices": sum(s.choices for s in steps),
            "handoffs": sum(s.handoff for s in steps),
        }


def fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "not reached"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} min {s} s" if s else f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} h {m} min"
