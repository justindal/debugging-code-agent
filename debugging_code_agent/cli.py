from __future__ import annotations

import argparse

from debugging_code_agent.runner import run_selected_problems


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("max-attempts must be >= 1")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(prog="debugging-code-agent")
    parser.add_argument(
        "--max-attempts",
        type=_positive_int,
        default=5,
        help="Maximum solve attempts per selected problem.",
    )
    args = parser.parse_args()
    run_selected_problems(max_attempts=args.max_attempts)
