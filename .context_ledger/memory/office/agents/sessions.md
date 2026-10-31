# Agent Sessions (append-only within the current office)

One entry per agent session in the **current office**, newest at the bottom.
Never edit or delete past entries — append corrections instead. This is not
append-only *forever*: when the office reaches `office_size` sessions (or a
milestone), `ledger-history close` freezes this whole office verbatim into
`.context_ledger/history/office-<NNN>/` (roster, registry, notes, logs —
nothing trimmed), writes the permanent accomplishments record
`.context_ledger/history/office-<NNN>.md`, and opens a fresh empty office
here. Closed offices in `history/` and `archive/` are never read at session
start. Before closing, note which open threads still matter — they are
re-seeded into the new office explicitly, and nothing else carries over.

<!-- TEMPLATE — copy below the last entry and FILL IN every placeholder:
---
## YYYY-MM-DD — Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay from .context_ledger/core/roles/> | **Core:** <version from .context_ledger/core/VERSION>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked — one line>
- **Open items:** <pointers into tasks/backlog.md (actionable) or tasks/parking-lot.md (findings/questions), or "none">
- **Notes:** .context_ledger/memory/office/sessions/<date>-<N>/notes.md  (or "none")
- **Report:** .context_ledger/memory/office/reviews/YYYY-MM-DD-review.md
-->

---
## 2026-10-30 — Session 4
- **Agent:** Margaret (S004) | **Model:** claude-sonnet-5-5 | **Platform:** macOS (darwin 24.6) local worktree | **Role:** engineer | **Core:** 2.3.0
- **Task:** Cohort C-rewind-01 Layer D — implement the time-travel debugger (`rewind/debugger.py`) and `tests/test_debugger.py`.
- **Commits:** 3 (b1d8a02..3c5e65f, plus this session-log commit)
- **Outcome:** done — `TimeTravelDebugger` drives the Timeline cursor; 34 tests pass on hand-built timelines (no other layer imported).
- **Open items:** `format_current` reads `step <snap.step>/<last index>` (e.g. 7 snapshots -> `step 6/6` at the end); the contract example `step 3/7` is ambiguous, so the integrator may flip it to `len` as the denominator. The pre-commit gate shells out to bare `python`, which this machine lacks; run it with `.venv/bin` on PATH.
- **Notes:** none
- **Report:** none
