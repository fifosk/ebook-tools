from __future__ import annotations

from modules.webapi.runtime_descriptor import (
    assert_runtime_descriptor_is_public,
    build_runtime_descriptor,
)


def test_runtime_descriptor_advertises_apple_pipeline_contract() -> None:
    descriptor = build_runtime_descriptor("test-version")

    assert descriptor["status"] == "ok"
    assert descriptor["app"] == "ebook-tools"
    assert descriptor["service"] == "ebook-tools-api"
    assert descriptor["healthPath"] == "/_health"
    assert descriptor["auth"] == {
        "loginPath": "/api/auth/login",
        "sessionPath": "/api/auth/session",
        "tokenTransport": "Authorization: Bearer",
    }
    assert descriptor["clientConfig"]["sessionTokenStorage"] == "device-keychain"
    assert descriptor["clientConfig"]["legacyTokenMigration"] == "userdefaults-authToken"
    assert descriptor["applePipeline"]["manifestId"] == "ebook-tools"
    assert descriptor["creation"] == {
        "bookOptionsPath": "/api/books/options",
        "bookJobsPath": "/api/books/jobs",
    }
    assert_runtime_descriptor_is_public(descriptor)
