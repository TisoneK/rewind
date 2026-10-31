"""The recording spine for time-travel — FROZEN CONTRACT.

This is what makes `rewind` a *time-travel* debugger: as a program runs,
the interpreter records a Snapshot of the whole variable environment after
every step, and the debugger scrubs a cursor backward and forward over the
recorded Snapshots. Both the interpreter (writer) and the debugger (reader)
code against this file, so they can be built independently.

Do not change this file when implementing a layer — code against it.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Snapshot:
    """An immutable record of program state at one step.

    step:  0-based index of this snapshot in the timeline.
    desc:  a short human description of the step that produced this state,
           e.g. "x = 5", "print x", "while cond -> true".
    env:   a snapshot of all variables and their values at this point. It
           is a *copy*; mutating the interpreter's live environment later
           never changes a recorded Snapshot.
    """
    step: int
    desc: str
    env: dict[str, int]


class Timeline:
    """An ordered, append-only recording of Snapshots, plus a scrub cursor.

    Writer side (interpreter):
        tl.record("x = 5", env)   # copies env, appends a Snapshot

    Reader side (debugger):
        len(tl)        -> number of snapshots
        tl.at(i)       -> Snapshot i (supports negatives, like a list)
        tl.snapshots   -> the list of Snapshots (read-only use)
        cursor navigation: tl.cursor, tl.goto(i), tl.forward(), tl.back(),
        tl.to_start(), tl.to_end(), tl.current()
    """

    def __init__(self) -> None:
        self.snapshots: list[Snapshot] = []
        self._cursor: int = 0

    # ---- writer side -------------------------------------------------
    def record(self, desc: str, env: dict[str, int]) -> Snapshot:
        """Append a Snapshot capturing a *copy* of env. Returns it."""
        snap = Snapshot(step=len(self.snapshots), desc=desc, env=dict(env))
        self.snapshots.append(snap)
        self._cursor = len(self.snapshots) - 1
        return snap

    # ---- reader side -------------------------------------------------
    def __len__(self) -> int:
        return len(self.snapshots)

    def at(self, i: int) -> Snapshot:
        """Snapshot at index i (negative indexes from the end)."""
        return self.snapshots[i]

    @property
    def cursor(self) -> int:
        """Index the scrub cursor currently points at (0 if empty)."""
        return self._cursor

    def current(self) -> Snapshot | None:
        """Snapshot under the cursor, or None if the timeline is empty."""
        if not self.snapshots:
            return None
        return self.snapshots[self._cursor]

    def goto(self, i: int) -> Snapshot | None:
        """Move the cursor to step i, clamped into range. Returns current()."""
        if not self.snapshots:
            return None
        self._cursor = max(0, min(i, len(self.snapshots) - 1))
        return self.current()

    def forward(self, n: int = 1) -> Snapshot | None:
        """Scrub forward n steps (clamped)."""
        return self.goto(self._cursor + n)

    def back(self, n: int = 1) -> Snapshot | None:
        """Scrub backward n steps (clamped) — the whole point of rewind."""
        return self.goto(self._cursor - n)

    def to_start(self) -> Snapshot | None:
        return self.goto(0)

    def to_end(self) -> Snapshot | None:
        return self.goto(len(self.snapshots) - 1)
