"""Chess CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from chess.config import AppSettings
from chess.log import get_logger, setup_logging
from chess.paths import DEFAULT_CONFIG

GUI_COMMANDS = frozenset({"play", "play-ai"})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess",
        description="Interactive chess board and minimax AI.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"YAML config path (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Warnings only")
    parser.add_argument("--log-level", default=None, help="Override log level")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("play", help="Free-play sandbox (drag pieces, add from panel)")
    play_ai = subparsers.add_parser("play-ai", help="Play vs minimax AI as White")
    play_ai.add_argument("--depth", type=int, default=None, help="Override ai.depth")
    return parser


def _resolve_log_level(args: argparse.Namespace) -> str:
    if args.log_level:
        return args.log_level
    if args.quiet:
        return "WARNING"
    if args.verbose:
        return "DEBUG"
    return "INFO"


def _load_settings(args: argparse.Namespace) -> AppSettings:
    overrides: dict = {}
    if args.command == "play-ai" and args.depth is not None:
        overrides = {"ai": {"depth": args.depth}}
    return AppSettings.from_yaml(args.config, overrides=overrides or None)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    setup_logging(_resolve_log_level(args))

    settings = _load_settings(args)

    if args.command in GUI_COMMANDS:
        get_logger(__name__).debug(
            "config=%s square_size=%d ai.depth=%d",
            args.config,
            settings.display.square_size,
            settings.ai.depth,
        )
    else:
        from chess.log import log_banner, log_kv_table, log_rule

        log_banner(args.command)
        log_rule("Config")
        log_kv_table(
            "Runtime",
            [
                ("config", str(args.config)),
                ("square_size", str(settings.display.square_size)),
                ("ai.depth", str(settings.ai.depth)),
                ("ai.color", settings.ai.color.name.lower()),
                ("game.promotion", settings.game.promotion.name.lower()),
            ],
        )

    if args.command == "play":
        from chess.ui.sandbox import run_sandbox

        run_sandbox(settings)
    elif args.command == "play-ai":
        from chess.ui.vs_ai import run_vs_ai

        run_vs_ai(settings)
    else:
        parser.error(f"unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
