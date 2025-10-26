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
        "--llm-source",
        choices=["local", "cloud"],
        help="Select the LLM endpoint source (local or cloud).",
    )
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
        "--video-backend",
        choices=["ffmpeg", "golang"],
        help="Select the backend used for video assembly.",
    )
    parser.add_argument(
        "--video-backend-executable",
        help="Override the executable used by the selected video backend.",
    )
    parser.add_argument(
        "--video-backend-loglevel",
        help="Override the log level passed to the video backend executable.",
    )
    parser.add_argument(
        "--video-backend-preset",
        action="append",
        metavar="NAME=VALUES",
        help=(
            "Override a video backend preset (repeatable). "
            "Values are comma-separated command arguments."
        ),
    )
    parser.add_argument(
        "--tts-backend",
        choices=["auto", "macos", "gtts"],
        help="Select the text-to-speech backend (auto, macos, or gtts).",
    )
    parser.add_argument(
        "--tts-executable",
        help="Override the executable path used by the configured TTS backend.",
    )
    parser.add_argument(
        "--say-path",
        help="Explicit path to the macOS 'say' binary when using the macOS backend.",
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

    user_parser = subparsers.add_parser(
        "user", help="Manage ebook-tools user accounts", allow_abbrev=False
    )
    user_parser.add_argument(
        "--store",
        dest="user_store",
        help="Path to the user store JSON file (defaults to config/users/users.json).",
    )
    user_parser.add_argument(
        "--session-file",
        dest="session_file",
        help="Path to the session storage file (defaults to ~/.ebooktools_session.json).",
    )
    user_parser.add_argument(
        "--active-session-file",
        dest="active_session_file",
        help="Path to the active session token file (defaults to ~/.ebooktools_active_session).",
    )
    user_parser.set_defaults(command="user")

    user_subparsers = user_parser.add_subparsers(dest="user_command", required=True)

    add_parser = user_subparsers.add_parser(
        "add", help="Create a new user account", allow_abbrev=False
    )
    add_parser.add_argument("username", help="Username for the new account.")
    add_parser.add_argument(
        "--password",
        help="Password for the new account (prompts interactively when omitted).",
    )
    add_parser.add_argument(
        "--role",
        dest="roles",
        action="append",
        help="Assign a role to the new account (repeatable).",
    )

    list_parser = user_subparsers.add_parser(
        "list", help="List registered user accounts", allow_abbrev=False
    )
    list_parser.set_defaults(user_command="list")

    login_parser = user_subparsers.add_parser(
        "login", help="Authenticate and create a new session", allow_abbrev=False
    )
    login_parser.add_argument("username", help="Username to authenticate.")
    login_parser.add_argument(
        "--password",
        help="Password for the account (prompts interactively when omitted).",
    )

    password_parser = user_subparsers.add_parser(
        "password", help="Update the password for an existing account", allow_abbrev=False
    )
    password_parser.add_argument("username", help="Account whose password should change.")
    password_parser.add_argument(
        "--password",
        help="New password to set (prompts interactively when omitted).",
    )

    logout_parser = user_subparsers.add_parser(
        "logout", help="Terminate an existing session", allow_abbrev=False
    )
    logout_parser.add_argument(
        "--token",
        help="Session token to revoke (defaults to the active session token).",
    )

    return parser


def parse_cli_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse ``argv`` using the new CLI parser with sub-commands."""

    parser = build_cli_parser()

    try:
        # ``parse_known_args`` lets us detect legacy invocations like ``-i``
        # without triggering an early ``SystemExit`` from ``argparse``.
        preliminary, unknown = parser.parse_known_args(argv)
    except SystemExit:
        return parse_legacy_args(argv)

    if getattr(preliminary, "command", None) is None:
        # No sub-command detected; assume legacy positional usage.
        return parse_legacy_args(argv)

    if unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")

    namespace = parser.parse_args(argv)
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
