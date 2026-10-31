# rewind

A **time-travel debugger** for a small toy language called **Pebble**.

Most debuggers only step *forward*: once a value changes, the old value is
gone. `rewind` records a snapshot of the entire program state after every
step as it runs, so you can scrub the cursor **backward** as freely as
forward — rewind to the moment a variable changed and watch it change again.

```
$ python -m rewind run examples/countdown.peb
5
4
3
2
1

$ python -m rewind replay examples/countdown.peb
=== examples/countdown.peb: 17 steps recorded ===
--- forward ---
  step 0/16    (start)
  step 1/16  n=5    (n = 5)
  step 2/16  n=5    (while cond)
  step 3/16  n=5    (print 5)
  ...
--- rewind ---
  ... state reconstructed backward to step 0 ...
final env: {'n': 0}
```

## The Pebble language

Pebble is deliberately tiny — integers, variables, arithmetic, comparisons,
`print`, `if/else`, and `while`:

```
n = 5;
while (n > 0) {
  print n;
  n = n - 1;
}
```

Full grammar lives in [`rewind/ast_nodes.py`](rewind/ast_nodes.py).

## Architecture

`rewind` is four small layers over three frozen contract modules. The
contracts are what let the layers be built and tested independently:

| Module | Role |
|---|---|
| `rewind/tokens.py` | **contract** — token types + `Token` |
| `rewind/ast_nodes.py` | **contract** — AST node dataclasses + grammar |
| `rewind/timeline.py` | **contract** — `Snapshot` + `Timeline` (the recording spine) |
| `rewind/lexer.py` | layer A — `tokenize(src) -> list[Token]` |
| `rewind/parser.py` | layer B — `parse(tokens) -> Program` |
| `rewind/interpreter.py` | layer C — `run(program, timeline)`; records a snapshot per step |
| `rewind/debugger.py` | layer D — `TimeTravelDebugger`; scrubs the timeline |
| `rewind/__main__.py` | CLI that composes all four |

The recording spine is the heart of it: the interpreter calls
`timeline.record(desc, env)` after each statement, and the debugger drives
the timeline's cursor to move through recorded state. See
[`CONTRACTS.md`](CONTRACTS.md) for each layer's exact signature.

## Developing

Standard library only, Python 3.10+.

```
pip install -e .
pytest          # each layer has its own test file under tests/
python -m rewind replay examples/fib.peb
```

## License

MIT.
