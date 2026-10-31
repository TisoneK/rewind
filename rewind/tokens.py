"""Token definitions for the Pebble language — FROZEN CONTRACT.

Every layer agrees on these token types and this Token shape. The lexer
produces a list[Token]; the parser consumes it. Do not change this file
when implementing a layer — code against it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # literals / names
    INT = auto()        # 42
    IDENT = auto()      # x, total
    # keywords
    PRINT = auto()      # print
    IF = auto()         # if
    ELSE = auto()       # else
    WHILE = auto()      # while
    # operators
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    ASSIGN = auto()     # =
    EQ = auto()         # ==
    LT = auto()         # <
    GT = auto()         # >
    # punctuation
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACE = auto()     # {
    RBRACE = auto()     # }
    SEMI = auto()       # ;
    EOF = auto()        # end of input

    def __repr__(self) -> str:  # nicer failure messages in tests
        return self.name


# Source keywords map to their token type. An identifier that is not a
# keyword is TokenType.IDENT.
KEYWORDS: dict[str, TokenType] = {
    "print": TokenType.PRINT,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
}


@dataclass(frozen=True)
class Token:
    """One lexical token.

    type:  the TokenType.
    value: the matched source text (e.g. "42", "x", "+"); for the final
           token it is "" and type is EOF.
    pos:   0-based character offset in the source where the token starts
           (the EOF token's pos is len(source)).
    """
    type: TokenType
    value: str
    pos: int
