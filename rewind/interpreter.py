"""Layer C — the Pebble interpreter and recorder.

Walks a ``Program`` against an environment ``dict[str, int]``. When a
``Timeline`` is supplied, every executed statement is recorded so the
debugger can scrub back and forth over the run.

Semantics:

* All values are Python ints. ``/`` is floor division (Python's ``//``) and
  raises ``ZeroDivisionError`` on a zero divisor.
* ``< > ==`` yield ``1`` or ``0``.
* Reading a variable that was never assigned raises ``NameError``.
* ``if`` / ``while`` treat any non-zero condition as true.

Recording (when ``timeline`` is given):

* ``"start"`` is recorded first, with the empty environment (step 0).
* One snapshot follows each executed statement, taken *after* its effect:
  ``"x = 5"`` (the assigned value), ``"print x"``.
* ``if`` records ``"if <cond> -> true|false"`` once it has chosen a branch.
* ``while`` records ``"while <cond> -> true|false"`` every time the
  condition is evaluated -- once per iteration plus the final false check --
  so each trip round the loop, and each body statement, is its own step.

If execution raises, the snapshots recorded up to that point stay in the
timeline, so the failing run can still be inspected.
"""
from __future__ import annotations

from rewind.ast_nodes import (
    Assign,
    BinOp,
    If,
    Node,
    Num,
    Print,
    Program,
    Var,
    While,
)
from rewind.timeline import Timeline

# Binding strength of each operator, for printing expressions in descriptions.
_PRECEDENCE = {"<": 1, ">": 1, "==": 1, "+": 2, "-": 2, "*": 3, "/": 3}


def run(program: Program, timeline: Timeline | None = None) -> dict[str, int]:
    """Execute ``program`` and return the final environment."""
    env, _ = run_collect(program, timeline)
    return env


def run_collect(
    program: Program, timeline: Timeline | None = None
) -> tuple[dict[str, int], list[int]]:
    """Execute ``program``; return ``(final environment, printed ints)``.

    ``print`` never writes to stdout here -- values are only collected.
    """
    env: dict[str, int] = {}
    prints: list[int] = []
    if timeline is not None:
        timeline.record("start", env)
    _exec_block(program.body, env, prints, timeline)
    return env, prints


def _exec_block(
    body: list[Node],
    env: dict[str, int],
    prints: list[int],
    timeline: Timeline | None,
) -> None:
    for stmt in body:
        _exec(stmt, env, prints, timeline)


def _exec(
    stmt: Node,
    env: dict[str, int],
    prints: list[int],
    timeline: Timeline | None,
) -> None:
    if isinstance(stmt, Assign):
        value = _eval(stmt.expr, env)
        env[stmt.name] = value
        _record(timeline, f"{stmt.name} = {value}", env)
    elif isinstance(stmt, Print):
        prints.append(_eval(stmt.expr, env))
        _record(timeline, f"print {_show(stmt.expr)}", env)
    elif isinstance(stmt, If):
        taken = _eval(stmt.cond, env) != 0
        _record(timeline, f"if {_show(stmt.cond)} -> {_truth(taken)}", env)
        _exec_block(stmt.then_body if taken else stmt.else_body, env, prints, timeline)
    elif isinstance(stmt, While):
        while True:
            again = _eval(stmt.cond, env) != 0
            _record(timeline, f"while {_show(stmt.cond)} -> {_truth(again)}", env)
            if not again:
                break
            _exec_block(stmt.body, env, prints, timeline)
    else:
        raise TypeError(f"not a statement: {stmt!r}")


def _eval(expr: Node, env: dict[str, int]) -> int:
    if isinstance(expr, Num):
        return expr.value
    if isinstance(expr, Var):
        try:
            return env[expr.name]
        except KeyError:
            raise NameError(f"name {expr.name!r} is not defined") from None
    if isinstance(expr, BinOp):
        left = _eval(expr.left, env)
        right = _eval(expr.right, env)
        op = expr.op
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise ZeroDivisionError("division by zero")
            return left // right
        if op == "<":
            return int(left < right)
        if op == ">":
            return int(left > right)
        if op == "==":
            return int(left == right)
        raise ValueError(f"unknown operator {op!r}")
    raise TypeError(f"not an expression: {expr!r}")


def _record(timeline: Timeline | None, desc: str, env: dict[str, int]) -> None:
    if timeline is not None:
        timeline.record(desc, env)


def _truth(flag: bool) -> str:
    return "true" if flag else "false"


def _show(expr: Node) -> str:
    """Render an expression as source text, parenthesising only where needed."""
    if isinstance(expr, Num):
        return str(expr.value)
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, BinOp):
        prec = _PRECEDENCE.get(expr.op, 0)
        # Operators are left-associative (comparisons don't chain at all), so a
        # right operand of equal precedence needs parentheses, and so does a
        # comparison on either side of another comparison.
        left = _show_operand(expr.left, prec, strict=prec == 1)
        right = _show_operand(expr.right, prec, strict=True)
        return f"{left} {expr.op} {right}"
    return repr(expr)


def _show_operand(expr: Node, parent_prec: int, strict: bool) -> str:
    text = _show(expr)
    if isinstance(expr, BinOp):
        prec = _PRECEDENCE.get(expr.op, 0)
        if prec < parent_prec or (strict and prec == parent_prec):
            return f"({text})"
    return text
