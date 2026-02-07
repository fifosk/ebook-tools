.PHONY: test test-fast test-audio test-translation test-webapi test-services \
       test-pipeline test-cli test-auth test-library test-render test-media \
       test-config test-metadata test-changed test-e2e test-e2e-headless

# ── Full suite ───────────────────────────────────────────────────────────
test:
	pytest

# ── Skip slow / integration tests ───────────────────────────────────────
test-fast:
	pytest -m "not slow and not integration"

# ── Domain markers ───────────────────────────────────────────────────────
test-audio:
	pytest -m audio

test-translation:
	pytest -m translation

test-webapi:
	pytest -m webapi

test-services:
	pytest -m services

test-pipeline:
	pytest -m pipeline

test-cli:
	pytest -m cli

test-auth:
	pytest -m auth

test-library:
	pytest -m library

test-render:
	pytest -m render

test-media:
	pytest -m media

test-config:
	pytest -m config

test-metadata:
	pytest -m metadata

# ── E2E browser tests (Playwright) ────────────────────────────────────
# Artifacts (screenshots, traces) written to test-results/ (gitignored)
E2E_ARGS = -m e2e -o "addopts=-rs" --screenshot=on --full-page-screenshot --tracing=retain-on-failure --e2e-report

test-e2e:
	pytest $(E2E_ARGS) --headed --slowmo=200

test-e2e-headless:
	pytest $(E2E_ARGS)
