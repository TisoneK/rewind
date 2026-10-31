"""Command-line entry point — composes the four layers.

    python -m rewind run    <file.peb>   # execute, show printed output
    python -m rewind replay <file.peb>   # execute, then scrub the whole
                                          # timeline forward AND backward,
                                          # printing the state at each step
                                          # (this is the time-travel demo)

Owned by the integrator, not by a single layer. It imports every layer, so
it only works once the lexer, parser, interpreter and debugger modules all
exist; until then it prints which layer is missing.
"""
from __future__ import annotations

import sys

from .timeline import Timeline


def _load_layers():
    try:
        from .lexer import tokenize
        from .parser import parse
        from .interpreter import run_collect
        from .debugger import TimeTravelDebugger
    except ImportError as exc:  # a layer is not built yet
        raise SystemExit(f"rewind: a layer is not available yet: {exc}")
    return tokenize, parse, run_collect, TimeTravelDebugger


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] not in ("run", "replay"):
        print(__doc__)
        return 2
    cmd, path = argv
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    tokenize, parse, run_collect, TimeTravelDebugger = _load_layers()

    program = parse(tokenize(src))
    timeline = Timeline()
    env, prints = run_collect(program, timeline)

    if cmd == "run":
        for value in prints:
            print(value)
        return 0

    # replay: scrub forward through the whole run, then rewind to the start.
    dbg = TimeTravelDebugger(timeline)
    print(f"=== {path}: {len(timeline)} steps recorded ===")
    print("--- forward ---")
    dbg.to_start()
    while True:
        print("  " + dbg.format_current())
        if timeline.cursor >= len(timeline) - 1:
            break
        dbg.step()
    print("--- rewind ---")
    while timeline.cursor > 0:
        dbg.back()
        print("  " + dbg.format_current())
    print(f"final env: {env}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
