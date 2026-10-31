"""Lexer for the Pebble language (Layer A).

Turns source text into a list of ``Token`` per the frozen ``rewind.tokens``
contract. The list always ends with an EOF token positioned at ``len(src)``.
"""
from __future__ import annotations

from rewind.tokens import KEYWORDS, Token, TokenType

_WHITESPACE = " \t\r\n"
_DIGITS = "0123456789"
_IDENT_START = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
_IDENT_PART = _IDENT_START + _DIGITS

_SINGLE: dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ";": TokenType.SEMI,
}


def tokenize(src: str) -> list[Token]:
    """Tokenize ``src``; raise ``SyntaxError`` on an unexpected character."""
    tokens: list[Token] = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in _WHITESPACE:
            i += 1
        elif ch == "#":
            while i < n and src[i] != "\n":
                i += 1
        elif ch in _DIGITS:
            start = i
            while i < n and src[i] in _DIGITS:
                i += 1
            tokens.append(Token(TokenType.INT, src[start:i], start))
        elif ch in _IDENT_START:
            start = i
            while i < n and src[i] in _IDENT_PART:
                i += 1
            word = src[start:i]
            tokens.append(Token(KEYWORDS.get(word, TokenType.IDENT), word, start))
        elif ch == "=":
            if src.startswith("==", i):
                tokens.append(Token(TokenType.EQ, "==", i))
                i += 2
            else:
                tokens.append(Token(TokenType.ASSIGN, "=", i))
                i += 1
        elif ch in _SINGLE:
            tokens.append(Token(_SINGLE[ch], ch, i))
            i += 1
        else:
            raise SyntaxError(f"unexpected character {ch!r} at offset {i}")
    tokens.append(Token(TokenType.EOF, "", n))
    return tokens
