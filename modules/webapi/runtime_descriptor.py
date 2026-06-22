"""Public non-secret runtime descriptor for app pipeline preflights."""

from __future__ import annotations

API_BASE_URL_ENVIRONMENT = (
    "INTERACTIVE_READER_API_BASE_URL",
    "EBOOK_TOOLS_API_BASE_URL",
    "E2E_API_BASE_URL",
)
CREDENTIAL_ENVIRONMENT = ("E2E_USERNAME", "E2E_PASSWORD")


def build_runtime_descriptor(version: str) -> dict[str, object]:
    """Return non-secret runtime facts safe for simulator/device preflights."""

    return {
        "status": "ok",
        "app": "ebook-tools",
        "service": "ebook-tools-api",
        "version": version,
        "healthPath": "/_health",
        "auth": {
            "loginPath": "/api/auth/login",
            "sessionPath": "/api/auth/session",
            "tokenTransport": "Authorization: Bearer",
        },
        "clientConfig": {
            "apiBaseUrlEnvironment": list(API_BASE_URL_ENVIRONMENT),
            "credentialEnvironment": list(CREDENTIAL_ENVIRONMENT),
            "sessionTokenStorage": "device-keychain",
            "legacyTokenMigration": "userdefaults-authToken",
        },
    }
