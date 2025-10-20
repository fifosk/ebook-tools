"""Argument parsing helpers for the ebook-tools CLI."""

from __future__ import annotations

import argparse
from typing import Optional, Sequence


def _add_shared_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Path to a configuration override JSON file (defaults to conf/config.local.json "
            "if present)."
        ),
    )
    parser.add_argument("--ebooks-dir", help="Directory containing source EPUB files and cover images.")
    parser.add_argument("--working-dir", help="Override the working directory for intermediate files.")
    parser.add_argument("--output-dir", help="Override the output directory for generated files.")
    parser.add_argument("--tmp-dir", help="Override the temporary directory for transient files.")
    parser.add_argument("--ffmpeg-path", help="Override the path to the FFmpeg executable.")
    parser.add_argument("--ollama-url", help="Override the Ollama API URL.")
    parser.add_argument(
        "--thread-count",
        type=int,
        help="Number of worker threads to use for translation and media generation.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging output.")
    return parser


def _add_run_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("input_file", nargs="?", help="Path to the input EPUB file.")
    parser.add_argument("input_language", nargs="?", help="Source language of the EPUB text.")
    parser.add_argument("target_languages", nargs="?", help="Comma-separated list of target languages.")
    parser.add_argument(
        "sentences_per_output_file",
        nargs="?",
        type=int,
        help="Number of sentences per generated output file.",
    )
    parser.add_argument("base_output_file", nargs="?", help="Base path for generated output files.")
    parser.add_argument("start_sentence", nargs="?", type=int, help="Sentence number to start processing from.")
    parser.add_argument(
        "end_sentence",
        nargs="?",
        help="Sentence number (or offset) to stop processing at.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Open the interactive configuration menu.",
    )
    parser.add_argument(
        "--slide-parallelism",
        choices=["off", "auto", "thread", "process"],
        help="Select the backend used for per-frame slide rendering.",
    )
    parser.add_argument(
        "--slide-parallel-workers",
        type=int,
        help="Explicit number of workers to use when slide parallelism is enabled.",
    )
    parser.add_argument(
        "--prefer-pillow-simd",
        action="store_true",
        help="Prefer SIMD-accelerated Pillow builds when rendering slides.",
    )
    parser.add_argument(
        "--benchmark-slide-rendering",
        action="store_true",
        help="Emit timing information for slide rendering operations.",
    )
    parser.add_argument(
        "--template",
        help="Slide template to use for generated videos (e.g. minimal, dark).",
    )
    return _add_shared_arguments(parser)


def build_run_parser() -> argparse.ArgumentParser:
    """Return the legacy parser that powers ``modules.ebook_tools``."""

    parser = argparse.ArgumentParser(
        description="Generate translated outputs from EPUB files.",
        allow_abbrev=False,
    )
    return _add_run_arguments(parser)


def build_cli_parser() -> argparse.ArgumentParser:
    """Build the modern CLI parser with explicit sub-commands."""

    parser = argparse.ArgumentParser(
        description="ebook-tools command line interface", allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Execute the pipeline", allow_abbrev=False)
    _add_run_arguments(run_parser)
    run_parser.set_defaults(command="run")

    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Launch the interactive configuration menu.",
        allow_abbrev=False,
    )
    _add_shared_arguments(interactive_parser)
    interactive_parser.set_defaults(command="interactive", interactive=True)

    return parser


def parse_cli_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse ``argv`` using the new CLI parser with sub-commands."""

    parser = build_cli_parser()
    namespace = parser.parse_args(argv)
    if getattr(namespace, "command", None) is None:
        # Fall back to legacy positional parsing for backwards compatibility.
        return parse_legacy_args(argv)
    if namespace.command == "run" and getattr(namespace, "interactive", False):
        namespace.command = "interactive"
    return namespace


def parse_legacy_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Preserve the original positional argument behaviour."""

    parser = build_run_parser()
    return parser.parse_args(argv)


__all__ = [
    "build_cli_parser",
    "build_run_parser",
    "parse_cli_args",
    "parse_legacy_args",
]
