"""Tests for Layer D (rewind/debugger.py).

Timelines are built by hand with Timeline.record() and fake envs, so these
tests depend on no other layer.
"""
from __future__ import annotations

import pytest

from rewind.debugger import TimeTravelDebugger
from rewind.timeline import Snapshot, Timeline


def make_timeline() -> Timeline:
    """A 7-snapshot run (steps 0..6), like `x=5; y=2; x=x+y; print x; ...`."""
    tl = Timeline()
    tl.record("start", {})
    tl.record("x = 5", {"x": 5})
    tl.record("y = 2", {"x": 5, "y": 2})
    tl.record("x = 5", {"x": 5, "y": 2})  # reassigned to the same value
    tl.record("x = x + y", {"x": 7, "y": 2})
    tl.record("print x", {"x": 7, "y": 2})
    tl.record("y = 0", {"x": 7, "y": 0})
    return tl


@pytest.fixture
def dbg() -> TimeTravelDebugger:
    d = TimeTravelDebugger(make_timeline())
    d.to_start()
    return d


# ---- navigation -----------------------------------------------------------

def test_step_moves_forward_and_returns_snapshot(dbg):
    snap = dbg.step()
    assert isinstance(snap, Snapshot)
    assert snap.step == 1 and snap.desc == "x = 5"
    assert dbg.timeline.cursor == 1


def test_step_n(dbg):
    assert dbg.step(3).step == 3
    assert dbg.step(2).step == 5


def test_step_clamps_at_end(dbg):
    assert dbg.step(100).step == 6
    assert dbg.step().step == 6


def test_back_moves_backward(dbg):
    dbg.goto(5)
    assert dbg.back().step == 4
    assert dbg.back(3).step == 1


def test_back_clamps_at_start(dbg):
    dbg.goto(2)
    assert dbg.back(100).step == 0
    assert dbg.back().step == 0


def test_goto(dbg):
    assert dbg.goto(4).step == 4
    assert dbg.goto(1).step == 1


def test_goto_clamps_out_of_range(dbg):
    assert dbg.goto(999).step == 6
    assert dbg.goto(-5).step == 0


def test_to_start_and_to_end(dbg):
    assert dbg.to_end().step == 6
    assert dbg.to_start().step == 0


def test_step_then_back_round_trips(dbg):
    dbg.goto(2)
    dbg.step(3)
    assert dbg.back(3).step == 2


def test_drives_the_timeline_cursor(dbg):
    # The debugger holds no position of its own: the Timeline's cursor is
    # the single source of truth, in both directions.
    dbg.step(4)
    assert dbg.timeline.cursor == 4
    dbg.timeline.goto(1)
    assert dbg.step().step == 2
    assert dbg.timeline.cursor == 2


def test_navigation_returns_the_recorded_snapshot_objects(dbg):
    assert dbg.goto(3) is dbg.timeline.at(3)


def test_navigation_on_empty_timeline_returns_none():
    d = TimeTravelDebugger(Timeline())
    assert d.step() is None
    assert d.back() is None
    assert d.goto(3) is None
    assert d.to_start() is None
    assert d.to_end() is None


def test_single_snapshot_timeline():
    tl = Timeline()
    tl.record("start", {})
    d = TimeTravelDebugger(tl)
    assert d.step().step == 0
    assert d.back().step == 0
    assert d.to_end().step == 0


# ---- format_current -------------------------------------------------------

def test_format_current_matches_contract_example(dbg):
    # step index over last step index, variables, then the description
    dbg.goto(2)
    assert dbg.format_current() == "step 2/6  x=5 y=2  (y = 2)"


def test_format_current_at_start_has_no_variables(dbg):
    assert dbg.format_current() == "step 0/6  -  (start)"


def test_format_current_at_end(dbg):
    dbg.to_end()
    assert dbg.format_current() == "step 6/6  x=7 y=0  (y = 0)"


def test_format_current_keeps_variable_insertion_order():
    tl = Timeline()
    tl.record("start", {})
    tl.record("b = 1", {"b": 1})
    tl.record("a = 2", {"b": 1, "a": 2})
    d = TimeTravelDebugger(tl)
    assert d.format_current() == "step 2/2  b=1 a=2  (a = 2)"


def test_format_current_negative_values():
    tl = Timeline()
    tl.record("start", {})
    tl.record("x = 0 - 3", {"x": -3})
    assert TimeTravelDebugger(tl).format_current() == "step 1/1  x=-3  (x = 0 - 3)"


def test_format_current_follows_the_cursor(dbg):
    dbg.goto(4)
    assert dbg.format_current().startswith("step 4/6  x=7 y=2")
    dbg.back(2)
    assert dbg.format_current().startswith("step 2/6  x=5 y=2")


def test_format_current_empty_timeline():
    assert TimeTravelDebugger(Timeline()).format_current() == "step 0/0  (empty timeline)"


# ---- diff -----------------------------------------------------------------

def test_diff_empty_at_step_zero(dbg):
    assert dbg.diff() == {}


def test_diff_empty_at_step_zero_with_nonempty_env():
    tl = Timeline()
    tl.record("start", {"x": 1})
    tl.record("x = 2", {"x": 2})
    d = TimeTravelDebugger(tl)
    d.to_start()
    assert d.diff() == {}


def test_diff_new_variable_has_none_old(dbg):
    dbg.goto(1)
    assert dbg.diff() == {"x": (None, 5)}


def test_diff_second_new_variable_only_reports_the_new_one(dbg):
    dbg.goto(2)
    assert dbg.diff() == {"y": (None, 2)}


def test_diff_changed_variable(dbg):
    dbg.goto(4)
    assert dbg.diff() == {"x": (5, 7)}


def test_diff_ignores_reassignment_to_same_value(dbg):
    dbg.goto(3)
    assert dbg.diff() == {}


def test_diff_ignores_steps_that_change_nothing(dbg):
    dbg.goto(5)  # print x
    assert dbg.diff() == {}


def test_diff_reports_multiple_changes():
    tl = Timeline()
    tl.record("start", {"a": 1, "b": 2})
    tl.record("swap", {"a": 2, "b": 1})
    d = TimeTravelDebugger(tl)
    d.goto(1)
    assert d.diff() == {"a": (1, 2), "b": (2, 1)}


def test_diff_variable_removed_has_none_new():
    # Pebble never un-defines a variable, but diff stays correct for any
    # timeline it is handed.
    tl = Timeline()
    tl.record("start", {"x": 1, "y": 2})
    tl.record("gone", {"x": 1})
    d = TimeTravelDebugger(tl)
    d.goto(1)
    assert d.diff() == {"y": (2, None)}


def test_diff_distinguishes_zero_from_missing():
    tl = Timeline()
    tl.record("start", {})
    tl.record("x = 0", {"x": 0})
    d = TimeTravelDebugger(tl)
    d.goto(1)
    assert d.diff() == {"x": (None, 0)}


def test_diff_follows_the_cursor_backward_too(dbg):
    dbg.to_end()
    assert dbg.diff() == {"y": (2, 0)}
    dbg.back(2)  # step 4
    assert dbg.diff() == {"x": (5, 7)}


def test_diff_does_not_move_the_cursor(dbg):
    dbg.goto(4)
    dbg.diff()
    assert dbg.timeline.cursor == 4


def test_diff_on_empty_timeline():
    assert TimeTravelDebugger(Timeline()).diff() == {}


# ---- loop-shaped timeline (what the interpreter's while loop produces) -----

def test_scrubbing_a_loop_forward_and_back():
    tl = Timeline()
    tl.record("start", {})
    tl.record("i = 0", {"i": 0})
    for n in range(1, 4):
        tl.record("while cond", {"i": n - 1})
        tl.record("i = i + 1", {"i": n})
    d = TimeTravelDebugger(tl)
    d.to_start()

    seen = []
    while d.timeline.cursor < len(tl) - 1:
        seen.append(d.step().env["i"])
    assert seen == [0, 0, 1, 1, 2, 2, 3]
    assert d.format_current() == "step 7/7  i=3  (i = i + 1)"
    assert d.diff() == {"i": (2, 3)}

    d.back(2)  # step 5: i = i + 1, taking i from 1 to 2
    assert d.format_current() == "step 5/7  i=2  (i = i + 1)"
    assert d.diff() == {"i": (1, 2)}
    d.back()  # step 4: the loop test re-checks, state unchanged
    assert d.diff() == {}
