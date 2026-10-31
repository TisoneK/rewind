"""AST node definitions for Pebble — FROZEN CONTRACT.

The parser builds a tree of these nodes; the interpreter walks it. Do not
change this file when implementing a layer — code against it.

Grammar (informal):

    program   := statement*
    statement := assign | print | if | while
    assign    := IDENT "=" expr ";"
    print     := "print" expr ";"
    if        := "if" "(" expr ")" block ("else" block)?
    while     := "while" "(" expr ")" block
    block     := "{" statement* "}"
    expr      := comparison
    comparison:= sum (("<" | ">" | "==") sum)?
    sum       := term (("+" | "-") term)*
    term      := factor (("*" | "/") factor)*
    factor    := INT | IDENT | "(" expr ")"

Booleans are integers: a comparison yields 1 (true) or 0 (false); `if`
and `while` treat any non-zero value as true.
"""
from __future__ import annotations

from dataclasses import dataclass


class Node:
    """Base class for every AST node (handy for isinstance checks)."""


@dataclass
class Num(Node):
    value: int


@dataclass
class Var(Node):
    name: str


@dataclass
class BinOp(Node):
    op: str          # one of: + - * / < > ==
    left: Node
    right: Node


@dataclass
class Assign(Node):
    name: str
    expr: Node


@dataclass
class Print(Node):
    expr: Node


@dataclass
class If(Node):
    cond: Node
    then_body: list[Node]
    else_body: list[Node]   # empty list when there is no else


@dataclass
class While(Node):
    cond: Node
    body: list[Node]


@dataclass
class Program(Node):
    body: list[Node]
