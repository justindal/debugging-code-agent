from __future__ import annotations

import argparse

from debugging_code_agent.llm import Provider
from debugging_code_agent.runner import run_selected_problems

_PROVIDERS: tuple[Provider, ...] = ("ollama", "server", "mlx")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("max-attempts must be >= 1")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(prog="debugging-code-agent")
    parser.add_argument(
        "--provider",
        choices=_PROVIDERS,
        default="ollama",
        help="LLM provider to use: ollama, server, or mlx.",
    )
    parser.add_argument(
        "--model",
        default="llama3.1",
        help="The model to use for the LLM.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Sampling temperature used by the model.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for server/mlx providers (mlx defaults to http://127.0.0.1:8080/v1).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional API key for server/mlx providers.",
    )
    parser.add_argument(
        "--max-attempts",
        type=_positive_int,
        default=5,
        help="Maximum solve attempts per selected problem.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Nucleus sampling probability.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=40,
        help="Top-k sampling cutoff.",
    )
    parser.add_argument(
        "--min-p",
        type=float,
        default=0.0,
        help="Minimum probability threshold (0 disables).",
    )
    parser.add_argument(
        "--repeat-penalty",
        type=float,
        default=1.05,
        help="Penalty applied to repeated tokens.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Sampling seed for reproducibility.",
    )
    args = parser.parse_args()
    if args.provider == "server" and not args.base_url:
        parser.error("--base-url is required when --provider server is used.")
    if not 0.0 < args.top_p <= 1.0:
        parser.error("--top-p must be in (0, 1].")
    if args.top_k < 0:
        parser.error("--top-k must be >= 0.")
    if not 0.0 <= args.min_p < 1.0:
        parser.error("--min-p must be in [0, 1).")
    if args.repeat_penalty <= 0.0:
        parser.error("--repeat-penalty must be > 0.")
    run_selected_problems(
        max_attempts=args.max_attempts,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        base_url=args.base_url,
        api_key=args.api_key,
        top_p=args.top_p,
        top_k=args.top_k,
        min_p=args.min_p,
        repeat_penalty=args.repeat_penalty,
        seed=args.seed,
    )
