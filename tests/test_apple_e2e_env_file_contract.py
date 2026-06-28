from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"
XCUITEST_BASE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReaderUITests"
    / "InteractiveReaderUITests.swift"
)


def test_apple_e2e_makefile_uses_configurable_env_file() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "E2E_TEMP_ROOT ?= /tmp/apple-device-app-pipeline/ebook-tools" in makefile
    assert "E2E_CONFIG_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PROFILE)/ios_e2e_config.json" in makefile
    assert "E2E_JOURNEY_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PROFILE)/ios_e2e_journey.json" in makefile
    assert "E2E_ENV_FILE ?= $(if $(wildcard .env),.env,$(if $(wildcard .env.local),.env.local,.env))" in makefile
    assert "E2E_PLATFORM_PROFILE ?= $(E2E_PROFILE)" in makefile
    assert "E2E_MUSIC_BED_SYNC_TEST ?=" in makefile
    assert "E2E_START_BROWSE_SECTION ?=" in makefile
    assert "E2E_ALLOW_RESTORED_SESSION ?=" in makefile
    assert "E2E_FAIL_ON_SKIPPED ?=" in makefile
    assert '$(PYTHON) scripts/write_apple_e2e_config.py \\' in makefile
    assert '--env-file "$(E2E_ENV_FILE)"' in makefile
    assert '--profile "$(E2E_PROFILE)"' in makefile
    assert '--fallback-config-path "$(E2E_PLATFORM_CONFIG_PATH)"' in makefile
    assert '--fallback-journey-path "$(E2E_PLATFORM_JOURNEY_PATH)"' in makefile
    assert "define CHECK_E2E_CONFIG" in makefile
    assert '$(PYTHON) scripts/check_apple_e2e_config.py \\' in makefile
    assert "$(PYTHON) scripts/check_apple_e2e_journeys.py" in makefile
    assert "tests/scripts/test_check_apple_e2e_journeys.py" in makefile
    assert "tests/scripts/test_ios_e2e_report.py" in makefile
    assert '--profile "$(E2E_PROFILE)"' in makefile
    assert '--allow-restored-session "$(E2E_ALLOW_RESTORED_SESSION)"' in makefile
    assert "define CHECK_XCODE_READINESS" in makefile
    assert '$(PYTHON) scripts/check_apple_xcode_readiness.py \\' in makefile
    assert '--xcodebuild "$(XCBUILD)"' in makefile
    assert makefile.count("@$(CHECK_E2E_CONFIG)") == 3
    assert makefile.count("@$(CHECK_XCODE_READINESS)") == 3
    assert "test-e2e-ipad: E2E_PLATFORM_PROFILE = ipados" in makefile
    assert "test-e2e-tvos: E2E_PLATFORM_PROFILE = tvos" in makefile
    assert '$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"' in makefile
    assert "test-e2e-iphone-create-readiness:" in makefile
    assert "E2E_PROFILE=iphone-create" in makefile
    assert "test-e2e-ipad-create-readiness:" in makefile
    assert "E2E_PROFILE=ipados-create" in makefile
    assert "test-e2e-tvos-create-readiness:" in makefile
    assert "E2E_PROFILE=tvos-create" in makefile
    for target in (
        "test-e2e-iphone-create-readiness",
        "test-e2e-ipad-create-readiness",
        "test-e2e-tvos-create-readiness",
    ):
        target_body = makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]
        assert "E2E_FAIL_ON_SKIPPED=1" in target_body
    assert "MUSIC_BED_SYNC_JOURNEY_SRC = tests/e2e/journeys/music_bed_sync.json" in makefile
    assert "test-e2e-ipad-music-bed-sync-dry-run:" in makefile
    assert "$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=ipados-music-bed-sync" in makefile
    assert "test-e2e-ipad-music-bed-sync:" in makefile
    assert "E2E_MUSIC_BED_SYNC_TEST=1 E2E_START_BROWSE_SECTION=Library E2E_ALLOW_RESTORED_SESSION=1 E2E_FAIL_ON_SKIPPED=1 $(MAKE) test-e2e-ipad" in makefile
    assert "E2E_PROFILE=ipados-music-bed-sync" in makefile
    assert "test-e2e-tvos-music-bed-sync-dry-run:" in makefile
    assert "$(MAKE) check-apple-e2e-journeys" in makefile
    assert "$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-music-bed-sync" in makefile
    assert "test-e2e-tvos-music-bed-sync:" in makefile
    assert "E2E_MUSIC_BED_SYNC_TEST=1 E2E_START_BROWSE_SECTION=Library E2E_ALLOW_RESTORED_SESSION=1 E2E_FAIL_ON_SKIPPED=1 $(MAKE) test-e2e-tvos" in makefile
    assert "E2E_PROFILE=tvos-music-bed-sync" in makefile
    assert 'E2E_MUSIC_BED_SYNC_TEST="$(E2E_MUSIC_BED_SYNC_TEST)"' in makefile
    assert 'E2E_START_BROWSE_SECTION="$(E2E_START_BROWSE_SECTION)"' in makefile
    assert 'E2E_ALLOW_RESTORED_SESSION="$(E2E_ALLOW_RESTORED_SESSION)"' in makefile
    assert '$(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \\' in makefile
    assert "$(if $(strip $(E2E_FAIL_ON_SKIPPED)),--fail-on-skipped)" in makefile
    assert "report_status=0" in makefile
    assert "if [ $$status -eq 0 ] && [ $$report_status -ne 0 ]; then status=$$report_status; fi" in makefile
    assert "--env-file .env \\" not in makefile
    assert "scripts/check_apple_create_readiness.py\n" not in makefile
    assert "scripts/check_apple_e2e_config.py\n" not in makefile


def test_testing_docs_describe_e2e_env_file_override() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")

    assert "E2E_ENV_FILE" in docs
    assert ".env.local" in docs
    assert "make test-e2e-ipad-create-readiness" in docs
    assert "make test-e2e-tvos-create-readiness" in docs
    assert "All dedicated Create-readiness Make targets pass `E2E_FAIL_ON_SKIPPED=1`" in docs
    assert "skipped `JourneyTests/testJourney`\ncase fails the gate" in docs
    assert "counter `autoResumeAlreadyPlaying` reaches at least 1" in docs
    assert "`E2E_ALLOW_RESTORED_SESSION=1` and `E2E_FAIL_ON_SKIPPED=1`" in docs
    assert "skipped XCUITest\ncases fail the Make target" in docs
    assert "/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_config.json" in docs
    assert "/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_journey.json" in docs
    assert "/tmp/ios_e2e_config.json" not in docs
    assert "/tmp/ios_e2e_journey.json" not in docs


def test_xcuitest_base_documents_profile_scoped_config_fallback() -> None:
    source = XCUITEST_BASE.read_text(encoding="utf-8")

    assert "/tmp/apple-device-app-pipeline/ebook-tools/<profile>/ios_e2e_config.json" in source
    assert "/tmp/ios_e2e_config.json" not in source
    assert 'app.launchEnvironment["E2E_MUSIC_BED_SYNC_TEST"] = "1"' in source
    assert 'app.launchEnvironment["E2E_START_BROWSE_SECTION"] = startSection' in source
    assert 'var allowsRestoredSession: Bool' in source
    assert "let profile: String?" in source
    assert "var e2eProfileLabel: String" in source
    assert "config?.profile?.trimmingCharacters" in source
    assert "let auth_token: String?" in source
    assert "var hasConfiguredE2EAuthToken: Bool" in source
    assert 'app.launchEnvironment["E2E_AUTH_TOKEN"] = authToken' in source
    assert "let allow_restored_session: Bool?" in source
    assert "config?.allow_restored_session == true" in source
    assert 'app.launchEnvironment["E2E_ALLOW_RESTORED_SESSION"] = "1"' in source
    assert 'app.launchEnvironment["E2E_DISABLE_SESSION_RESTORE"] = "1"' in source
    assert "private struct E2EJourneyIdentity: Decodable" in source
    assert "private func loadJourneyID() -> String?" in source
    assert 'journeyID == "music_bed_sync"' in source
    assert 'app.launchEnvironment["E2E_START_BROWSE_SECTION"] = "Library"' in source


def test_apple_journey_runner_prefers_stable_row_identifiers_on_all_surfaces() -> None:
    runner = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReaderUITests"
        / "JourneyRunner.swift"
    ).read_text(encoding="utf-8")

    play_first_body = runner.split("private func doPlayFirstItem(_ step: JourneyStep) throws", 1)[1].split(
        "private func waitForPlayer()", 1
    )[0]
    assert "step.unless_visible" in play_first_body
    assert "waitForPlayer()" in play_first_body
    assert 'element(withIdentifier: "libraryRowButton")' in play_first_body
    assert 'element(withIdentifier: "jobRowButton")' in play_first_body
    assert play_first_body.count('element(withIdentifier: "libraryRowButton")') == 2
    assert play_first_body.index("case .tvOS:") < play_first_body.index("default:")
    assert play_first_body.index("default:") < play_first_body.rindex('element(withIdentifier: "libraryRowButton")')
