"""Tests for Layer B (parser). Inputs are built from Token objects directly —
the lexer is deliberately not imported."""
import pytest

from rewind.ast_nodes import Assign, BinOp, If, Num, Print, Program, Var, While
from rewind.parser import parse
from rewind.tokens import KEYWORDS, Token, TokenType

_SYMBOLS = {
    "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR,
    "/": TokenType.SLASH, "=": TokenType.ASSIGN, "==": TokenType.EQ,
    "<": TokenType.LT, ">": TokenType.GT, "(": TokenType.LPAREN,
    ")": TokenType.RPAREN, "{": TokenType.LBRACE, "}": TokenType.RBRACE,
    ";": TokenType.SEMI,
}


def toks(spec: str, eof: bool = True) -> list[Token]:
    """Build tokens from a whitespace-separated spec, e.g. 'x = 1 + 2 ;'.

    A stand-in for the lexer: each word is already one lexeme.
    """
    out = []
    for n, word in enumerate(spec.split()):
        if word in _SYMBOLS:
            t = _SYMBOLS[word]
        elif word in KEYWORDS:
            t = KEYWORDS[word]
        elif word.isdigit():
            t = TokenType.INT
        else:
            t = TokenType.IDENT
        out.append(Token(t, word, n * 2))
    if eof:
        out.append(Token(TokenType.EOF, "", len(spec)))
    return out


def expr(spec: str):
    """Parse `print <spec> ;` and return the printed expression."""
    (stmt,) = parse(toks(f"print {spec} ;")).body
    assert isinstance(stmt, Print)
    return stmt.expr


# --- programs and simple statements ---------------------------------------

def test_empty_program():
    assert parse(toks("")) == Program([])


def test_assign_number():
    assert parse(toks("x = 5 ;")) == Program([Assign("x", Num(5))])


def test_assign_variable():
    assert parse(toks("x = y ;")) == Program([Assign("x", Var("y"))])


def test_print_statement():
    assert parse(toks("print x ;")) == Program([Print(Var("x"))])


def test_multiple_statements_in_order():
    prog = parse(toks("a = 1 ; b = 2 ; print a ;"))
    assert prog.body == [Assign("a", Num(1)), Assign("b", Num(2)), Print(Var("a"))]


def test_integer_literal_converted_to_int():
    node = expr("007")
    assert node == Num(7) and isinstance(node.value, int)


def test_returns_program_instance():
    assert isinstance(parse(toks("x = 1 ;")), Program)


# --- expressions: precedence and associativity -----------------------------

def test_mul_binds_tighter_than_add():
    assert expr("1 + 2 * 3") == BinOp("+", Num(1), BinOp("*", Num(2), Num(3)))


def test_mul_on_left_of_add():
    assert expr("1 * 2 + 3") == BinOp("+", BinOp("*", Num(1), Num(2)), Num(3))


def test_div_binds_tighter_than_sub():
    assert expr("8 - 4 / 2") == BinOp("-", Num(8), BinOp("/", Num(4), Num(2)))


def test_addition_is_left_associative():
    assert expr("1 + 2 + 3") == BinOp("+", BinOp("+", Num(1), Num(2)), Num(3))


def test_subtraction_is_left_associative():
    assert expr("10 - 3 - 2") == BinOp("-", BinOp("-", Num(10), Num(3)), Num(2))


def test_mixed_add_sub_left_to_right():
    assert expr("1 - 2 + 3") == BinOp("+", BinOp("-", Num(1), Num(2)), Num(3))


def test_division_is_left_associative():
    assert expr("8 / 4 / 2") == BinOp("/", BinOp("/", Num(8), Num(4)), Num(2))


def test_mixed_mul_div_left_to_right():
    assert expr("8 / 4 * 2") == BinOp("*", BinOp("/", Num(8), Num(4)), Num(2))


@pytest.mark.parametrize("op", ["<", ">", "=="])
def test_comparison_looser_than_arithmetic(op):
    assert expr(f"a + 1 {op} b * 2") == BinOp(
        op, BinOp("+", Var("a"), Num(1)), BinOp("*", Var("b"), Num(2))
    )


@pytest.mark.parametrize("op", ["<", ">", "=="])
def test_simple_comparison(op):
    assert expr(f"x {op} 3") == BinOp(op, Var("x"), Num(3))


@pytest.mark.parametrize("op", ["<", ">", "=="])
def test_comparison_is_non_associative(op):
    # grammar allows at most one comparison operator per expression
    with pytest.raises(SyntaxError):
        parse(toks(f"print a {op} b {op} c ;"))


def test_chained_different_comparisons_rejected():
    with pytest.raises(SyntaxError):
        parse(toks("print a < b > c ;"))


def test_parentheses_override_precedence():
    assert expr("( 1 + 2 ) * 3") == BinOp("*", BinOp("+", Num(1), Num(2)), Num(3))


def test_parentheses_on_right_operand():
    assert expr("10 - ( 3 - 2 )") == BinOp("-", Num(10), BinOp("-", Num(3), Num(2)))


def test_nested_parentheses():
    assert expr("( ( 1 ) )") == Num(1)


def test_parenthesised_comparison_as_operand():
    assert expr("( a < b ) + 1") == BinOp("+", BinOp("<", Var("a"), Var("b")), Num(1))


def test_comparison_of_parenthesised_comparisons():
    assert expr("( a < b ) == ( c > d )") == BinOp(
        "==", BinOp("<", Var("a"), Var("b")), BinOp(">", Var("c"), Var("d"))
    )


def test_long_expression():
    # a + b * c - d / e
    assert expr("a + b * c - d / e") == BinOp(
        "-",
        BinOp("+", Var("a"), BinOp("*", Var("b"), Var("c"))),
        BinOp("/", Var("d"), Var("e")),
    )


# --- if / else -------------------------------------------------------------

def test_if_without_else():
    prog = parse(toks("if ( x ) { y = 1 ; }"))
    assert prog.body == [If(Var("x"), [Assign("y", Num(1))], [])]


def test_if_with_else():
    prog = parse(toks("if ( x < 3 ) { y = 1 ; } else { y = 2 ; }"))
    assert prog.body == [
        If(BinOp("<", Var("x"), Num(3)), [Assign("y", Num(1))], [Assign("y", Num(2))])
    ]


def test_if_empty_blocks():
    assert parse(toks("if ( x ) { } else { }")).body == [If(Var("x"), [], [])]


def test_if_multiple_statements_in_blocks():
    prog = parse(toks("if ( x ) { a = 1 ; print a ; } else { b = 2 ; print b ; }"))
    (node,) = prog.body
    assert node.then_body == [Assign("a", Num(1)), Print(Var("a"))]
    assert node.else_body == [Assign("b", Num(2)), Print(Var("b"))]


def test_statement_after_if_is_outside_it():
    prog = parse(toks("if ( x ) { a = 1 ; } b = 2 ;"))
    assert prog.body == [If(Var("x"), [Assign("a", Num(1))], []), Assign("b", Num(2))]


def test_else_if_requires_block():
    # `else if` is not in the grammar: else must be followed by a block
    with pytest.raises(SyntaxError):
        parse(toks("if ( x ) { } else if ( y ) { }"))


def test_else_binds_to_nearest_if():
    prog = parse(toks("if ( a ) { if ( b ) { x = 1 ; } else { x = 2 ; } }"))
    (outer,) = prog.body
    assert outer.else_body == []
    (inner,) = outer.then_body
    assert inner.else_body == [Assign("x", Num(2))]


# --- while -----------------------------------------------------------------

def test_while_loop():
    prog = parse(toks("while ( n > 0 ) { n = n - 1 ; }"))
    assert prog.body == [
        While(
            BinOp(">", Var("n"), Num(0)),
            [Assign("n", BinOp("-", Var("n"), Num(1)))],
        )
    ]


def test_while_empty_body():
    assert parse(toks("while ( x ) { }")).body == [While(Var("x"), [])]


def test_nested_blocks():
    prog = parse(toks("while ( a ) { if ( b ) { print c ; } a = a - 1 ; }"))
    (loop,) = prog.body
    assert loop.body == [
        If(Var("b"), [Print(Var("c"))], []),
        Assign("a", BinOp("-", Var("a"), Num(1))),
    ]


def test_deeply_nested_while():
    prog = parse(toks("while ( a ) { while ( b ) { while ( c ) { print 1 ; } } }"))
    node = prog.body[0]
    for _ in range(2):
        assert isinstance(node, While)
        node = node.body[0]
    assert node == While(Var("c"), [Print(Num(1))])


# --- whole programs (the shipped examples, as token lists) ----------------

def test_countdown_program():
    src = "n = 5 ; while ( n > 0 ) { print n ; n = n - 1 ; } print n ;"
    assert parse(toks(src)) == Program([
        Assign("n", Num(5)),
        While(
            BinOp(">", Var("n"), Num(0)),
            [Print(Var("n")), Assign("n", BinOp("-", Var("n"), Num(1)))],
        ),
        Print(Var("n")),
    ])


def test_fib_program():
    src = (
        "a = 0 ; b = 1 ; while ( a < 50 ) { print a ; "
        "next = a + b ; a = b ; b = next ; }"
    )
    prog = parse(toks(src))
    assert len(prog.body) == 3
    loop = prog.body[2]
    assert isinstance(loop, While)
    assert loop.cond == BinOp("<", Var("a"), Num(50))
    assert loop.body[1] == Assign("next", BinOp("+", Var("a"), Var("b")))


# --- error handling --------------------------------------------------------

@pytest.mark.parametrize("spec", [
    "x = 5",                      # missing semicolon
    "x = ;",                      # missing expression
    "= 5 ;",                      # missing target
    "5 = x ;",                    # number is not an assignment target
    "x 5 ;",                      # missing '='
    "x == 5 ;",                   # '==' is not assignment
    "print ;",                    # print without expression
    "print x",                    # print missing semicolon
    "x = 1 + ;",                  # dangling operator
    "x = * 2 ;",                  # leading binary operator
    "x = - 2 ;",                  # unary minus is not in the grammar
    "x = ( 1 + 2 ;",              # unclosed paren
    "x = 1 + 2 ) ;",              # stray close paren
    "x = ( ) ;",                  # empty parens
    "x = 1 2 ;",                  # two operands, no operator
    "x = 1 ; ;",                  # empty statement
    "; ",                         # lone semicolon
    "}",                          # stray close brace
    "{ x = 1 ; }",                # bare block is not a statement
    "if x { }",                   # condition not parenthesised
    "if ( x ) y = 1 ;",           # body not a block
    "if ( x ) { y = 1 ;",         # unclosed block
    "if ( ) { }",                 # empty condition
    "if ( x ) { } else y = 1 ;",  # else body not a block
    "else { }",                   # else without if
    "while x { }",                # while condition not parenthesised
    "while ( x ) y = 1 ;",        # while body not a block
    "while ( x ) {",              # unclosed block at EOF
    "while ( x )",                # missing body
    "while ( x ) { } }",          # extra close brace
    "if",                         # truncated
    "print print ;",              # keyword as expression
    "x = if ;",                   # keyword as expression
])
def test_malformed_input_raises_syntax_error(spec):
    with pytest.raises(SyntaxError):
        parse(toks(spec))


def test_missing_eof_token_rejected():
    with pytest.raises(SyntaxError):
        parse(toks("x = 1 ;", eof=False))


def test_empty_token_list_rejected():
    with pytest.raises(SyntaxError):
        parse([])


def test_error_message_reports_offset():
    tokens = [
        Token(TokenType.IDENT, "x", 10),
        Token(TokenType.ASSIGN, "=", 12),
        Token(TokenType.SEMI, ";", 14),
        Token(TokenType.EOF, "", 15),
    ]
    with pytest.raises(SyntaxError, match="offset 14"):
        parse(tokens)


def test_error_at_eof_reports_end_of_input():
    tokens = [
        Token(TokenType.PRINT, "print", 0),
        Token(TokenType.IDENT, "x", 6),
        Token(TokenType.EOF, "", 7),
    ]
    with pytest.raises(SyntaxError, match="end of input at offset 7"):
        parse(tokens)


def test_parse_does_not_mutate_input():
    tokens = toks("x = 1 + 2 ;")
    before = list(tokens)
    parse(tokens)
    assert tokens == before
