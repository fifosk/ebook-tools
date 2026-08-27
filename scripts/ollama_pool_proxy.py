#!/usr/bin/env python3
"""Local Ollama adapter: lease a fleet seat and resolve its key for each request.

Only the fixed Ollama API is reachable. Fleet/vendor credentials stay on the host;
the backend holds a separate adapter token. Requires existing, authorized WQ and
central-store clients; neither pool nor credential refusals are bypassed.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LANES = {"ollama-cloud": "fleet/ollama-key", "ollama-gmail": "fleet/ollama-key-gmail"}
MAX_BODY = 2 * 1024 * 1024
MAX_REPLY = 16 * 1024 * 1024


class PoolUnavailable(RuntimeError):
    pass


class Fleet:
    def __init__(self, repo: Path, expected_identity: str):
        self.repo = repo
        self.env = dict(os.environ, COWORK_WQ_BEARER_SOURCE="claude-json")
        identity = self.call("queue_whoami")
        if not identity.get("authorized") or identity.get("identity") != expected_identity:
            raise PoolUnavailable("Configured pool identity does not match")

    def call(self, verb: str, **arguments):
        try:
            result = subprocess.run(
                [str(self.repo / "scripts/run-python.sh"), str(self.repo / "scripts/_lib/wq_client.py"), verb, json.dumps(arguments)],
                env=self.env, capture_output=True, text=True, timeout=30, check=True,
            )
            payload = json.loads(result.stdout)
            if not isinstance(payload, dict):
                raise ValueError()
            return payload
        except (subprocess.SubprocessError, ValueError, OSError):
            raise PoolUnavailable("Pool control request failed") from None

    def key(self, ref: str) -> str:
        if ref not in LANES.values():
            raise PoolUnavailable("Unrecognized seat credential")
        try:
            result = subprocess.run(
                ["/bin/bash", "-c", '. "$1"; central_store_fetch "$2" ebook-tools:subtitle-pool', "_",
                 str(self.repo / "scripts/_lib/central-store-fetch.sh"), ref],
                capture_output=True, text=True, timeout=15, check=True,
            )
            value = result.stdout.strip()
            if len(value) < 16 or any(c.isspace() for c in value):
                raise ValueError()
            return value
        except (subprocess.SubprocessError, ValueError, OSError):
            raise PoolUnavailable("Seat credential unavailable") from None


def upstream(path, payload, key):
    request = urllib.request.Request(
        "https://ollama.com" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read(MAX_REPLY + 1)
            if len(body) > MAX_REPLY:
                raise PoolUnavailable("Provider response too large")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        # Never expose provider error bodies, credentials, or request text.
        status = exc.code
        exc.close()
        return status, {}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise PoolUnavailable("Provider request failed") from None


class PoolAdapter:
    def __init__(self, fleet, send=upstream, clock=time.monotonic):
        self.fleet, self.send, self.clock = fleet, send, clock
        self.cooldowns = {}
        self.lock = threading.Lock()

    def request(self, path, payload=None):
        payload = dict(payload) if payload is not None else None
        if payload is not None:
            payload["stream"] = False  # Buffer before releasing the lease.
            model = payload.get("model", "")
            if not isinstance(model, str) or not model or len(model) > 200:
                return 400, {"error": "A valid model is required"}, None
            # Local Ollama tags use -cloud; the hosted catalog uses bare names.
            if model.endswith("-cloud"):
                payload["model"] = model[:-6]
        else:
            model = "model-inventory"
        tried = set()
        for _ in LANES:
            with self.lock:
                eligible = [a for a in LANES if a not in tried and self.cooldowns.get(a, 0) <= self.clock()]
            if not eligible:
                break
            arguments = {"model": model, "ttl": 600, "session": "ebook-tools"}
            if len(eligible) == 1:
                arguments["account"] = eligible[0]
            grant = self.fleet.call("ollama_acquire", **arguments)
            if grant.get("granted") is not True or not grant.get("lease_id"):
                # Denied means no provider call, including when the limiter is down.
                break
            account = grant.get("account")
            outcome = "failed"
            served_by = ""
            try:
                if account not in eligible or grant.get("seat_ref") != LANES.get(account):
                    raise PoolUnavailable("Pool returned an unexpected seat binding")
                tried.add(account)
                key = self.fleet.key(LANES[account])
                status, body = self.send(path, payload, key)
                served_by = account  # Direct vendor call bound to this leased key.
                del key
                if status == 200:
                    outcome = "success"
                    return status, body, account
                outcome = "quota-429" if status == 429 else "http-" + str(status)
                if status not in (401, 403, 408, 429) and status < 500:
                    return status, {"error": "Ollama rejected the request", "status": status}, account
                with self.lock:
                    self.cooldowns[account] = self.clock() + (300 if status in (401, 403) else 30)
            except PoolUnavailable:
                if account in LANES:
                    tried.add(account)
                    with self.lock:
                        self.cooldowns[account] = self.clock() + 30
                else:
                    raise
            finally:
                try:
                    result = self.fleet.call("ollama_release", lease_id=grant["lease_id"], outcome=outcome, served_by=served_by)
                    if result.get("released") is not True or result.get("binding_verified") is False:
                        print("pool_release_unconfirmed=true", file=sys.stderr, flush=True)
                except PoolUnavailable:
                    # TTL is longer than the bounded provider call; gateway reaps on failure.
                    print("pool_release_failed=true ttl_backstop_seconds=600", file=sys.stderr, flush=True)
        return 503, {"error": "No healthy Ollama cloud seat is available; retry later"}, None


def handler_for(adapter, token):
    capacity = threading.BoundedSemaphore(4)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # No request contents or Authorization in access logs.

        def respond(self, status, body, account=None, streaming=False):
            if streaming and status == 200:
                choices = body.get("choices", [])
                delta = {"choices": [{"index": 0, "delta": {"content": choices[0].get("message", {}).get("content", "") if choices else ""}}], "usage": body.get("usage", {})}
                data = ("data: " + json.dumps(delta) + "\n\ndata: [DONE]\n\n").encode()
                content_type = "text/event-stream"
            else:
                data = json.dumps(body).encode()
                content_type = "application/json"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if account:
                self.send_header("X-Ebook-Ollama-Seat", account)
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self):
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                self.respond(401, {"error": "Unauthorized"})
                return
            if self.command == "GET" and self.path == "/health":
                self.respond(200, {"status": "ok"})
                return
            allowed = self.path == "/v1/models" if self.command == "GET" else self.path == "/v1/chat/completions"
            if not allowed:
                self.respond(404, {"error": "Unsupported endpoint"})
                return
            if not capacity.acquire(blocking=False):
                self.respond(503, {"error": "Adapter is busy; retry later"})
                return
            try:
                payload = None
                if self.command == "POST":
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_BODY:
                        self.respond(413, {"error": "Invalid request size"})
                        return
                    self.connection.settimeout(15)
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError()
                status, body, account = adapter.request(self.path, payload)
                self.respond(status, body, account, bool(payload and payload.get("stream")))
                print(json.dumps({"event": "ollama_pool_request", "status": status, "account": account}), flush=True)
            except PoolUnavailable:
                self.respond(503, {"error": "Ollama pool unavailable"})
            except (ValueError, TimeoutError):
                self.respond(400, {"error": "Invalid request"})
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                capacity.release()

        do_GET = handle_request
        do_POST = handle_request

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fleet-repo", type=Path, required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=11436)
    args = parser.parse_args()
    if args.token_file.stat().st_mode & 0o077:
        raise SystemExit("Adapter token file must be private")
    token = args.token_file.read_text().strip()
    if len(token) < 32:
        raise SystemExit("Adapter token is missing or too short")
    adapter = PoolAdapter(Fleet(args.fleet_repo, args.expected_identity))
    ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(adapter, token)).serve_forever()


if __name__ == "__main__":
    main()
