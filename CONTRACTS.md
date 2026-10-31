# Layer contracts — build against these, don't change them

`rewind` is split into four layers. Each is **one module + one test file**,
built independently against the three frozen contract modules
(`rewind/tokens.py`, `rewind/ast_nodes.py`, `rewind/timeline.py`). You can
build and test your layer **without** the other three existing — construct
your inputs directly from the contract types.

Do not edit another layer's files or the frozen contracts. Do not add
third-party dependencies (standard library only, Python 3.10+).

## Layer A — Lexer → `rewind/lexer.py`, tested by `tests/test_lexer.py`

```python
from rewind.tokens import Token, TokenType
def tokenize(src: str) -> list[Token]: ...
```

Turn source text into a list of `Token`. Skip spaces/tabs/newlines. Support
`# ...` line comments. Recognise ints, identifiers/keywords (see
`tokens.KEYWORDS`), the operators (note `==` vs `=`), and `( ) { } ;`. Each
token's `pos` is the 0-based offset where it starts. The final token is
`Token(TokenType.EOF, "", len(src))`. Raise `SyntaxError` with the offset on
an unexpected character.

## Layer B — Parser → `rewind/parser.py`, tested by `tests/test_parser.py`

```python
from rewind.tokens import Token
from rewind.ast_nodes import Program
def parse(tokens: list[Token]) -> Program: ...
```

Consume a token list (ending in EOF) and build the AST per the grammar in
`ast_nodes.py`. Operator precedence: `* /` bind tighter than `+ -`, which
bind tighter than the comparisons `< > ==`. `if`/`while` conditions are
parenthesised; bodies are `{ ... }` blocks. Raise `SyntaxError` on malformed
input. You can build your test inputs by calling your own lexer is **not**
allowed (it may not exist yet) — construct `Token`s directly, or paste a
known token list.

## Layer C — Interpreter + recorder → `rewind/interpreter.py`, tested by `tests/test_interpreter.py`

```python
from rewind.ast_nodes import Program
from rewind.timeline import Timeline

def run(program: Program, timeline: Timeline | None = None) -> dict[str, int]: ...
def run_collect(program: Program, timeline: Timeline | None = None) -> tuple[dict[str, int], list[int]]: ...
```

Walk the `Program` and execute it against an environment `dict[str, int]`.

- Expressions are integer-valued: `+ - * /` (use integer division for `/`,
  and raise `ZeroDivisionError` on divide-by-zero); comparisons `< > ==`
  yield `1` or `0`; a `Var` never assigned raises `NameError`.
- `if`/`while` treat any non-zero condition value as true.
- Recording: if a `timeline` is passed, record ONE snapshot
  `timeline.record("start", env)` *before* executing (step 0 = empty start),
  then after **every executed statement** call `timeline.record(desc, env)`
  with a short `desc` — e.g. `"x = 5"`, `"print x"`, `"while cond"`. A loop
  body that runs N times records N sets of snapshots; that is what makes the
  timeline scrubbable.
- `run` returns the final environment dict.
- `run_collect` does the same but also returns the list of ints produced by
  `print` statements, in order: `(env, prints)`. Implement `run` in terms of
  `run_collect` (or vice-versa) so they never diverge. `print` writes nothing
  to stdout from `run_collect` — it only collects (the CLI handles display).

## Layer D — Time-travel debugger → `rewind/debugger.py`, tested by `tests/test_debugger.py`

```python
from rewind.timeline import Timeline, Snapshot
class TimeTravelDebugger:
    def __init__(self, timeline: Timeline) -> None: ...
    def step(self, n: int = 1) -> Snapshot | None: ...      # scrub forward
    def back(self, n: int = 1) -> Snapshot | None: ...      # scrub backward
    def goto(self, step: int) -> Snapshot | None: ...
    def to_start(self) -> Snapshot | None: ...
    def to_end(self) -> Snapshot | None: ...
    def format_current(self) -> str: ...   # e.g. "step 3/7  x=5 y=2  (x = 5)"
    def diff(self) -> dict[str, tuple[int | None, int | None]]: ...
        # vars that changed from the previous step -> (old, new)
```

Drive the `Timeline`'s cursor (don't re-implement the list). Build your test
timelines by constructing `Timeline()` and calling `.record(...)` with fake
envs — you do not need the interpreter. `diff()` compares the current step to
the previous one (empty at step 0).

> The glue `rewind/__main__.py` (lexer → parser → interpreter → debugger CLI)
> is written and owned by the parent/integrator. You don't need to touch it;
> it starts working once all four modules land.
