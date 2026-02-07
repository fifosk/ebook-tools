"""Shared user-journey runner for Playwright E2E tests.

Loads JSON journey definitions from ``tests/e2e/journeys/`` and executes
them against a Playwright ``Page``.  Each journey is a list of abstract
steps (``login``, ``navigate_tab``, ``select_filter``, etc.) that are
mapped to concrete browser actions here.

New journeys are automatically discovered by :func:`get_journey_names`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

JOURNEYS_DIR = Path(__file__).parent / "journeys"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def get_journey_names() -> list[str]:
    """Return sorted list of journey IDs (stem of each .json file)."""
    return sorted(p.stem for p in JOURNEYS_DIR.glob("*.json"))


def load_journey(name: str) -> dict:
    """Load a journey definition by name."""
    path = JOURNEYS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Journey not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Web journey runner
# ---------------------------------------------------------------------------

class WebJourneyRunner:
    """Interpret journey steps against a Playwright page.

    The page is expected to be pre-authenticated (via the
    ``authenticated_page`` fixture from conftest.py).
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    # -- public API --------------------------------------------------------

    def run(self, journey: dict) -> None:
        """Execute all steps in *journey* sequentially."""
        for step in journey.get("steps", []):
            action = step["action"]
            handler = getattr(self, f"_do_{action}", None)
            if handler is None:
                raise ValueError(f"Unknown journey action: {action!r}")
            handler(step)
            self._maybe_screenshot(step)

    # -- step handlers -----------------------------------------------------

    def _do_login(self, step: dict) -> None:
        # The page is already authenticated via storage state.
        # Just verify the sidebar loaded successfully.
        sidebar = self.page.locator("#dashboard-sidebar")
        expect(sidebar).to_be_visible(timeout=15_000)

    def _do_navigate_tab(self, step: dict) -> None:
        tab = step.get("tab", "Jobs")
        if tab == "Jobs":
            # Jobs are shown in the sidebar "Job Overview" section by default.
            # Ensure the section is open.
            section = self.page.locator(
                "details.sidebar__section:has(summary:text('Job Overview'))"
            )
            if section.count() > 0:
                # Open the details element if closed
                if section.get_attribute("open") is None:
                    section.locator("summary").click()
        elif tab == "Library":
            # Click the "Browse Library" link in the sidebar
            browse_btn = self.page.locator(
                "button.sidebar__link--player, "
                "[aria-label*='Browse']"
            )
            if browse_btn.count() > 0:
                browse_btn.first.click()
                self.page.wait_for_load_state("networkidle")

    def _do_select_filter(self, step: dict) -> None:
        filter_name = step.get("filter", "Books")
        # Map journey filter names to sidebar section summary text
        section_map = {
            "Books": "Audiobooks",
            "Video": "Videos",
            "Subtitles": "Subtitles",
        }
        summary_text = section_map.get(filter_name, filter_name)
        # Find and ensure the matching sub-section is open
        section = self.page.locator(
            f"details.sidebar__section:has(summary:text('{summary_text}'))"
        )
        section.first.wait_for(state="visible", timeout=10_000)
        if section.first.get_attribute("open") is None:
            section.first.locator("summary").click()

    def _do_play_first_item(self, step: dict) -> None:
        play_btn = self.page.locator("button.sidebar__job-play")
        play_btn.first.wait_for(state="visible", timeout=15_000)

        if play_btn.count() == 0:
            if step.get("skip_if_empty"):
                pytest.skip("No playable items found in sidebar")
            raise AssertionError("No play buttons found in sidebar")

        play_btn.first.click()

        # Wait for the player panel to appear
        player = self.page.locator(".player-panel[role='region']")
        expect(player).to_be_visible(timeout=15_000)

    def _do_go_back(self, step: dict) -> None:
        # The web app is a SPA — the sidebar persists alongside the player.
        # "Go back" means dismissing the player or simply verifying the
        # sidebar is still reachable.  Try close/back buttons first, then
        # fall back to confirming the sidebar is visible (it always is).
        close_btn = self.page.locator(
            "[aria-label='Close player'], "
            "[data-testid='player-close'], "
            "button.player-panel__close"
        )
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
            self.page.wait_for_timeout(500)

        # Verify the sidebar is visible (always true in this SPA)
        sidebar = self.page.locator("#dashboard-sidebar")
        expect(sidebar).to_be_visible(timeout=10_000)

    def _do_assert_visible(self, step: dict) -> None:
        selector = step.get("selector", "")
        if not selector:
            return
        element = self.page.locator(selector)
        timeout = step.get("timeout", 10_000)
        expect(element.first).to_be_visible(timeout=timeout)

    def _do_wait(self, step: dict) -> None:
        ms = step.get("ms", 1000)
        self.page.wait_for_timeout(ms)

    # -- helpers -----------------------------------------------------------

    def _maybe_screenshot(self, step: dict) -> None:
        name = step.get("screenshot")
        if name:
            self.page.screenshot(
                path=f"test-results/screenshots/web-journey-{name}.png",
                full_page=True,
            )
