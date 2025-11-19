"""Command line entrypoint for running the FastAPI application with uvicorn."""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

import uvicorn


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


def main(argv: Sequence[str] | None = None) -> None:
    """Parse CLI arguments and launch the uvicorn server."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.ssl_certfile and not args.ssl_keyfile:
        parser.error("--ssl-keyfile is required when --ssl-certfile is provided")
    if args.ssl_keyfile and not args.ssl_certfile:
        parser.error("--ssl-certfile is required when --ssl-keyfile is provided")

    uvicorn.run(
        "modules.webapi.application:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
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
