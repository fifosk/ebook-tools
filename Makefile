.PHONY: test test-fast test-audio test-translation test-webapi test-services \
       test-pipeline test-cli test-auth test-library test-render test-media \
       test-config test-metadata test-changed \
       test-e2e test-e2e-headless test-e2e-web test-e2e-web-headless \
       test-e2e-ios test-e2e-iphone test-e2e-ipad test-e2e-tvos \
       test-e2e-all test-e2e-apple-parallel

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
E2E_ARGS = -m e2e -o "addopts=-rs" --screenshot=on --full-page-screenshot --tracing=retain-on-failure

# Legacy targets (backward compat)
test-e2e:
	pytest $(E2E_ARGS) --e2e-report --headed --slowmo=200

test-e2e-headless:
	pytest $(E2E_ARGS) --e2e-report

# Named Web targets with custom report title
test-e2e-web:
	pytest $(E2E_ARGS) --headed --slowmo=200 \
		--e2e-report=test-results/web-e2e-report.md \
		--e2e-report-title="Web E2E Test Report"

test-e2e-web-headless:
	pytest $(E2E_ARGS) \
		--e2e-report=test-results/web-e2e-report.md \
		--e2e-report-title="Web E2E Test Report"

# ── Apple E2E tests (XCUITest) ────────────────────────────────────────
XCBUILD = /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild
XCPROJ = ios/InteractiveReader/InteractiveReader.xcodeproj
JOURNEY_SRC = tests/e2e/journeys/basic_playback.json

# Write config + journey to /tmp (idempotent, parallel-safe)
define WRITE_E2E_CONFIG
python -c "import json; from pathlib import Path; \
	env={}; \
	[env.update(dict([l.strip().split('=',1)])) for l in Path('.env').read_text().splitlines() if '=' in l and not l.startswith('#')]; \
	Path('/tmp/ios_e2e_config.json').write_text(json.dumps({ \
		'username': env.get('E2E_USERNAME',''), \
		'password': env.get('E2E_PASSWORD',''), \
		'api_base_url': env.get('E2E_API_BASE_URL','https://api.langtools.fifosk.synology.me') \
	}))" && cp $(JOURNEY_SRC) /tmp/ios_e2e_journey.json
endef

# ── iPhone E2E ───────────────────────────────────────────────────────
IPHONE_DESTINATION = 'platform=iOS Simulator,name=iPhone 17 Pro'
IPHONE_E2E_RESULT = $(CURDIR)/test-results/iphone-e2e.xcresult

test-e2e-iphone:
	@rm -rf $(IPHONE_E2E_RESULT) test-results/iphone-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPHONE_DESTINATION) \
		-resultBundlePath $(IPHONE_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(IPHONE_E2E_RESULT) \
		--output test-results/iphone-e2e-report.md \
		--title "iPhone E2E Test Report" \
		--screenshot-prefix iphone
	@rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json

# ── iPad E2E ─────────────────────────────────────────────────────────
IPAD_DESTINATION = 'platform=iOS Simulator,name=iPad Air 11-inch (M3)'
IPAD_E2E_RESULT = $(CURDIR)/test-results/ipad-e2e.xcresult

test-e2e-ipad:
	@rm -rf $(IPAD_E2E_RESULT) test-results/ipad-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPAD_DESTINATION) \
		-resultBundlePath $(IPAD_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(IPAD_E2E_RESULT) \
		--output test-results/ipad-e2e-report.md \
		--title "iPad E2E Test Report" \
		--screenshot-prefix ipad
	@rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json

# ── tvOS E2E ─────────────────────────────────────────────────────────
TVOS_DESTINATION = 'platform=tvOS Simulator,name=Apple TV'
TVOS_E2E_RESULT = $(CURDIR)/test-results/tvos-e2e.xcresult

test-e2e-tvos:
	@rm -rf $(TVOS_E2E_RESULT) test-results/tvos-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTVUITests \
		-destination $(TVOS_DESTINATION) \
		-resultBundlePath $(TVOS_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(TVOS_E2E_RESULT) \
		--output test-results/tvos-e2e-report.md \
		--title "tvOS E2E Test Report" \
		--screenshot-prefix tvos
	@rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json

# ── Legacy alias ─────────────────────────────────────────────────────
test-e2e-ios: test-e2e-iphone

# ── Run all platforms sequentially ────────────────────────────────────
# Parallel execution (-j4) corrupts xcresult bundles (Xcode mkstemp bug),
# so we run sequentially.  Use -k to continue on failures.
test-e2e-all:
	@$(WRITE_E2E_CONFIG)
	@$(MAKE) -k \
		test-e2e-web-headless \
		test-e2e-iphone \
		test-e2e-ipad \
		test-e2e-tvos \
		; EXIT=$$?; \
	rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json; \
	exit $$EXIT
