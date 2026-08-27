from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("ollama_pool_proxy", Path(__file__).parents[2] / "scripts/ollama_pool_proxy.py")
proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy)


class Fleet:
    def __init__(self):
        self.calls = []
        self.keys = []
        self.denied = False
        self.wrong_ref = False
        self.missing_key = False

    def call(self, verb, **kwargs):
        self.calls.append((verb, kwargs))
        if verb == "ollama_acquire":
            if self.denied:
                return {"granted": False}
            account = kwargs.get("account", "ollama-cloud")
            return {"granted": True, "lease_id": str(len(self.calls)), "account": account,
                    "seat_ref": "wrong" if self.wrong_ref else proxy.LANES[account]}
        return {"released": True, "binding_verified": True}

    def key(self, ref):
        self.keys.append(ref)
        if self.missing_key and ref == "fleet/ollama-key":
            raise proxy.PoolUnavailable()
        return ref


@pytest.mark.parametrize("failure", [401, 403, 429, 500])
def test_failed_seat_releases_and_uses_other_lease(failure):
    fleet = Fleet()
    sent = []

    def send(path, payload, key):
        sent.append((path, payload, key))
        return (failure, {}) if key == "fleet/ollama-key" else (200, {"choices": []})

    adapter = proxy.PoolAdapter(fleet, send, clock=lambda: 10)
    payload = {"model": "mistral-large-3:675b-cloud", "stream": True}
    assert adapter.request("/v1/chat/completions", payload) == (200, {"choices": []}, "ollama-gmail")
    assert [s[2] for s in sent] == ["fleet/ollama-key", "fleet/ollama-key-gmail"]
    assert sent[0][1] == {"model": "mistral-large-3:675b", "stream": False}
    assert payload["stream"] is True
    releases = [args for verb, args in fleet.calls if verb == "ollama_release"]
    assert [r["served_by"] for r in releases] == ["ollama-cloud", "ollama-gmail"]
    assert releases[0]["outcome"] == ("quota-429" if failure == 429 else f"http-{failure}")
    assert releases[1]["outcome"] == "success"
    sent.clear()
    assert adapter.request("/v1/chat/completions", payload)[0] == 200
    assert [s[2] for s in sent] == ["fleet/ollama-key-gmail"]


def test_pool_refusal_never_dispatches():
    fleet = Fleet()
    fleet.denied = True
    adapter = proxy.PoolAdapter(fleet, lambda *_: pytest.fail("unleased request"))
    assert adapter.request("/v1/models")[0] == 503
    assert fleet.keys == []
    assert len(fleet.calls) == 1


def test_binding_mismatch_never_reads_key_and_releases():
    fleet = Fleet()
    fleet.wrong_ref = True
    adapter = proxy.PoolAdapter(fleet, lambda *_: pytest.fail("wrong seat request"))
    assert adapter.request("/v1/models")[0] == 503
    assert fleet.keys == []
    assert len([v for v, _ in fleet.calls if v == "ollama_release"]) == 2


def test_missing_key_switches_without_borrowing_another_seat_key():
    fleet = Fleet()
    fleet.missing_key = True
    sent = []

    def send(path, payload, key):
        sent.append(key)
        return 200, {"data": []}

    assert proxy.PoolAdapter(fleet, send).request("/v1/models")[2] == "ollama-gmail"
    assert sent == ["fleet/ollama-key-gmail"]
    releases = [args for verb, args in fleet.calls if verb == "ollama_release"]
    assert releases[0]["served_by"] == ""
    assert releases[1]["served_by"] == "ollama-gmail"


def test_bad_request_does_not_rotate_or_expose_provider_body():
    fleet = Fleet()
    adapter = proxy.PoolAdapter(fleet, lambda *_: (400, {"error": "secret request text"}))
    status, body, _ = adapter.request("/v1/chat/completions", {"model": "test"})
    assert status == 400
    assert "secret" not in str(body)
    assert len(fleet.keys) == 1


def test_all_seats_unavailable_is_bounded_and_redacted():
    fleet = Fleet()
    adapter = proxy.PoolAdapter(fleet, lambda *_: (401, {"error": "private response"}))
    status, body, account = adapter.request("/v1/chat/completions", {"model": "test"})
    assert status == 503 and account is None
    assert "private" not in str(body)
    assert len(fleet.keys) == 2
    assert adapter.request("/v1/models")[0] == 503
    assert len(fleet.keys) == 2


def test_adapter_http_requires_auth_and_only_allows_fixed_paths():
    import json
    import threading
    import urllib.error
    import urllib.request

    fleet = Fleet()
    adapter = proxy.PoolAdapter(fleet, lambda *_: (200, {"choices": [{"message": {"content": "hello"}}]}))
    server = proxy.ThreadingHTTPServer(("127.0.0.1", 0), proxy.handler_for(adapter, "test-token"))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base + "/v1/models")
        assert error.value.code == 401
        request = urllib.request.Request(base + "/arbitrary", headers={"Authorization": "Bearer test-token"})
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 404
        assert fleet.calls == []
        request = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps({"model": "test", "stream": True}).encode(), headers={"Authorization": "Bearer test-token"})
        with urllib.request.urlopen(request) as response:
            assert response.headers["X-Ebook-Ollama-Seat"] == "ollama-cloud"
            assert b'"content": "hello"' in response.read()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(2)
