"""Layer D — the time-travel debugger.

A thin reader over a recorded `Timeline`. The Timeline owns the snapshot list
and the scrub cursor; this class only drives that cursor (so it never
disagrees with anyone else holding the same Timeline) and renders what is
under it.
"""
from __future__ import annotations

from .timeline import Snapshot, Timeline


class TimeTravelDebugger:
    """Scrub backward and forward over a recorded Timeline.

    Every navigation method returns the Snapshot now under the cursor, or
    None when the timeline is empty. Movement is clamped to the recorded
    range, never wrapping or raising.
    """

    def __init__(self, timeline: Timeline) -> None:
        self.timeline = timeline

    # ---- navigation --------------------------------------------------
    def step(self, n: int = 1) -> Snapshot | None:
        """Scrub forward n steps."""
        return self.timeline.forward(n)

    def back(self, n: int = 1) -> Snapshot | None:
        """Scrub backward n steps."""
        return self.timeline.back(n)

    def goto(self, step: int) -> Snapshot | None:
        """Jump to an absolute step index."""
        return self.timeline.goto(step)

    def to_start(self) -> Snapshot | None:
        return self.timeline.to_start()

    def to_end(self) -> Snapshot | None:
        return self.timeline.to_end()

    # ---- inspection --------------------------------------------------
    def format_current(self) -> str:
        """One-line summary of the current step.

        e.g. ``"step 3/7  x=5 y=2  (x = 5)"``: the step index over the last
        step index, then the variables, then the step's description.
        """
        snap = self.timeline.current()
        if snap is None:
            return "step 0/0  (empty timeline)"
        last = len(self.timeline) - 1
        variables = " ".join(f"{k}={v}" for k, v in snap.env.items()) or "-"
        return f"step {snap.step}/{last}  {variables}  ({snap.desc})"

    def diff(self) -> dict[str, tuple[int | None, int | None]]:
        """Variables that changed between the previous step and this one.

        Maps name -> (old, new); None marks a variable that did not exist
        on that side. Empty at step 0 (nothing precedes it) and on an empty
        timeline.
        """
        snap = self.timeline.current()
        if snap is None or snap.step == 0:
            return {}
        before = self.timeline.at(snap.step - 1).env
        after = snap.env
        names = [*before, *(k for k in after if k not in before)]
        return {
            name: (before.get(name), after.get(name))
            for name in names
            if before.get(name) != after.get(name)
        }
