"""Utility script to troubleshoot Ollama connectivity for ebook-tools."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules import llm_client


def _format_host_chain(chain: Iterable[Tuple[str, Optional[str]]]) -> str:
    parts = []
    for host, api_key in chain:
        status = "present" if api_key else "absent"
        parts.append(f"- {host} (API key {status})")
    return "\n".join(parts) if parts else "<no hosts resolved>"


def _read_prompt(prompt: Optional[str], prompt_file: Optional[str]) -> Optional[str]:
    if prompt:
        return prompt
    if prompt_file:
        with open(prompt_file, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    return None


def _print_environment_summary() -> None:
    api_key_present = "yes" if os.getenv("OLLAMA_API_KEY") else "no"
    configured_url = llm_client.get_api_url()
    print("Environment summary:")
    print(f"  OLLAMA_API_KEY present: {api_key_present}")
    print(f"  Configured API URL   : {configured_url or '<not set>'}")
    print(f"  Active model         : {llm_client.get_model()}")


def _dump_raw(label: str, payload: Any) -> None:
    try:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    except TypeError:
        encoded = repr(payload)
    print(f"\n{label}:\n{encoded}\n")


def run_diagnostic(args: argparse.Namespace) -> int:
    if args.api_url:
        llm_client.set_api_url(args.api_url)
    if args.model:
        llm_client.set_model(args.model)
    if args.debug:
        llm_client.set_debug(True)

    _print_environment_summary()

    if args.show_hosts:
        try:
            host_chain = list(llm_client._resolve_host_chain())  # type: ignore[attr-defined]
        except AttributeError:
            host_chain = []
        print("\nResolved host chain:")
        print(_format_host_chain(host_chain))

    if args.health_check:
        print("\nRunning health check…", end=" ")
        healthy = llm_client.health_check()
        print("ok" if healthy else "failed")
        if not healthy:
            return 1

    prompt = _read_prompt(args.prompt, args.prompt_file)
    if not prompt:
        if args.health_check or args.show_hosts:
            return 0
        print("No prompt supplied. Use --prompt, --prompt-file, or pipe text via stdin.")
        return 1

    payload: dict[str, Any] = {
        "model": llm_client.get_model(),
        "messages": [{"role": "user", "content": prompt}],
        "stream": args.stream,
    }
    if args.system_message:
        payload["messages"].insert(0, {"role": "system", "content": args.system_message})

    print("\nDispatching chat request…")
    response = llm_client.send_chat_request(
        payload,
        max_attempts=args.max_attempts,
        timeout=args.timeout,
        backoff_seconds=args.backoff,
    )

    if response.error:
        print(f"Request failed: {response.error}")
        status = 1
    else:
        print("Request succeeded.")
        print("\nModel response:\n")
        print(response.text or "<empty>")
        status = 0

    if response.token_usage:
        print("\nToken usage:")
        for key, value in response.token_usage.items():
            print(f"  {key}: {value}")

    if args.show_raw and response.raw is not None:
        _dump_raw("Raw response payload", response.raw)

    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Send a test request to Ollama using the ebook-tools LLM client and "
            "print debugging information."
        )
    )
    parser.add_argument(
        "--prompt",
        "-p",
        "--promt",
        dest="prompt",
        help="Prompt text to send to the model.",
    )
    parser.add_argument("--prompt-file", help="File containing the prompt text.")
    parser.add_argument("--system-message", help="Optional system message to prepend.")
    parser.add_argument("--stream", action="store_true", help="Enable streaming mode for the request.")
    parser.add_argument("--model", help="Override the model name for this run.")
    parser.add_argument("--api-url", help="Override the Ollama API URL for this run.")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum retry attempts.")
    parser.add_argument("--timeout", type=int, help="Per-request timeout in seconds.")
    parser.add_argument("--backoff", type=float, default=1.0, help="Retry backoff multiplier in seconds.")
    parser.add_argument(
        "--show-hosts",
        action="store_true",
        help="Display the resolved host chain before executing the request.",
    )
    parser.add_argument(
        "--show-raw",
        action="store_true",
        help="Print the raw response payload for troubleshooting.",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run the built-in health check before sending the prompt.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable verbose LLM client logging.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_diagnostic(args)
    except KeyboardInterrupt:
        print("Aborted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
