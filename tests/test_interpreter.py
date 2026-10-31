"""Tests for Layer C — the interpreter + recorder.

Inputs are built directly from ``rewind.ast_nodes``; neither the lexer nor
the parser is imported, so this file stands alone.
"""
from __future__ import annotations

import pytest

from rewind.ast_nodes import Assign, BinOp, If, Num, Print, Program, Var, While
from rewind.interpreter import run, run_collect
from rewind.timeline import Timeline


def prog(*body) -> Program:
    return Program(list(body))


def bin_(op, left, right) -> BinOp:
    return BinOp(op, left, right)


def counting_loop(limit: int = 3) -> Program:
    """x = 0; while (x < limit) { x = x + 1; }"""
    return prog(
        Assign("x", Num(0)),
        While(
            bin_("<", Var("x"), Num(limit)),
            [Assign("x", bin_("+", Var("x"), Num(1)))],
        ),
    )


# ---- expressions ------------------------------------------------------

@pytest.mark.parametrize(
    "op, a, b, expected",
    [
        ("+", 2, 3, 5),
        ("-", 2, 3, -1),
        ("*", 4, 3, 12),
        ("/", 7, 2, 3),
        ("/", 6, 3, 2),
        ("<", 1, 2, 1),
        ("<", 2, 2, 0),
        (">", 3, 2, 1),
        (">", 2, 3, 0),
        ("==", 4, 4, 1),
        ("==", 4, 5, 0),
    ],
)
def test_binary_operators(op, a, b, expected):
    assert run(prog(Assign("r", bin_(op, Num(a), Num(b))))) == {"r": expected}


def test_nested_expression_respects_tree_shape():
    # (1 + 2) * (10 - 4) / 3  ==  ((3 * 6) / 3)  ==  6
    expr = bin_(
        "/",
        bin_("*", bin_("+", Num(1), Num(2)), bin_("-", Num(10), Num(4))),
        Num(3),
    )
    assert run(prog(Assign("r", expr))) == {"r": 6}


def test_division_is_floor_division():
    assert run(prog(Assign("r", bin_("/", Num(-7), Num(2))))) == {"r": -4}


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        run(prog(Assign("r", bin_("/", Num(1), Num(0)))))


def test_divide_by_zero_from_variable_raises():
    p = prog(Assign("z", Num(0)), Print(bin_("/", Num(5), Var("z"))))
    with pytest.raises(ZeroDivisionError):
        run(p)


def test_unassigned_var_raises_name_error():
    with pytest.raises(NameError, match="ghost"):
        run(prog(Print(Var("ghost"))))


def test_assignment_reads_its_own_old_value():
    p = prog(Assign("x", Num(1)), Assign("x", bin_("+", Var("x"), Num(41))))
    assert run(p) == {"x": 42}


def test_var_unassigned_on_right_hand_side_of_first_assignment():
    with pytest.raises(NameError):
        run(prog(Assign("x", bin_("+", Var("x"), Num(1)))))


# ---- statements -------------------------------------------------------

def test_empty_program():
    assert run(prog()) == {}
    assert run_collect(prog()) == ({}, [])


def test_print_collects_in_order_and_does_not_write_stdout(capsys):
    p = prog(Print(Num(1)), Print(Num(2)), Print(bin_("+", Num(1), Num(2))))
    env, printed = run_collect(p)
    assert (env, printed) == ({}, [1, 2, 3])
    assert capsys.readouterr().out == ""


def test_if_true_branch():
    p = prog(
        If(Num(1), [Assign("x", Num(10))], [Assign("x", Num(20))]),
    )
    assert run(p) == {"x": 10}


def test_if_false_takes_else():
    p = prog(
        If(Num(0), [Assign("x", Num(10))], [Assign("x", Num(20))]),
    )
    assert run(p) == {"x": 20}


def test_if_false_without_else_does_nothing():
    assert run(prog(If(Num(0), [Assign("x", Num(1))], []))) == {}


@pytest.mark.parametrize("cond", [1, 2, 42, -1, -100])
def test_any_nonzero_condition_is_true(cond):
    p = prog(If(Num(cond), [Assign("x", Num(1))], [Assign("x", Num(0))]))
    assert run(p) == {"x": 1}


def test_comparison_as_condition():
    p = prog(
        Assign("a", Num(3)),
        If(bin_(">", Var("a"), Num(2)), [Print(Num(1))], [Print(Num(0))]),
    )
    assert run_collect(p)[1] == [1]


def test_while_counts_up():
    assert run(counting_loop(5)) == {"x": 5}


def test_while_with_false_condition_never_runs_body():
    p = prog(While(Num(0), [Print(Num(99))]))
    assert run_collect(p) == ({}, [])


def test_while_nonzero_condition_value_not_just_comparison():
    # n = 3; while (n) { print n; n = n - 1; }
    p = prog(
        Assign("n", Num(3)),
        While(Var("n"), [Print(Var("n")), Assign("n", bin_("-", Var("n"), Num(1)))]),
    )
    assert run_collect(p) == ({"n": 0}, [3, 2, 1])


def test_nested_loops_and_if():
    # i = 0; evens = 0
    # while (i < 6) { if (i / 2 * 2 == i) { evens = evens + 1; } i = i + 1; }
    is_even = bin_("==", bin_("*", bin_("/", Var("i"), Num(2)), Num(2)), Var("i"))
    p = prog(
        Assign("i", Num(0)),
        Assign("evens", Num(0)),
        While(
            bin_("<", Var("i"), Num(6)),
            [
                If(is_even, [Assign("evens", bin_("+", Var("evens"), Num(1)))], []),
                Assign("i", bin_("+", Var("i"), Num(1))),
            ],
        ),
    )
    assert run(p) == {"i": 6, "evens": 3}


def test_factorial_program():
    # n = 5; f = 1; while (n > 0) { f = f * n; n = n - 1; } print f;
    p = prog(
        Assign("n", Num(5)),
        Assign("f", Num(1)),
        While(
            bin_(">", Var("n"), Num(0)),
            [
                Assign("f", bin_("*", Var("f"), Var("n"))),
                Assign("n", bin_("-", Var("n"), Num(1))),
            ],
        ),
        Print(Var("f")),
    )
    assert run_collect(p) == ({"n": 0, "f": 120}, [120])


def test_run_and_run_collect_agree():
    p = counting_loop(4)
    assert run(p) == run_collect(p)[0]


def test_run_is_repeatable_with_fresh_environments():
    p = counting_loop(3)
    first, second = run(p), run(p)
    assert first == second == {"x": 3}
    assert first is not second


def test_non_statement_node_is_rejected():
    with pytest.raises(TypeError):
        run(prog(Num(1)))


def test_unknown_operator_is_rejected():
    with pytest.raises(ValueError):
        run(prog(Assign("x", bin_("%", Num(1), Num(2)))))


# ---- recording --------------------------------------------------------

def test_no_timeline_is_fine():
    assert run(counting_loop(2), None) == {"x": 2}


def test_empty_program_records_only_start():
    tl = Timeline()
    run(prog(), tl)
    assert [(s.step, s.desc, s.env) for s in tl.snapshots] == [(0, "start", {})]


def test_start_is_recorded_first_with_empty_env():
    tl = Timeline()
    run(prog(Assign("x", Num(5))), tl)
    assert tl.at(0).desc == "start"
    assert tl.at(0).env == {}


def test_one_snapshot_per_statement_after_its_effect():
    tl = Timeline()
    p = prog(
        Assign("x", Num(5)),
        Assign("y", bin_("+", Var("x"), Num(2))),
        Print(Var("y")),
    )
    run(p, tl)
    assert [s.desc for s in tl.snapshots] == ["start", "x = 5", "y = 7", "print y"]
    assert [s.env for s in tl.snapshots] == [
        {},
        {"x": 5},
        {"x": 5, "y": 7},
        {"x": 5, "y": 7},
    ]
    assert [s.step for s in tl.snapshots] == [0, 1, 2, 3]


def test_assign_desc_shows_the_assigned_value():
    tl = Timeline()
    run(prog(Assign("x", Num(2)), Assign("x", bin_("*", Var("x"), Num(3)))), tl)
    assert [s.desc for s in tl.snapshots][1:] == ["x = 2", "x = 6"]


def test_snapshots_are_independent_copies():
    tl = Timeline()
    env = run(counting_loop(3), tl)
    env["x"] = 999
    assert [s.env.get("x") for s in tl.snapshots] == [None, 0, 0, 1, 1, 2, 2, 3, 3]


def test_loop_body_records_every_iteration():
    tl = Timeline()
    run(counting_loop(3), tl)
    assert [s.desc for s in tl.snapshots] == [
        "start",
        "x = 0",
        "while x < 3 -> true",
        "x = 1",
        "while x < 3 -> true",
        "x = 2",
        "while x < 3 -> true",
        "x = 3",
        "while x < 3 -> false",
    ]


def test_body_snapshot_count_scales_with_iterations():
    for n in (0, 1, 7):
        tl = Timeline()
        run(counting_loop(n), tl)
        # start + init + (n body assigns + n true checks) + final false check
        assert len(tl) == 1 + 1 + 2 * n + 1


def test_if_records_condition_outcome_then_branch():
    tl = Timeline()
    p = prog(
        Assign("a", Num(1)),
        If(bin_("==", Var("a"), Num(1)), [Assign("b", Num(10))], [Assign("b", Num(20))]),
        If(Var("a"), [], [Assign("never", Num(1))]),
    )
    run(p, tl)
    assert [s.desc for s in tl.snapshots] == [
        "start",
        "a = 1",
        "if a == 1 -> true",
        "b = 10",
        "if a -> true",
    ]


def test_if_false_records_outcome_and_else_branch():
    tl = Timeline()
    run(prog(If(Num(0), [Assign("x", Num(1))], [Assign("x", Num(2))])), tl)
    assert [s.desc for s in tl.snapshots] == ["start", "if 0 -> false", "x = 2"]


def test_print_does_not_change_env_but_is_a_step():
    tl = Timeline()
    run(prog(Assign("x", Num(3)), Print(bin_("+", Var("x"), Num(1)))), tl)
    assert tl.at(-1).desc == "print x + 1"
    assert tl.at(-1).env == tl.at(-2).env == {"x": 3}


def test_run_collect_records_too_and_matches_run():
    p = counting_loop(3)
    tl_run, tl_collect = Timeline(), Timeline()
    run(p, tl_run)
    env, printed = run_collect(p, tl_collect)
    assert printed == []
    assert env == {"x": 3}
    assert [(s.desc, s.env) for s in tl_run.snapshots] == [
        (s.desc, s.env) for s in tl_collect.snapshots
    ]


def test_timeline_left_at_end_and_scrubbable():
    tl = Timeline()
    run(counting_loop(3), tl)
    assert tl.cursor == len(tl) - 1
    assert tl.to_start().env == {}
    assert tl.goto(3).env == {"x": 1}
    assert tl.back(2).env == {"x": 0}
    assert tl.to_end().env == {"x": 3}


def test_error_keeps_snapshots_up_to_the_failure():
    tl = Timeline()
    p = prog(
        Assign("x", Num(1)),
        Assign("y", bin_("/", Var("x"), Num(0))),
        Assign("z", Num(9)),
    )
    with pytest.raises(ZeroDivisionError):
        run(p, tl)
    assert [s.desc for s in tl.snapshots] == ["start", "x = 1"]


def test_name_error_keeps_snapshots_up_to_the_failure():
    tl = Timeline()
    with pytest.raises(NameError):
        run(prog(Assign("x", Num(1)), Print(Var("nope"))), tl)
    assert len(tl) == 2


@pytest.mark.parametrize(
    "expr, text",
    [
        (bin_("+", Var("a"), bin_("*", Var("b"), Num(2))), "a + b * 2"),
        (bin_("*", bin_("+", Var("a"), Var("b")), Num(2)), "(a + b) * 2"),
        (bin_("-", Var("a"), bin_("-", Var("b"), Var("c"))), "a - (b - c)"),
        (bin_("-", bin_("-", Var("a"), Var("b")), Var("c")), "a - b - c"),
        (bin_("/", Num(8), bin_("*", Num(2), Num(2))), "8 / (2 * 2)"),
        (bin_("<", bin_("+", Var("a"), Num(1)), Var("b")), "a + 1 < b"),
        (bin_("==", bin_("<", Var("a"), Var("b")), Num(1)), "(a < b) == 1"),
    ],
)
def test_print_desc_renders_expression_with_minimal_parens(expr, text):
    tl = Timeline()
    run(prog(Assign("a", Num(1)), Assign("b", Num(2)), Assign("c", Num(3)), Print(expr)), tl)
    assert tl.at(-1).desc == f"print {text}"
