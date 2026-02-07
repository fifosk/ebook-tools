"""E2E: Login flow and interactive player playback verification."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e]


class TestDashboard:
    """Verify that an authenticated session reaches the dashboard."""

    def test_dashboard_loads(self, authenticated_page: Page) -> None:
        page = authenticated_page

        # Sidebar brand visible
        brand = page.locator(".sidebar__title")
        expect(brand).to_have_text("Language Tools")

        # Sidebar element present
        sidebar = page.locator("#dashboard-sidebar")
        expect(sidebar).to_be_visible()

    def test_sidebar_has_sections(self, authenticated_page: Page) -> None:
        page = authenticated_page

        # At least one sidebar section should appear (jobs load async)
        sections = page.locator(".sidebar__section")
        expect(sections.first).to_be_visible(timeout=10_000)


class TestPlayback:
    """Click play from the sidebar and verify the interactive player opens."""

    def test_sidebar_play_opens_player(self, authenticated_page: Page) -> None:
        page = authenticated_page

        # Wait for sidebar job play buttons to appear
        play_btn = page.locator("button.sidebar__job-play")
        play_btn.first.wait_for(state="visible", timeout=15_000)

        if play_btn.count() == 0:
            pytest.skip("No jobs with play buttons in sidebar")

        # Click the first play button
        play_btn.first.click()

        # Player panel should appear
        player = page.locator(".player-panel[role='region']")
        expect(player).to_be_visible(timeout=15_000)

    def test_player_renders_text(self, authenticated_page: Page) -> None:
        page = authenticated_page

        # Click play to open the player
        play_btn = page.locator("button.sidebar__job-play")
        play_btn.first.wait_for(state="visible", timeout=15_000)

        if play_btn.count() == 0:
            pytest.skip("No jobs with play buttons in sidebar")

        play_btn.first.click()

        # Wait for the interactive text document area
        doc = page.locator("[data-testid='player-panel-document']")
        expect(doc).to_be_visible(timeout=20_000)

        # Text frames with rendered sentences should appear
        frame = page.locator("[data-text-player-frame='true']")
        expect(frame.first).to_be_visible(timeout=20_000)
