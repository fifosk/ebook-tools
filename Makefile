.PHONY: test test-fast test-audio test-translation test-webapi test-services \
       test-pipeline test-cli test-auth test-library test-render test-media \
       test-config test-metadata test-changed test-e2e test-e2e-headless \
       test-e2e-ios

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

# ── iOS E2E tests (XCUITest) ────────────────────────────────────────
XCBUILD = /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild
XCPROJ = ios/InteractiveReader/InteractiveReader.xcodeproj
IOS_DESTINATION = 'platform=iOS Simulator,name=iPhone 15 Pro'
IOS_E2E_RESULT = test-results/ios-e2e.xcresult

test-e2e-ios:
	@rm -rf $(IOS_E2E_RESULT) test-results/ios-e2e-attachments
	@python -c "import json; from pathlib import Path; \
		env={}; \
		[env.update(dict([l.strip().split('=',1)])) for l in Path('.env').read_text().splitlines() if '=' in l and not l.startswith('#')]; \
		Path('/tmp/ios_e2e_config.json').write_text(json.dumps({ \
			'username': env.get('E2E_USERNAME',''), \
			'password': env.get('E2E_PASSWORD',''), \
			'api_base_url': env.get('E2E_API_BASE_URL','https://api.langtools.fifosk.synology.me') \
		}))"
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IOS_DESTINATION) \
		-resultBundlePath $(IOS_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(IOS_E2E_RESULT) \
		--output test-results/ios-e2e-report.md
	@rm -f /tmp/ios_e2e_config.json
