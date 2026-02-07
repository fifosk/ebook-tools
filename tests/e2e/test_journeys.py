"""E2E: Shared user-journey tests.

Automatically discovers all JSON journey definitions in ``tests/e2e/journeys/``
and runs each one as a parametrized test case.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .journey_runner import WebJourneyRunner, get_journey_names, load_journey

pytestmark = [pytest.mark.e2e]


@pytest.mark.parametrize("journey_name", get_journey_names(), ids=lambda n: n)
def test_journey(authenticated_page: Page, journey_name: str) -> None:
    journey = load_journey(journey_name)
    runner = WebJourneyRunner(authenticated_page)
    runner.run(journey)
