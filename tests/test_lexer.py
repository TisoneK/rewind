"""Tests for Layer A — the lexer."""
import pytest

from rewind.lexer import tokenize
from rewind.tokens import KEYWORDS, Token, TokenType

T = TokenType


def types(src):
    return [t.type for t in tokenize(src)]


def values(src):
    return [t.value for t in tokenize(src)]


def test_empty_source_is_just_eof():
    assert tokenize("") == [Token(T.EOF, "", 0)]


def test_whitespace_and_comments_only():
    src = "  \t\n# nothing here\n   "
    assert tokenize(src) == [Token(T.EOF, "", len(src))]


def test_eof_is_last_with_pos_len_src():
    src = "x = 1;"
    toks = tokenize(src)
    assert toks[-1] == Token(T.EOF, "", len(src))
    assert all(t.type is not T.EOF for t in toks[:-1])


@pytest.mark.parametrize("src", ["0", "7", "42", "1234567890", "007"])
def test_ints(src):
    assert tokenize(src) == [Token(T.INT, src, 0), Token(T.EOF, "", len(src))]


def test_negative_is_minus_then_int():
    assert types("-5") == [T.MINUS, T.INT, T.EOF]


@pytest.mark.parametrize("name", ["x", "total", "_tmp", "a1", "x_y_2", "Print", "IF", "printx", "iffy"])
def test_identifiers(name):
    assert tokenize(name)[0] == Token(T.IDENT, name, 0)


@pytest.mark.parametrize("word,tt", sorted(KEYWORDS.items()))
def test_keywords(word, tt):
    assert tokenize(word) == [Token(tt, word, 0), Token(T.EOF, "", len(word))]


def test_keywords_match_contract_set():
    assert set(KEYWORDS) == {"print", "if", "else", "while"}


@pytest.mark.parametrize(
    "src,tt",
    [
        ("+", T.PLUS), ("-", T.MINUS), ("*", T.STAR), ("/", T.SLASH),
        ("=", T.ASSIGN), ("==", T.EQ), ("<", T.LT), (">", T.GT),
        ("(", T.LPAREN), (")", T.RPAREN), ("{", T.LBRACE), ("}", T.RBRACE),
        (";", T.SEMI),
    ],
)
def test_each_operator_and_punctuation(src, tt):
    assert tokenize(src) == [Token(tt, src, 0), Token(T.EOF, "", len(src))]


def test_eq_vs_assign():
    assert types("a == b") == [T.IDENT, T.EQ, T.IDENT, T.EOF]
    assert types("a = b") == [T.IDENT, T.ASSIGN, T.IDENT, T.EOF]
    assert types("a=b") == [T.IDENT, T.ASSIGN, T.IDENT, T.EOF]
    assert types("a==b") == [T.IDENT, T.EQ, T.IDENT, T.EOF]


def test_triple_equals_is_eq_then_assign():
    assert types("===") == [T.EQ, T.ASSIGN, T.EOF]
    assert types("= =") == [T.ASSIGN, T.ASSIGN, T.EOF]


def test_adjacent_tokens_without_spaces():
    assert types("(1+2)*x;") == [
        T.LPAREN, T.INT, T.PLUS, T.INT, T.RPAREN, T.STAR, T.IDENT, T.SEMI, T.EOF,
    ]


def test_int_followed_by_ident_splits():
    assert tokenize("12ab")[:2] == [Token(T.INT, "12", 0), Token(T.IDENT, "ab", 2)]


def test_comment_runs_to_end_of_line():
    toks = tokenize("x = 1; # y = 2;\nz = 3;")
    assert [t.value for t in toks if t.type is T.IDENT] == ["x", "z"]


def test_comment_at_eof_without_newline():
    assert types("x # trailing") == [T.IDENT, T.EOF]


def test_comment_may_contain_any_chars():
    assert types("# $ @ ! ` ~ é\n1") == [T.INT, T.EOF]


def test_hash_inside_line_starts_comment():
    assert types("1#2") == [T.INT, T.EOF]


def test_all_whitespace_kinds_skipped():
    assert types("a\tb\nc\r\nd  e") == [T.IDENT] * 5 + [T.EOF]


def test_pos_offsets():
    src = "x = 10;\nprint x;"
    got = [(t.type, t.value, t.pos) for t in tokenize(src)]
    assert got == [
        (T.IDENT, "x", 0),
        (T.ASSIGN, "=", 2),
        (T.INT, "10", 4),
        (T.SEMI, ";", 6),
        (T.PRINT, "print", 8),
        (T.IDENT, "x", 14),
        (T.SEMI, ";", 15),
        (T.EOF, "", 16),
    ]


def test_pos_after_comment_and_eq():
    src = "# c\na == 1"
    got = [(t.value, t.pos) for t in tokenize(src)]
    assert got == [("a", 4), ("==", 6), ("1", 9), ("", 10)]


def test_pos_points_at_source_text():
    src = "while (n > 0) { n = n - 1; }  # done"
    for t in tokenize(src)[:-1]:
        assert src[t.pos : t.pos + len(t.value)] == t.value


def test_full_program():
    src = """
    # factorial
    n = 5; acc = 1;
    while (n > 0) { acc = acc * n; n = n - 1; }
    if (acc == 120) { print acc; } else { print 0; }
    """
    assert values(src)[:-1] == [
        "n", "=", "5", ";", "acc", "=", "1", ";",
        "while", "(", "n", ">", "0", ")", "{", "acc", "=", "acc", "*", "n", ";",
        "n", "=", "n", "-", "1", ";", "}",
        "if", "(", "acc", "==", "120", ")", "{", "print", "acc", ";", "}",
        "else", "{", "print", "0", ";", "}",
    ]


def test_returns_list_of_tokens():
    toks = tokenize("x")
    assert isinstance(toks, list)
    assert all(isinstance(t, Token) for t in toks)


@pytest.mark.parametrize("bad", ["@", "$", "!", "&", "|", "%", "[", "]", ".", ",", ":", '"', "'", "é"])
def test_bad_char_raises_syntax_error(bad):
    with pytest.raises(SyntaxError):
        tokenize(bad)


def test_bad_char_error_mentions_offset_and_char():
    with pytest.raises(SyntaxError) as exc:
        tokenize("x = 1 @ 2")
    assert "offset 6" in str(exc.value)
    assert "'@'" in str(exc.value)


def test_bad_char_after_comment_line_reports_correct_offset():
    with pytest.raises(SyntaxError, match="offset 6"):
        tokenize("# c\n  $")


def test_bang_alone_is_error_not_neq():
    with pytest.raises(SyntaxError):
        tokenize("a != b")


def test_non_ascii_letters_not_identifiers():
    with pytest.raises(SyntaxError):
        tokenize("café")
    with pytest.raises(SyntaxError):
        tokenize("١")  # Arabic-indic digit one
