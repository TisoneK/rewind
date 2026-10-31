"""Layer B — recursive-descent parser for Pebble.

Turns the token list produced by the lexer into the AST defined in
``rewind.ast_nodes``. The grammar is documented there; each rule below maps
to one method of ``_Parser``.
"""
from __future__ import annotations

from rewind.ast_nodes import Assign, BinOp, If, Node, Num, Print, Program, Var, While
from rewind.tokens import Token, TokenType

_COMPARE_OPS = (TokenType.LT, TokenType.GT, TokenType.EQ)
_SUM_OPS = (TokenType.PLUS, TokenType.MINUS)
_TERM_OPS = (TokenType.STAR, TokenType.SLASH)


def parse(tokens: list[Token]) -> Program:
    """Parse a token list (ending in EOF) into a Program.

    Raises SyntaxError, naming the offending source offset, on malformed input.
    """
    return _Parser(tokens).parse_program()


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        if not tokens or tokens[-1].type is not TokenType.EOF:
            raise SyntaxError("token list must end with an EOF token")
        self.tokens = tokens
        self.i = 0

    # -- token helpers -----------------------------------------------------

    @property
    def cur(self) -> Token:
        return self.tokens[self.i]

    def _at(self, *types: TokenType) -> bool:
        return self.cur.type in types

    def _advance(self) -> Token:
        tok = self.cur
        if tok.type is not TokenType.EOF:
            self.i += 1
        return tok

    def _error(self, expected: str) -> SyntaxError:
        tok = self.cur
        found = "end of input" if tok.type is TokenType.EOF else repr(tok.value)
        return SyntaxError(f"expected {expected} but found {found} at offset {tok.pos}")

    def _expect(self, type_: TokenType, what: str) -> Token:
        if self.cur.type is not type_:
            raise self._error(what)
        return self._advance()

    # -- statements --------------------------------------------------------

    def parse_program(self) -> Program:
        body: list[Node] = []
        while not self._at(TokenType.EOF):
            body.append(self._statement())
        return Program(body)

    def _statement(self) -> Node:
        t = self.cur.type
        if t is TokenType.IDENT:
            return self._assign()
        if t is TokenType.PRINT:
            return self._print()
        if t is TokenType.IF:
            return self._if()
        if t is TokenType.WHILE:
            return self._while()
        raise self._error("a statement")

    def _assign(self) -> Assign:
        name = self._advance().value
        self._expect(TokenType.ASSIGN, "'=' after variable name")
        expr = self._expr()
        self._expect(TokenType.SEMI, "';'")
        return Assign(name, expr)

    def _print(self) -> Print:
        self._advance()
        expr = self._expr()
        self._expect(TokenType.SEMI, "';'")
        return Print(expr)

    def _condition(self) -> Node:
        self._expect(TokenType.LPAREN, "'(' before condition")
        cond = self._expr()
        self._expect(TokenType.RPAREN, "')' after condition")
        return cond

    def _if(self) -> If:
        self._advance()
        cond = self._condition()
        then_body = self._block()
        else_body: list[Node] = []
        if self._at(TokenType.ELSE):
            self._advance()
            else_body = self._block()
        return If(cond, then_body, else_body)

    def _while(self) -> While:
        self._advance()
        cond = self._condition()
        return While(cond, self._block())

    def _block(self) -> list[Node]:
        self._expect(TokenType.LBRACE, "'{'")
        body: list[Node] = []
        while not self._at(TokenType.RBRACE):
            if self._at(TokenType.EOF):
                raise self._error("'}' to close block")
            body.append(self._statement())
        self._advance()
        return body

    # -- expressions -------------------------------------------------------

    def _expr(self) -> Node:
        return self._comparison()

    def _comparison(self) -> Node:
        # Non-associative: at most one comparison operator, per the grammar.
        left = self._sum()
        if self._at(*_COMPARE_OPS):
            op = self._advance().value
            left = BinOp(op, left, self._sum())
        return left

    def _sum(self) -> Node:
        left = self._term()
        while self._at(*_SUM_OPS):
            op = self._advance().value
            left = BinOp(op, left, self._term())
        return left

    def _term(self) -> Node:
        left = self._factor()
        while self._at(*_TERM_OPS):
            op = self._advance().value
            left = BinOp(op, left, self._factor())
        return left

    def _factor(self) -> Node:
        tok = self.cur
        if tok.type is TokenType.INT:
            self._advance()
            try:
                return Num(int(tok.value))
            except ValueError:
                raise SyntaxError(
                    f"invalid integer literal {tok.value!r} at offset {tok.pos}"
                ) from None
        if tok.type is TokenType.IDENT:
            self._advance()
            return Var(tok.value)
        if tok.type is TokenType.LPAREN:
            self._advance()
            inner = self._expr()
            self._expect(TokenType.RPAREN, "')'")
            return inner
        raise self._error("an expression")
