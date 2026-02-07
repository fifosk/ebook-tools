"""E2E test fixtures: authentication, base URL, and browser context."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # picks up .env at repo root (gitignored)

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

# Type alias from pytest-playwright for the new_context factory fixture
try:
    from pytest_playwright.pytest_playwright import CreateContextCallback
except ImportError:
    from typing import Callable
    CreateContextCallback = Callable[..., BrowserContext]


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("e2e", "Browser E2E test options")
    group.addoption(
        "--e2e-base-url",
        action="store",
        default=None,
        help=(
            "Base URL for the web app under test. "
            "Defaults to E2E_BASE_URL env var or https://langtools.fifosk.synology.me"
        ),
    )


# ---------------------------------------------------------------------------
# Base URL
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config) -> str:
    """Resolve the app base URL from CLI, env, or default."""
    url = (
        pytestconfig.getoption("--e2e-base-url", default=None)
        or os.environ.get("E2E_BASE_URL")
        or "https://langtools.fifosk.synology.me"
    )
    return url.rstrip("/")


@pytest.fixture(scope="session")
def api_base_url(base_url: str) -> str:
    """Resolve the API base URL from the frontend URL."""
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return base_url.replace(":5173", ":8000")
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(base_url)
    api_host = f"api.{parsed.hostname}"
    return urlunparse(parsed._replace(netloc=api_host))


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def e2e_credentials() -> dict[str, str]:
    """Read E2E_USERNAME and E2E_PASSWORD from environment."""
    username = os.environ.get("E2E_USERNAME", "")
    password = os.environ.get("E2E_PASSWORD", "")
    if not username or not password:
        pytest.skip(
            "E2E credentials not configured. "
            "Set E2E_USERNAME and E2E_PASSWORD environment variables."
        )
    return {"username": username, "password": password}


# ---------------------------------------------------------------------------
# Authenticated browser context (session-scoped login, per-test isolation)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def auth_token(api_base_url: str, e2e_credentials: dict[str, str]) -> str:
    """Log in via the API and return a valid session token."""
    import httpx

    resp = httpx.post(
        f"{api_base_url}/api/auth/login",
        json=e2e_credentials,
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("token")
    assert token, "Login response did not contain a token"
    return token


@pytest.fixture(scope="session")
def storage_state_path(
    tmp_path_factory: pytest.TempPathFactory,
    base_url: str,
    auth_token: str,
    browser: Browser,
) -> Path:
    """Inject the auth token into localStorage and save Playwright storage state.

    This navigates to the app once, writes the token, and saves state to a temp
    file. All subsequent test contexts load from this file — no repeated logins.
    """
    state_path = tmp_path_factory.mktemp("e2e") / "storage_state.json"

    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()

    page.goto(base_url, wait_until="domcontentloaded")

    # Match AuthProvider's persistToken format: JSON.stringify({ token })
    page.evaluate(
        """([key, value]) => {
            window.localStorage.setItem(key, JSON.stringify({ token: value }));
        }""",
        ["ebook-tools.auth.token", auth_token],
    )

    ctx.storage_state(path=str(state_path))
    ctx.close()

    return state_path


@pytest.fixture()
def browser_context_args(
    browser_context_args: dict,
    storage_state_path: Path,
) -> dict:
    """Override pytest-playwright's browser_context_args to inject auth state.

    This ensures every context created via the built-in ``new_context`` fixture
    (and therefore the ``context`` / ``page`` fixtures) is pre-authenticated
    and accepts self-signed certs.
    """
    return {
        **browser_context_args,
        "storage_state": str(storage_state_path),
        "ignore_https_errors": True,
    }


@pytest.fixture()
def authenticated_page(
    new_context: CreateContextCallback,
    base_url: str,
) -> Page:
    """Authenticated page already navigated to the app root.

    Uses pytest-playwright's ``new_context`` so the artifact recorder
    captures screenshots, traces, and videos automatically.
    """
    ctx = new_context()
    page = ctx.new_page()
    page.goto(base_url, wait_until="networkidle")
    return page
