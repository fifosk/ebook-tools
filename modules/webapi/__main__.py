"""Command line entrypoint for running the FastAPI application with uvicorn."""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any, Sequence

import uvicorn

# Uvicorn logging configuration that reduces console verbosity
# Access logs are suppressed by default; errors and system status are shown
QUIET_LOG_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "WARNING", "propagate": False},
    },
}

# Verbose log config - shows access logs at INFO level
VERBOSE_LOG_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for the web API runner."""

    parser = argparse.ArgumentParser(
        description="Run the ebook-tools FastAPI application with uvicorn",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Hostname or IP address for the uvicorn server (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="TCP port for the uvicorn server (default: %(default)s)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload; useful during local development.",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level passed to uvicorn (default: %(default)s)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Reduce console output; suppress access logs and routine events. Errors and system status are still shown.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show all logs including access logs and detailed events.",
    )
    parser.add_argument(
        "--ssl-certfile",
        help="Path to the TLS certificate file (PEM). Enables HTTPS when provided.",
    )
    parser.add_argument(
        "--ssl-keyfile",
        help="Path to the TLS private key file (PEM). Required when --ssl-certfile is set.",
    )
    parser.add_argument(
        "--ssl-keyfile-password",
        help="Password for the encrypted TLS private key, if applicable.",
    )
    return parser


def _configure_app_logging(quiet: bool, verbose: bool) -> None:
    """Configure the application's ebook_tools logger for console verbosity."""
    from modules import logging_manager

    if quiet:
        # Enable quiet mode - suppresses INFO/DEBUG from console, keeps file logs
        logging_manager.set_console_quiet_mode(True)
    elif verbose:
        # In verbose mode, ensure quiet mode is off and set to DEBUG
        logging_manager.set_console_quiet_mode(False)
        logger = logging_manager.get_logger()
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
    else:
        # Default: quiet mode off, normal INFO level
        logging_manager.set_console_quiet_mode(False)


def main(argv: Sequence[str] | None = None) -> None:
    """Parse CLI arguments and launch the uvicorn server."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.ssl_certfile and not args.ssl_keyfile:
        parser.error("--ssl-keyfile is required when --ssl-certfile is provided")
    if args.ssl_keyfile and not args.ssl_certfile:
        parser.error("--ssl-certfile is required when --ssl-keyfile is provided")

    # Determine quiet mode from args or environment
    quiet_mode = args.quiet or os.environ.get("EBOOK_API_QUIET", "").lower() in ("1", "true", "yes")
    verbose_mode = args.verbose or os.environ.get("EBOOK_API_VERBOSE", "").lower() in ("1", "true", "yes")

    # Verbose overrides quiet
    if verbose_mode:
        quiet_mode = False

    # Select log configuration
    if quiet_mode:
        log_config = QUIET_LOG_CONFIG
        _configure_app_logging(quiet=True, verbose=False)
    elif verbose_mode:
        log_config = VERBOSE_LOG_CONFIG
        _configure_app_logging(quiet=False, verbose=True)
    else:
        # Default: quiet mode (reduced verbosity)
        log_config = QUIET_LOG_CONFIG
        _configure_app_logging(quiet=True, verbose=False)

    # Print startup banner (always shown)
    protocol = "https" if args.ssl_certfile else "http"
    host_display = "localhost" if args.host == "0.0.0.0" else args.host
    print(f"Starting ebook-tools API at {protocol}://{host_display}:{args.port}", flush=True)
    if quiet_mode:
        print("Console output: quiet mode (errors and warnings only). Full logs in log/app.log", flush=True)

    uvicorn.run(
        "modules.webapi.application:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        log_config=log_config,
        factory=True,
        ssl_certfile=args.ssl_certfile,
        ssl_keyfile=args.ssl_keyfile,
        ssl_keyfile_password=args.ssl_keyfile_password,
    )


if __name__ == "__main__":  # pragma: no cover - CLI integration
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - user initiated shutdown
        logging.getLogger(__name__).info("Server interrupted by user")
