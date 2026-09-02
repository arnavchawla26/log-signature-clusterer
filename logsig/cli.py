"""Command-line entry point: ``logsig``."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .cluster import ClusterEngine
from .report import RENDERERS
from .tokenize import tokenize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logsig",
        description=(
            "Cluster a raw log file into its distinct signatures, ranked "
            "by frequency. Pass '-' (or omit the file) to read stdin."
        ),
    )
    parser.add_argument(
        "logfile",
        nargs="?",
        default="-",
        help="Path to a log file to read (default: stdin, or pass '-')",
    )
    parser.add_argument(
        "--format",
        choices=sorted(RENDERERS),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--similarity",
        type=float,
        default=0.5,
        metavar="0..1",
        help=(
            "Minimum fraction of matching tokens for a line to join an "
            "existing cluster instead of starting a new one (default: 0.5)"
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Only show the N most frequent signatures",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=None,
        metavar="N",
        help="Only show signatures that matched at least N lines",
    )
    return parser


def _read_lines(path: str) -> list[str]:
    if path == "-":
        return sys.stdin.readlines()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.readlines()


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw_lines = _read_lines(args.logfile)
    except OSError as exc:
        print(f"logsig: cannot read '{args.logfile}': {exc}", file=sys.stderr)
        return 2

    try:
        engine = ClusterEngine(similarity_threshold=args.similarity)
    except ValueError as exc:
        print(f"logsig: {exc}", file=sys.stderr)
        return 2

    for line_no, raw in enumerate(raw_lines, start=1):
        engine.add_line(raw.rstrip("\n"), tokenize(raw), line_no)

    renderer = RENDERERS[args.format]
    output = renderer(engine, top=args.top, min_count=args.min_count)
    sys.stdout.write(output)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
