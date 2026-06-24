# Testing Guide

## Overview

The ebook-tools project has a comprehensive test suite with **801+ tests** that
are fully green (10 skipped). Tests are organized by domain using pytest markers,
enabling fast targeted runs during development. End-to-end tests run on-demand
across **4 platforms**: Web (Playwright), iPhone, iPad, and tvOS (XCUITest).

![Test Architecture](images/test-architecture.png)

**Key characteristics:**

- **pytest-based** with 16 custom markers for domain isolation
- **E2E tests excluded by default** (`addopts = "-rs -m 'not e2e'"`)
- **Session-scoped fixtures** prevent real RAMDisk mounts during tests
- **Shared JSON journey architecture** for cross-platform E2E consistency
- **Markdown reports with screenshots** for E2E results

## Running Tests

### Apple Pipeline Smoke

For native Apple build/install/launch smoke tests, use the shared home Apple
pipeline instead of adding another local ebook-tools wrapper:

```bash
cd /Users/fifo/Projects/home/apple-device-app-pipeline
python3 scripts/check_app_source_sync.py --app ebook-tools
python3 scripts/check_app_backend.py --app ebook-tools
python3 scripts/ensure_simulator_fleet.py --app ebook-tools --dry-run
python3 scripts/ensure_simulator_fleet.py --app ebook-tools --download-missing
python3 scripts/run_app_simulator_smoke.py --app ebook-tools --profile ipados
python3 scripts/run_app_simulator_smoke.py --app ebook-tools --profile ios
python3 scripts/run_app_simulator_smoke.py --app ebook-tools --profile tvos

# Attended physical deploy dry runs
python3 scripts/run_app_device_deploy.py --app ebook-tools --profile ipad --signed-build-only
python3 scripts/run_app_device_deploy.py --app ebook-tools --profile ipad --dry-run
python3 scripts/run_app_device_deploy.py --app ebook-tools --profile iphone --dry-run
python3 scripts/run_app_device_deploy.py --app ebook-tools --profile appletv --dry-run
python3 scripts/run_app_device_deploy.py --app ebook-tools --profile cinema --dry-run

# Repo-owned wrappers for the same attended-device gates
make apple-device-preflight APPLE_DEVICE_PROFILE=ipad APPLE_DEVICE_ID=<id>
make apple-device-signed-build-only APPLE_DEVICE_PROFILE=ipad
make apple-device-deploy-dry-run APPLE_DEVICE_PROFILE=appletv
make apple-device-full-entitlement-plan APPLE_DEVICE_ID=<id> \
  FULL_CAPABILITY_IOS_PROFILE=<app.mobileprovision> \
  WILDCARD_IOS_EXTENSION_PROFILE=<extension.mobileprovision> \
  APPLE_DEVELOPMENT_IDENTITY="<identity>"
```

The shared pipeline validates the MacBook simulator lane from the local
`/Users/fifo/Projects/home/ebook-tools` clone against the Mac Studio/NAS-hosted
backend topology. It can also repair simulator runtime drift via Xcode platform
downloads when requested. Physical device installs additionally require the
target device to be awake/trusted and Xcode provisioning to cover iCloud, Sign in
with Apple, and Push Notifications. The Makefile targets below remain the
ebook-tools-owned authenticated XCUITest journeys and report generation.
Use `--signed-build-only` to check that physical-device provisioning gate before
attempting an install.

Authenticated Apple journeys should also be launched through the shared
manifest wrapper when dogfooding the home pipeline:

```bash
cd /Users/fifo/Projects/home/apple-device-app-pipeline
python3 scripts/run_app_owned_journey.py --app ebook-tools --list
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile ipados --dry-run
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile ipados-create --dry-run
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile tvos-create --dry-run
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile ios-uitests-build --dry-run
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile macos-ipad-style-dry-run --dry-run
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile macos-ipad-style --dry-run
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile tvos --use-remote-env
```

The ebook-tools app manifest allowlists only `E2E_USERNAME`, `E2E_PASSWORD`,
and `E2E_API_BASE_URL` from the Mac Studio runtime `.env`. The wrapper redacts
sensitive values in its output and writes profile-scoped XCUITest config under
`/tmp/apple-device-app-pipeline/ebook-tools/{profile}/`. Real iPhone, iPad, and
Apple TV installs remain attended; simulator journeys may use injected test
credentials.

When a physical device feels slow after login or session restore, measure the
authenticated backend path without printing credentials or tokens:

```bash
scripts/check_auth_latency.py --runs 5
```

The script reads `E2E_USERNAME`, `E2E_PASSWORD`, and optional
`E2E_API_BASE_URL` from the environment or `.env`, then reports only HTTP
status and elapsed time for `/api/auth/login` and `/api/auth/session`. On
June 21, 2026, the Mac Studio runtime check against the NAS-routed public API
showed login after warmup at roughly 23-31 ms and session restore at roughly
18-24 ms, so the observed attended-device login sluggishness should be
investigated in app launch/debugger/UI sequencing before backend routing.

The Apple Make targets also use the same `tempfile.gettempdir()`-scoped
simulator mutation lock as the shared pipeline while `xcodebuild test` is
running. This keeps app-owned XCUITest journeys from racing with shared
simulator smokes that boot, install, launch, or shut down devices during
parallel dogfood runs.

Current iPad M5 deployment gate:

The authenticated iPadOS simulator journey is green through the shared pipeline:

```bash
python3 scripts/run_app_owned_journey.py --app ebook-tools --profile ipados --use-remote-env
```

Run the Apple Create readiness preflight before authenticated Create journeys
against a shared backend:

```bash
python3 scripts/check_apple_create_readiness.py --env-file .env.local
```

The Make targets choose `E2E_ENV_FILE` automatically: `.env` when present,
otherwise `.env.local`, with an explicit override available for one-off runs.

The reusable manifest also exposes stricter native Create journeys as
`iphone-create` and `ipados-create`. They run the same preflight before Xcode
and then execute the `create_readiness.json` journey, which verifies generated
book controls and source-book continuation fields plus Narrate EPUB, subtitle,
and YouTube dubbing defaults from backend-visible sources.

The preflight verifies backend-visible EPUBs, subtitle sources, newest playable
YouTube/NAS video subtitle pairs, generated-book sentence/language/voice
defaults, the broad book language inventory, and the shared subtitle/YouTube
dubbing processing defaults from `/api/books/options`. It fails if the Create
contract regresses to a small language list, including the iPad-visible
six-language regression, or if the backend stops advertising the generated-book
or media-job defaults used by Web and Apple creation forms. The native Create
readiness journey also selects `Hindi` in the target-language picker so the full
Web-backed language catalog is exercised in the simulator UI, not only the
backend contract.

Latest result on June 21, 2026: `InteractiveReaderUITests/JourneyTests/testJourney`
passed on the `iPad Pro 13-inch (M5)` simulator with 1 test, 0 failures. The
journey asserts the visible `appVersionBadge` frame so the pipeline rejects the
narrow/vertical version-pill regression that was seen on the physical iPad.

Device preflight currently sees `Fifo Ipad Pro` through CoreDevice:

```bash
python3 scripts/run_app_device_deploy.py --app ebook-tools --profile ipad --device-preflight-only
```

For the repo-owned local macOS Designed for iPad/iPhone destination, use the
non-deploying helper checks before a compile:

```bash
make apple-macos-ipad-destination
make build-apple-macos-ipad-style-dry-run
make build-apple-macos-ipad-style
```

The shared pipeline exposes the same lane as the `macos-ipad-style-dry-run`
and `macos-ipad-style` app-owned profiles, mapping to the dry-run and compile
targets above. These commands resolve the local Mac destination and app product
path without touching physical iPhone/iPad/Apple TV devices.

To compile every repo-owned Apple surface that does not touch physical
hardware, use the aggregate local build gate:

```bash
make build-apple-local-surfaces
```

This chains the iPhone simulator, iPad simulator, tvOS simulator, and local Mac
Designed for iPad/iPhone compile checks. It is the preferred local gate before
requesting an attended physical-device deploy.

When the active hardware lane is office-iPad-only and the iPhone is
unavailable, use the narrower iPad/local-Mac build gate:

```bash
make build-apple-office-ipad-surfaces
```

This chains the iPad simulator build with the local Mac Designed for
iPad/iPhone compile check and avoids the iPhone simulator and all physical
device update helpers.

To run the Apple contract gate and then compile every non-physical Apple
surface, use the aggregate local verification gate:

```bash
make verify-apple-local-surfaces
```

This is the preferred repo-owned Apple preflight before requesting an attended
iPhone, iPad, Apple TV, or local Mac Designed for iPad/iPhone update.

For office-iPad-only iteration, use the matching verification gate:

```bash
make verify-apple-office-ipad-surfaces
```

This runs the Apple contracts, the iPad simulator build, the iOS UITest
build-for-testing lane on the iPad destination, and the local Mac Designed for
iPad/iPhone compile check without requiring an iPhone.

The reusable Apple device app pipeline can also be driven from this checkout
through repo-owned wrapper targets:

```bash
make apple-pipeline-contracts
make test-apple-language-catalogs
make test-apple-create-readiness-contract
make test-apple-local-surface-contract
make apple-pipeline-backend
make apple-pipeline-backend-tests
make apple-pipeline-source-sync
make apple-pipeline-web-checks
make apple-pipeline-simulator-smoke-dry-run
make apple-pipeline-simulator-smokes-dry-run
make apple-pipeline-owned-journeys
make apple-pipeline-owned-journey-dry-run
make apple-pipeline-owned-journeys-dry-run
make apple-pipeline-ipad-create-readiness
make apple-pipeline-ipad-create-readiness-dry-run
make apple-pipeline-tvos-create-readiness
make apple-pipeline-tvos-create-readiness-dry-run
make apple-pipeline-orchestration-dry-runs
make verify-apple-shared-pipeline
make verify-apple-golden-pipeline
```

`verify-apple-shared-pipeline` runs the shared pipeline contract, backend
health/runtime, backend pytest, Web checks, and simulator/journey orchestration
dry-runs without physical deployment. Run
`apple-pipeline-source-sync` after the Mac Studio/runtime checkout has been
fast-forwarded, because that check compares the local and remote Git state.
When that source-sync check is expected to pass, `verify-apple-golden-pipeline`
adds it in front of `verify-apple-shared-pipeline` while still avoiding
physical-device deployment.
`apple-pipeline-backend-tests` runs the manifest registered repo-owned
`make test-backend-*` pytest targets and cleans generated caches.
`apple-pipeline-web-checks` runs the
manifest registered Web focused checks and production/export build through the
shared pipeline runner. The focused Create, saved-template, Library, Video
Dubbing, Subtitle Tool, app-view deeplink, full Vitest, and production/export
build checks are repo-owned Web targets, so the shared manifest only names
stable app commands before restoring generated Web artifacts. Use
`APPLE_PIPELINE_SMOKE_PROFILE=ios|ipados|tvos` with
`apple-pipeline-simulator-smoke-dry-run` before launching a shared simulator
smoke. Use `apple-pipeline-ipad-create-readiness-dry-run`, then
`apple-pipeline-ipad-create-readiness`, for the office-iPad-only Create
readiness lane; it delegates to the registered `ipados-create` app-owned
journey. Use `apple-pipeline-tvos-create-readiness-dry-run`, then
`apple-pipeline-tvos-create-readiness`, when Apple TV Create needs the same
strict backend-source readiness check through the registered `tvos-create`
journey. Use `APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create` or
`tvos-create` with `apple-pipeline-owned-journey-dry-run` when you need an
explicit profile override. `apple-pipeline-orchestration-dry-runs` expands the
registered iPhone/iPad/tvOS simulator smoke profiles and app-owned journeys
without booting simulators or loading remote secrets.

For a quick Apple TV compile check without launching the full tvOS journey, run
the repo-owned simulator build lane:

```bash
make build-apple-tvos-simulator
```

This compiles the `InteractiveReaderTV` scheme for the default Apple TV 4K
simulator destination and writes DerivedData under `test-results/`, without
installing to Apple TV hardware.

For iPhone/iPad compile checks without launching the full XCUITest journeys,
run the matching repo-owned simulator build lanes:

```bash
make build-apple-iphone-simulator
make build-apple-ipad-simulator
make build-apple-ios-simulators
make build-apple-ios-uitests
```

These compile the shared `InteractiveReader` scheme for the default iPhone and
iPad simulator destinations, and `build-apple-ios-uitests` compiles the
`InteractiveReaderUITests` scheme with `build-for-testing` so journey-runner
changes can be checked without launching the full XCUITest journey. All write
DerivedData under `test-results/` without installing to iPhone or iPad hardware.

For repo-owned physical iPhone/iPad update readiness, the guarded helper can
exercise CoreDevice paths without installing:

```bash
make apple-devices
APPLE_DEVICE_ID="Fifo Ipad Pro" bash scripts/apple_unattended_device_update.sh --device-preflight-only
APPLE_DEVICE_ID="Fifo Ipad Pro" bash scripts/apple_unattended_device_update.sh --verify-installed
APPLE_DEVICE_ID="Fifo Ipad Pro" bash scripts/apple_unattended_device_update.sh --build-only --allow-provisioning-updates
```

`--device-preflight-only` checks that CoreDevice can see and query the selected
device without requiring the app to already be installed. `--verify-installed`
is the separate installed-app metadata check, and confirmed installs run the
device preflight before build/install unless `--no-preflight` is passed.

The reusable Apple device pipeline also calls the repo-owned
`src/check_poc_readiness.py` hook before signed build/install when readiness is
not skipped. Despite the legacy filename, the ebook-tools hook is intentionally
token-safe: it checks `/_health` and `/api/system/runtime`, then verifies that
the public runtime descriptor advertises the Apple Create, Library action,
offline export, and playback-state paths used by iPhone, iPad, macOS
iPad-style, and tvOS surfaces. It accepts the shared helper's
legacy flags (`--use-remote-env-tokens`, read/write token requirements, and
`--skip-apple-build`) so iPad/TV update runs can reuse the same unattended
command shape while the unavailable iPhone profile is left out of the run.

Run the local Apple contract gate after changing native Create payloads,
deployment helpers, or simulator journey config wiring:

```bash
make test-apple-contracts
```

This checks backend/Web/Apple language catalogue parity, iPad Create split-view
layout wiring, the public runtime descriptor contract, preflight/config parsing,
the Swift creation payload contract, the macOS iPad-style build helper, the
iPhone/iPad simulator compile lanes, the tvOS simulator compile lane, the
office-iPad local build/verification gates, the local Apple surface build gate,
the local Apple verification gate, the
repo-owned Apple deploy readiness hook, the guarded
physical-device update helper, the shared Apple pipeline preflight targets, and
the XCUITest config writer without installing to iPhone, iPad, or Apple TV
hardware.

For focused language picker/catalog work, use:

```bash
make test-apple-language-catalogs
```

This runs the backend/Web/Apple catalog parity tests, the catalog generator
tests, and the generator staleness check without invoking the full Apple
contract suite.

For focused Apple Create readiness preflight work, use:

```bash
make test-apple-create-readiness-contract
```

This runs the native Create readiness checker tests plus the simulator-journey
and env-file contracts that prove the preflight is wired before iPhone, iPad,
and tvOS Create journeys.

For focused non-physical Apple build surface wiring, use:

```bash
make test-apple-local-surface-contract
```

This checks the iPhone/iPad simulator build lanes, tvOS simulator build lane,
Mac Designed for iPad helper, and aggregate local/office-iPad surface gates
without compiling or installing apps.

The public runtime descriptor at `/api/system/runtime` also advertises the
Create, saved-template, Library action, offline export, and playback-state
endpoints used by Apple surfaces. The reusable pipeline backend check validates
those fields before simulator or device runs, and the Apple Settings screen
exposes matching readiness rows, so an older deployment fails early without
needing credentials.

Use dry-runs to inspect the exact unattended command sequence before a physical
update:

```bash
APPLE_DEVICE_ID="Fifo Ipad Pro" bash scripts/apple_unattended_device_update.sh --install --dry-run
APPLE_DEVICE_ID="Fifo Ipad Pro" CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh --install --launch --dry-run
```

Actual physical installs remain explicit and attended by policy:

```bash
APPLE_DEVICE_ID="Fifo Ipad Pro" CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh --install
```

After install, the helper runs `devicectl device info apps --bundle-id` with a
JSON output file under `test-results/` and fails if installed app metadata for
`com.example.InteractiveReader` is not found. Add `--launch` only when the
device is awake and unlocked; locked devices can still install and verify
metadata, but foreground launch may block until the user unlocks the device.
When a signed app has already been produced by Xcode or a prior build, use
`--skip-build --app-path /path/to/InteractiveReader.app` with the same
confirmation guard to install that bundle without driving Xcode again.

Latest attended iPad M5 deployment from June 22, 2026: `v2026.06.22.12`
with marketing version `2026.6.22` and bundle version `2026062212`. The
post-install `devicectl` verification reported:

```text
InteractiveReader   com.example.InteractiveReader   2026.6.22   2026062212
```

The `.12` install used the shared pipeline's iPad simulator gate plus Xcode's
GUI `InteractiveReader` scheme and `Fifo Ipad Pro` run destination. The shared
CLI deploy wrapper reached the signed device build but failed because
command-line Xcode account/profile state rejected the app capabilities; the GUI
path used the active Xcode session and installed the bundle. If the iPad is
unlocked, relaunch outside the debugger with:

```bash
xcrun devicectl device process launch \
  --device BC4A8986-54B2-543C-83CB-4B28F4F73BB2 \
  --terminate-existing \
  com.example.InteractiveReader
```

The June 22 `.12` install completed while the iPad was locked; CoreDevice
verified the installed bundle metadata, but Xcode could not launch into a debug
session until the device was unlocked. After metadata verification, cancel the
blocked Xcode launch sheet so the app is not left attached to a stalled
debugger. Keep the iPad awake and unlocked for launch verification; for future
attended installs, prefer USB-C, tap Trust when prompted, then re-enable network
deployment from Xcode Devices and Simulators if needed.

June 24, 2026 iPad/iPhone full-entitlement deploy recipe: when Xcode CLI
automatic signing reported `No Accounts: Add a new account in Accounts
settings` plus missing Push Notifications, Sign in with Apple, and iCloud
capabilities, the successful unattended fallback was to keep entitlements and
sign the built bundle locally. First confirm the cached profiles are capable:

```bash
python3 scripts/ios_profile_capability_check.py \
  --bundle-id com.example.InteractiveReader \
  --entitlements ios/InteractiveReader/InteractiveReader/Supporting/InteractiveReader.entitlements \
  --embedded-bundle-id com.example.InteractiveReader.NotificationServiceExtension
```

Then ask the repo-owned planner to print the unsigned build, profile embedding,
codesign, verify, and guarded skip-build install commands:

```bash
make apple-device-full-entitlement-plan \
  APPLE_DEVICE_ID="<device-id-or-name>" \
  FULL_CAPABILITY_IOS_PROFILE="$FULL_CAPABILITY_IOS_PROFILE" \
  WILDCARD_IOS_EXTENSION_PROFILE="$WILDCARD_IOS_EXTENSION_PROFILE" \
  APPLE_DEVELOPMENT_IDENTITY="$APPLE_DEVELOPMENT_IDENTITY"
```

The planner is dry by default. To run the same full-entitlement build, profile
embedding, merged-entitlements generation, signing, and verification flow
without touching a device, use:

```bash
make apple-device-full-entitlement-build \
  APPLE_DEVICE_ID="<device-id-or-name>" \
  FULL_CAPABILITY_IOS_PROFILE="$FULL_CAPABILITY_IOS_PROFILE" \
  WILDCARD_IOS_EXTENSION_PROFILE="$WILDCARD_IOS_EXTENSION_PROFILE" \
  APPLE_DEVELOPMENT_IDENTITY="$APPLE_DEVELOPMENT_IDENTITY"
```

Only after an explicit physical-device deploy request, add the guarded install
handoff:

```bash
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  make apple-device-full-entitlement-install \
  APPLE_DEVICE_ID="<device-id-or-name>" \
  FULL_CAPABILITY_IOS_PROFILE="$FULL_CAPABILITY_IOS_PROFILE" \
  WILDCARD_IOS_EXTENSION_PROFILE="$WILDCARD_IOS_EXTENSION_PROFILE" \
  APPLE_DEVELOPMENT_IDENTITY="$APPLE_DEVELOPMENT_IDENTITY"
```

The generated plan follows this sequence:

```bash
DERIVED="test-results/DerivedData-device-manual-codesign"
APP="$DERIVED/Build/Products/Debug-iphoneos/InteractiveReader.app"
APPEX="$APP/PlugIns/NotificationServiceExtension.appex"

/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild \
  -project ios/InteractiveReader/InteractiveReader.xcodeproj \
  -scheme InteractiveReader \
  -configuration Debug \
  -destination 'generic/platform=iOS' \
  -derivedDataPath "$DERIVED" \
  CODE_SIGNING_ALLOWED=NO \
  build

cp "$FULL_CAPABILITY_IOS_PROFILE" "$APP/embedded.mobileprovision"
cp "$WILDCARD_IOS_EXTENSION_PROFILE" "$APPEX/embedded.mobileprovision"

python3 scripts/apple_merge_entitlements.py \
  --profile "$FULL_CAPABILITY_IOS_PROFILE" \
  --bundle-id com.example.InteractiveReader \
  --project-entitlements ios/InteractiveReader/InteractiveReader/Supporting/InteractiveReader.entitlements \
  --output "$DERIVED/MergedEntitlements/InteractiveReader.entitlements.plist"
python3 scripts/apple_merge_entitlements.py \
  --profile "$WILDCARD_IOS_EXTENSION_PROFILE" \
  --bundle-id com.example.InteractiveReader.NotificationServiceExtension \
  --output "$DERIVED/MergedEntitlements/NotificationServiceExtension.entitlements.plist"

find "$APPEX" -maxdepth 1 -type f -name '*.dylib' -print0 \
  | xargs -0 -I{} /usr/bin/codesign --force --sign "$APPLE_DEVELOPMENT_IDENTITY" --timestamp=none "{}"
/usr/bin/codesign --force --sign "$APPLE_DEVELOPMENT_IDENTITY" --timestamp=none \
  --entitlements "$DERIVED/MergedEntitlements/NotificationServiceExtension.entitlements.plist" "$APPEX"
find "$APP" -maxdepth 1 -type f -name '*.dylib' -print0 \
  | xargs -0 -I{} /usr/bin/codesign --force --sign "$APPLE_DEVELOPMENT_IDENTITY" --timestamp=none "{}"
/usr/bin/codesign --force --sign "$APPLE_DEVELOPMENT_IDENTITY" --timestamp=none \
  --entitlements "$DERIVED/MergedEntitlements/InteractiveReader.entitlements.plist" "$APP"
/usr/bin/codesign --verify --deep --strict --verbose=4 "$APP"

APPLE_DEVICE_ID="<device-id-or-name>" \
APPLE_DEVICE_APP_PATH="$APP" \
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh \
  --skip-build --install --launch --launch-console-timeout 10
```

For the June 24 `.27` iPad Pro install, `APPLE_DEVICE_ID="Fifo Ipad Pro"`
worked for CoreDevice preflight but not as an `xcodebuild` destination id; the
helper now resolves friendly names through `devicectl device info details` and
passes the hardware UDID (`00008142-001C71AE3AC2401C`) to `xcodebuild`.
The successful manual signing pass used `scripts/apple_merge_entitlements.py`
for both bundles. The app entitlements combine the project iCloud/Push/Sign in
with Apple values with profile-generated `application-identifier`,
`com.apple.developer.team-identifier`, `get-task-allow`, and
`keychain-access-groups`, and replace the placeholder ubiquity kvstore value
with `3Y7288895K.com.example.InteractiveReader`. The notification extension
is signed with its own `application-identifier`, team id, `get-task-allow`,
and keychain group. Signing the app only with
`InteractiveReader.entitlements` passes local `codesign --verify` but fails
device install with `0xe8008015`.

For Apple TV local dry-runs, use the repo-owned profile instead of manually
overriding scheme, bundle id, and output folder:

```bash
bash scripts/apple_unattended_device_update.sh \
  --device "<apple-tv-id-or-name>" \
  --profile appletv \
  --dry-run \
  --build-only
```

The `appletv` profile resolves `InteractiveReaderTV`,
`com.example.InteractiveReader.tvos`, and
`Debug-appletvos/InteractiveReaderTV.app`; physical install still requires the
explicit `CONFIRM_PHYSICAL_DEVICE_UPDATE=YES` guard and an explicit deploy
request.

On the successful June 24 run, `devicectl` verified the same stable build on
iPad Pro and iPhone, and the launch console showed remote notification
registration:

```text
InteractiveReader   com.example.InteractiveReader   2026.6.24   2026062427
```

Those capabilities are declared by `InteractiveReader.entitlements` and are part
of the iOS/iPadOS app contract. Treat CLI signing failures as an Xcode
account/profile refresh gate or use the full-entitlement manual codesign
fallback above; do not remove or strip the iCloud/Sign in with Apple/Push
entitlements when validating device features.
The older entitlement-stripping fallback now requires
`APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES` and should stay locked for any
iCloud, Push Notifications, or Sign in with Apple validation.

To inspect local cached profile capability shape without printing secrets, run:

```bash
python3 scripts/ios_profile_capability_check.py \
  --bundle-id com.example.InteractiveReader \
  --entitlements ios/InteractiveReader/InteractiveReader/Supporting/InteractiveReader.entitlements \
  --embedded-bundle-id com.example.InteractiveReader.NotificationServiceExtension
```

The checker filters profiles to `iOS` by default, reports profile UUIDs, app-id
suffixes, platforms, paths, and whether a profile is Xcode-managed, and accepts
iOS wildcard profiles only for embedded bundle IDs that do not declare their own
entitlement file.

The shared pipeline signing contract should pass before physical deploy:

```bash
python3 scripts/check_app_signing_contract.py --app ebook-tools --profile ipad
```

This contract checks both `~/Library/MobileDevice/Provisioning Profiles` and
Xcode-managed profiles under `~/Library/Developer/Xcode/UserData/Provisioning
Profiles`, including plain `*` wildcard profiles for embedded extension bundle
ids.

- After every pushed Apple app checkpoint, refresh the Mac Studio runtime clone
  and recheck source sync:

```bash
ssh mac-studio.local 'cd /Users/fifo/Projects/home/ebook-tools && git pull --ff-only'
python3 scripts/check_app_source_sync.py --app ebook-tools
```

Current checkpoint on June 24, 2026: local MacBook and Mac Studio clones are
clean on `main` at `13a5b5ab`; the Mac Studio backend image was rebuilt with
`docker compose up -d --build backend`, and `make apple-pipeline-source-sync`
plus `make apple-pipeline-backend` pass against
`https://api.langtools.fifosk.synology.me`. The shared backend checker must read
the full `/api/system/runtime` response, because the Apple Create, template,
Library, offline export, and playback-state descriptor now exceeds 2 KB.

### Quick Start

```bash
# Install dev dependencies
pip install -e .[dev]

# Run the full suite (801+ tests)
pytest

# Run a specific domain
pytest -m webapi

# Fast feedback loop (skip slow and integration tests)
make test-fast
```

### Targeted Testing (Preferred)

Targeted test runs are the recommended workflow. They complete in seconds rather
than minutes, keep feedback tight, and let you focus on the domain you are
changing. Only run the full suite for wide-ranging changes like core refactors,
dependency upgrades, or configuration changes that touch many modules.

#### Marker Reference

All markers are defined in `pyproject.toml` under `[tool.pytest.ini_options]`.

| Marker | Domain | Description |
|--------|--------|-------------|
| `webapi` | Web API | FastAPI routes, middleware, CORS, auth endpoints |
| `services` | Services | Job manager, pipeline service, file locator, assistant |
| `pipeline` | Pipeline | Core rendering pipeline, multi-sentence chunks, timeline |
| `audio` | Audio | TTS backends, voice selection, audio highlighting |
| `translation` | Translation | Translation engine, batch processing, CJK tokenization |
| `metadata` | Metadata | Metadata enrichment, structured conversion, library metadata |
| `cli` | CLI | Command-line interface, args parsing, user commands |
| `auth` | Auth | User management, session management, auth service |
| `library` | Library | Library sync, indexer, repository |
| `render` | Render | Output writer, text pipeline, parallel dispatch |
| `media` | Media | Command runner, media backends |
| `config` | Config | Config manager, storage settings, runtime context |
| `ramdisk` | RAMDisk | RAMDisk lifecycle, guard, mount/unmount |
| `observability` | Observability | Prometheus metrics, dashboard PromQL coverage, JSON validation |
| `slow` | Slow | Tests that take >2s (WhisperX, Piper, pipelines) |
| `integration` | Integration | End-to-end workflows requiring external services |
| `e2e` | E2E | Browser/device tests via Playwright (requires running app) |

#### Examples

```bash
# Run a single domain
pytest -m webapi
pytest -m audio
pytest -m translation

# Combine markers
pytest -m "services or pipeline"
pytest -m "not slow and not integration"

# Run a specific test file
pytest tests/modules/webapi/test_job_media_routes.py -v

# Run a specific test by name
pytest -k "test_dashboard_loads" -v
```

### Makefile Shortcuts

The Makefile provides convenient targets for every domain. Makefile pytest
targets run through `$(PYTHON) -m pytest`, using `.venv/bin/python` when
available and `python3` otherwise.

| Target | Command | Description |
|--------|---------|-------------|
| `make test` | `$(PYTHON) -m pytest` | Full suite (801+ tests) |
| `make test-fast` | `$(PYTHON) -m pytest -m "not slow and not integration"` | Skip slow and integration tests |
| `make test-audio` | `$(PYTHON) -m pytest -m audio` | TTS backends and audio tests |
| `make test-translation` | `$(PYTHON) -m pytest -m translation` | Translation engine tests |
| `make test-webapi` | `$(PYTHON) -m pytest -m webapi` | FastAPI route tests |
| `make test-backend-library-search-source-isbn` | `$(PYTHON) -m pytest ...` | Shared-pipeline Library, Search, source upload, and ISBN backend slice |
| `make test-backend-admin-system-status` | `$(PYTHON) -m pytest ...` | Shared-pipeline admin system status backend slice |
| `make test-backend-create-book` | `$(PYTHON) -m pytest ...` | Shared-pipeline generated-book backend slice |
| `make test-backend-creation-templates` | `$(PYTHON) -m pytest ...` | Shared-pipeline saved creation-template backend slice |
| `make test-backend-subtitle-router` | `$(PYTHON) -m pytest ...` | Shared-pipeline subtitle router backend slice |
| `make test-backend-youtube-dubbing-service` | `$(PYTHON) -m pytest ...` | Shared-pipeline YouTube dubbing/download route and service slice |
| `make test-web-create-book-focused` | `npm --prefix web test -- --run ...` | Focused generated-book Create page Vitest slice |
| `make test-web-create-intake-focused` | `npm --prefix web test -- --run ...` | Focused Create intake and narration form Vitest slice |
| `make test-web-creation-templates-focused` | `npm --prefix web test -- --run ...` | Focused saved creation-template sanitizer and payload Vitest slice |
| `make test-web-library-focused` | `npm --prefix web test -- --run ...` | Focused Library metadata Vitest slice |
| `make test-web-video-dubbing-focused` | `npm --prefix web test -- --run ...` | Focused Video Dubbing utility, hook, and page Vitest slice |
| `make test-web-subtitle-tool-focused` | `npm --prefix web test -- --run ...` | Focused Subtitle Tool utility and hook Vitest slice |
| `make test-web-app-view-deeplink-focused` | `npm --prefix web test -- --run ...` | Focused app-view deeplink utility Vitest slice |
| `make test-web-full` | `npm --prefix web test -- --run` | Full Web Vitest suite |
| `make build-web-production` | `npm --prefix web run build` | Production app and export-player build |
| `make test-services` | `$(PYTHON) -m pytest -m services` | Job manager and service tests |
| `make test-pipeline` | `$(PYTHON) -m pytest -m pipeline` | Core pipeline tests |
| `make test-cli` | `$(PYTHON) -m pytest -m cli` | CLI argument and command tests |
| `make test-auth` | `$(PYTHON) -m pytest -m auth` | Authentication and session tests |
| `make test-library` | `$(PYTHON) -m pytest -m library` | Library sync and indexer tests |
| `make test-render` | `$(PYTHON) -m pytest -m render` | Output writer and text pipeline tests |
| `make test-media` | `$(PYTHON) -m pytest -m media` | Media command runner tests |
| `make test-config` | `$(PYTHON) -m pytest -m config` | Config manager tests |
| `make test-metadata` | `$(PYTHON) -m pytest -m metadata` | Metadata enrichment tests |

### Full Suite

Run the full suite when your changes are wide-ranging:

- Core refactors that touch shared utilities
- Dependency upgrades (`pip install --upgrade`)
- Configuration schema changes
- Fixture or conftest modifications

```bash
# Full suite
pytest

# With coverage report
pytest --cov=modules

# Verbose output
pytest -v
```

## Test Architecture

### Directory Structure

```
tests/
├── conftest.py                          # Session fixtures, ramdisk patches, CLI options
├── helpers/
│   └── job_manager_stubs.py             # Canonical PipelineInput/PipelineRequest stubs
├── stubs/                               # Lightweight stand-ins for optional dependencies
│   ├── pydantic_settings/
│   ├── pydantic/
│   └── pydub/
├── modules/
│   ├── audio/                           # TTS backend tests
│   │   ├── test_tts_backends.py
│   │   ├── test_tts_voice_selection.py
│   │   └── test_piper_backend.py
│   ├── cli/                             # CLI tests
│   │   ├── test_args.py
│   │   ├── test_assets.py
│   │   ├── test_context.py
│   │   ├── test_pipeline_runner.py
│   │   └── test_user_commands.py
│   ├── config_manager/
│   │   └── test_storage_settings.py
│   ├── core/                            # Pipeline and rendering tests
│   │   ├── test_exporter_audio_tracks.py
│   │   ├── test_multi_sentence_chunks.py
│   │   ├── test_pipeline_config_defaults.py
│   │   ├── test_pipeline_voice_logging.py
│   │   ├── test_rendering_exporters.py
│   │   ├── test_storage_config.py
│   │   └── test_timeline_builder.py
│   ├── library/                         # Library sync and indexer tests
│   │   ├── test_indexer.py
│   │   ├── test_library_metadata.py
│   │   ├── test_library_repository.py
│   │   ├── test_library_service.py
│   │   └── test_subtitle_library.py
│   ├── lookup_cache/                    # Lookup cache tests
│   ├── media/                           # Media command runner tests
│   │   └── test_command_runner.py
│   ├── render/                          # Output writer and parallel dispatch tests
│   │   ├── backends/
│   │   │   └── test_polly.py
│   │   ├── test_output_writer.py
│   │   ├── test_parallel.py
│   │   ├── test_polly_api_client.py
│   │   └── test_text_pipeline.py
│   ├── services/                        # Job manager, pipeline, metadata tests
│   │   ├── conftest.py
│   │   ├── job_manager/
│   │   │   └── test_executor.py
│   │   ├── metadata/
│   │   │   ├── test_metadata_enrichment.py
│   │   │   ├── test_metadata_integration.py
│   │   │   └── test_structured_conversion.py
│   │   ├── test_assistant.py
│   │   ├── test_config_phase.py
│   │   ├── test_file_locator.py
│   │   ├── test_job_manager_*.py        # Multiple job manager test files
│   │   ├── test_request_factory.py
│   │   └── test_youtube_dubbing_*.py    # YouTube dubbing tests
│   ├── translation/                     # Translation engine tests
│   │   ├── test_googletrans_provider.py
│   │   ├── test_token_alignment.py
│   │   ├── test_translation_batch.py
│   │   ├── test_translation_engine_quality.py
│   │   ├── test_translation_integration.py
│   │   ├── test_translation_logging.py
│   │   ├── test_translation_validation.py
│   │   └── test_translation_workers.py
│   ├── user_management/                 # Auth service and session tests
│   │   ├── test_auth_service.py
│   │   ├── test_local_user_store.py
│   │   └── test_session_manager.py
│   ├── webapi/                          # FastAPI route tests
│   │   ├── conftest.py
│   │   ├── test_admin_user_routes.py
│   │   ├── test_application_cleanup.py
│   │   ├── test_assistant_routes.py
│   │   ├── test_audio_routes.py
│   │   ├── test_dashboard_access_control.py
│   │   ├── test_dependencies.py
│   │   ├── test_job_cover_route.py
│   │   ├── test_job_media_routes.py
│   │   ├── test_library_media_*.py
│   │   ├── test_search_routes.py
│   │   ├── test_storage_file_download.py
│   │   └── test_system_routes.py
│   ├── test_audio_highlight.py
│   ├── test_image_prompting.py
│   ├── test_language_policies.py
│   ├── test_pipeline_job_manager_state.py
│   ├── test_runtime_tmp_dir.py
│   ├── test_subtitles_processing.py
│   └── test_whisperx_alignment.py
├── integration/                         # Integration tests (require external services)
│   ├── test_cjk_tokenization.py
│   ├── test_piper_whisperx_pipeline.py
│   └── test_word_timing_validation.py
├── library/
│   └── test_library_sync.py
├── e2e/                                 # End-to-end tests (on-demand)
│   ├── conftest.py                      # Playwright setup, auth, base URL
│   ├── journeys/                        # Shared JSON journey definitions
│   │   └── basic_playback.json
│   ├── journey_runner.py                # WebJourneyRunner (Playwright)
│   ├── report.py                        # Markdown report generator plugin
│   ├── test_login_and_playback.py       # Login flow and player tests
│   └── test_journeys.py                 # Parametrized journey runner
└── bruno/                               # Bruno API collection (manual testing)
    └── ebook-tools/
```

### Key Testing Patterns

#### Monkeypatch Best Practice

Always use object-based monkeypatch, not string-based paths. String-based
patching breaks with namespace packages:

```python
# Correct: object-based patching
import modules.ramdisk_manager as rm
monkeypatch.setattr(rm, "ensure_ramdisk", lambda: False)

# Wrong: string-based patching (breaks with namespace packages)
monkeypatch.setattr("modules.ramdisk_manager.ensure_ramdisk", lambda: False)
```

#### Session Fixtures

The root `tests/conftest.py` provides session-scoped fixtures that apply to all
tests:

- **`_disable_ramdisk_globally`** (autouse, session) - Patches `ensure_ramdisk`,
  `teardown_ramdisk`, and `is_mounted` to no-ops. RAMDisk lifecycle is owned by
  the API; tests must never trigger real `diskutil` subprocess calls. Individual
  tests that need to exercise RAMDisk logic can override with `monkeypatch`.

- **`epub_job_cli_overrides`** (session) - Collects CLI options like
  `--sample-sentence-count`, `--sample-target-language`, and `--sample-topic`
  for integration tests that generate sample EPUBs.

- **HuggingFace environment** - Configures the HF cache directory at module
  load time (before pytest collects tests) via `configure_hf_environment()`.
  If the workstation environment points `EBOOK_HF_CACHE_PATH` at an offline or
  unwritable external volume, pytest falls back to a local temporary cache
  (`/tmp/ebook-tools-test-hf-cache` by default, or `EBOOK_TEST_HF_CACHE_PATH`).
  This fallback is test-only; production API/container startup should keep
  failing visibly when model storage is misconfigured.

#### PipelineInput Stubs

The canonical test stub lives in `tests/helpers/job_manager_stubs.py`. It
installs lightweight stand-ins for `PipelineInput`, `PipelineRequest`,
`PipelineResponse`, `MetadataLoader`, `TranslationTask`, and related classes
when the real modules are not available. Key fields to note:

- `media_metadata` (not `book_metadata`)
- `add_images: bool` is required
- `generate_video` has been removed

#### WebAPI Test Client

WebAPI tests use FastAPI's `TestClient` via the `test_client` fixture defined
in `tests/modules/webapi/conftest.py`. This creates an in-process ASGI client
without starting a real server.

## Observability Tests

The observability test suite validates the Prometheus metrics pipeline and
Grafana dashboard integrity end-to-end.

```bash
pytest -m observability -v
make test-observability          # same via Makefile
```

### Test Layers

| Layer | Tests | What it validates |
|-------|-------|-------------------|
| Metric presence | Custom metrics | Every `ebook_tools_*` metric exists in `/metrics` with the correct Prometheus type |
| Label cardinality | 5 | Labelled metrics expose expected label names |
| Dashboard coverage | 1 | Every PromQL expression in all 4 dashboards references an existing metric |
| HTTP auto-instrumentation | 2 | API traffic generates `http_request_duration_seconds`; `/metrics` is excluded |
| Auth counter | 1 | Failed login increments `ebook_tools_auth_attempts_total{result="failure"}` |
| Dashboard JSON structure | 1 | All 4 dashboards have valid Grafana JSON with correct datasource UIDs |

The **dashboard coverage test** is particularly valuable: it parses every
PromQL expression from all dashboard JSON files and verifies that each
referenced metric name exists in either the `/metrics` endpoint output or
a known list of external metrics (e.g., `pg_stat_*`).

---

## E2E Testing

E2E tests are **not** part of the regular test suite. They are on-demand only
and require:

- A running API server (production or local)
- Credentials configured in `.env` (`E2E_USERNAME`, `E2E_PASSWORD`)
- Platform-specific tooling (Playwright for Web, Xcode for Apple)

### Architecture: Shared JSON Journeys

E2E tests use a shared journey architecture where platform-agnostic test
scenarios are defined in JSON and interpreted by platform-specific runners.
Steps may include a `platforms` array when a check belongs only to a specific
surface, such as `["tvOS"]` for an Apple TV-only Create smoke check or
`["web"]` for a Web-only assertion.

```
tests/e2e/journeys/*.json          # Journey definitions (shared)
        |
        +--- WebJourneyRunner      # Python (Playwright) for Web
        |    (journey_runner.py)
        |
        +--- JourneyRunner         # Swift (XCUITest) for iPhone/iPad/tvOS
             (JourneyRunner.swift)
```

Adding a new JSON journey file automatically propagates to all 4 platforms
without any code changes.

#### Journey Step Types

| Step | Description |
|------|-------------|
| `login` | Verify authenticated session loaded (Web uses storage state) |
| `navigate_tab` | Navigate to a sidebar tab (Jobs, Library) |
| `select_filter` | Select a content filter (Books, Video, Subtitles) |
| `play_first_item` | Click the first playable item; optionally skip if empty |
| `go_back` | Return to the previous view (SPA close / edge swipe / Menu button) |
| `assert_visible` | Assert a CSS selector is visible with optional timeout |
| `wait` | Wait for a specified number of milliseconds |
| `platforms` | Optional per-step filter; Web accepts `web`/`browser`, Apple accepts `iPhone`, `iPad`, or `tvOS` |

#### Example Journey

```json
{
  "id": "basic_playback",
  "name": "Basic Book Playback",
  "description": "Login, navigate to Jobs, play a book, return to menu",
  "steps": [
    { "action": "login", "screenshot": "after_login" },
    { "action": "navigate_tab", "tab": "Jobs", "screenshot": "jobs_tab" },
    { "action": "select_filter", "filter": "Books", "screenshot": "books_filter" },
    { "action": "play_first_item", "screenshot": "player_opened", "skip_if_empty": true },
    { "action": "go_back", "screenshot": "returned_to_menu" }
  ]
}
```

### Web E2E (Playwright)

**Prerequisites:**

```bash
pip install -e .[e2e]
playwright install
```

**Key files:**

| File | Purpose |
|------|---------|
| `tests/e2e/conftest.py` | Base URL resolution, credentials, auth token, storage state |
| `tests/e2e/journey_runner.py` | `WebJourneyRunner` class that maps journey steps to Playwright actions |
| `tests/e2e/test_journeys.py` | Parametrized test that auto-discovers and runs all journeys |
| `tests/e2e/test_login_and_playback.py` | Manual login flow and player rendering tests |
| `tests/e2e/report.py` | Markdown report generator plugin (`--e2e-report` flag) |

**Running:**

| Target | Mode | Report |
|--------|------|--------|
| `make test-e2e-web` | Headed, slow-mo 200ms | `test-results/web-e2e-report.md` |
| `make test-e2e-web-headless` | Headless | `test-results/web-e2e-report.md` |
| `make test-e2e` | Headed (legacy) | `test-results/e2e-report.md` |
| `make test-e2e-headless` | Headless (legacy) | `test-results/e2e-report.md` |

**Authentication flow:** The `conftest.py` fixtures handle authentication
once per session:

1. `e2e_credentials` reads `E2E_USERNAME`/`E2E_PASSWORD` from environment
2. `auth_token` calls `POST /api/auth/login` to get a JWT
3. `storage_state_path` injects the token into `localStorage` and saves
   Playwright storage state
4. `browser_context_args` loads the saved state into every test context
5. `authenticated_page` provides a page already navigated to the app root

### Apple E2E (XCUITest)

**Prerequisites:**

- Xcode with iOS and tvOS simulators
- `E2E_USERNAME` and `E2E_PASSWORD` set in `.env` or supplied as environment
  variables by the shared Apple pipeline wrapper

**Key files (iOS):**

| File | Purpose |
|------|---------|
| `InteractiveReaderUITests/JourneyRunner.swift` | Swift journey runner (interprets JSON steps) |
| `InteractiveReaderUITests/JourneyTests.swift` | Discovers and runs JSON journeys |
| `InteractiveReaderUITests/LoginTests.swift` | Login flow tests |
| `InteractiveReaderUITests/PlaybackTests.swift` | Player interaction tests |
| `InteractiveReaderUITests/LibraryTests.swift` | Library browsing tests |
| `InteractiveReaderUITests/TestHelpers.swift` | Shared test utilities |

**XCUITest schemes:**

- `InteractiveReaderUITests` - iOS E2E tests (iPhone and iPad)
- `InteractiveReaderTVUITests` - tvOS E2E tests (Apple TV)

Both schemes are checked in under
`ios/InteractiveReader/InteractiveReader.xcodeproj/xcshareddata/xcschemes/` so
repo-owned Make targets do not depend on per-user Xcode scheme state.

**Running:**

| Target | Simulator | Report |
|--------|-----------|--------|
| `make test-e2e-iphone` | iPhone 17 Pro | `test-results/iphone-e2e-report.md` |
| `make test-e2e-ipad` | iPad Pro 13-inch (M5) | `test-results/ipad-e2e-report.md` |
| `make test-e2e-tvos` | Apple TV 4K (3rd generation) | `test-results/tvos-e2e-report.md` |
| `make test-e2e-ios` | (alias for `test-e2e-iphone`) | |

Override `IPHONE_DESTINATION`, `IPAD_DESTINATION`, or `TVOS_DESTINATION` when a
different installed simulator model is needed.

Create-readiness probes use `tests/e2e/journeys/create_readiness.json` to open
native Apple Create, type a generated-book continuation context, and verify
that Narrate EPUB, subtitle, and YouTube dubbing source fields auto-populate
from backend-visible sources:

```bash
make test-e2e-iphone-create-readiness
make test-e2e-ipad-create-readiness
make test-e2e-tvos-create-readiness
make test-e2e-apple-create-readiness
```

These probes are intentionally stricter than the default playback journey and
should be run against an API whose EPUB, subtitle, and YouTube/NAS inventories
are expected to be populated. They run
`scripts/check_apple_create_readiness.py` before Xcode starts; the preflight
requires `E2E_USERNAME` and `E2E_PASSWORD` from the environment or
`E2E_ENV_FILE` (defaulting to `.env`, then `.env.local`), uses
`E2E_API_BASE_URL` when set, and reports only aggregate inventory counts.
HTTP failures name the exact API path, so a message such as
`/api/books/options` returning 404 means the target backend has not yet been
updated to the modern book-creation options contract used by Apple Create.

**Configuration:** The Makefile writes credentials and journey data to
temporary files that XCUITest reads at runtime:

- `/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_config.json` - Contains `username`, `password`, `api_base_url`
- `/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_journey.json` - Copy of the journey JSON for the test run

Values from the process environment override `E2E_ENV_FILE`, so commands such as
`run_app_owned_journey.py --env E2E_API_BASE_URL=...` can inject simulator-safe
configuration without editing local files. These temporary files are cleaned up
after each run. The Makefile writes them through
`scripts/write_apple_e2e_config.py`, which shares the preflight env-file
parsing behavior: single- or double-quoted values such as
`E2E_USERNAME='editor'` are stripped before XCUITest reads the temporary config.
For reusable-pipeline profiles such as `ipados-create`, the writer also mirrors
the files to the platform default profile (`ipados`, `iphone`, or `tvos`) so the
XCTest bundle can still load them when Xcode does not propagate shell
environment variables into the test runner.

```bash
E2E_ENV_FILE=.env.local make test-e2e-ipad-create-readiness
```

**Platform-specific behaviors:**

- **iPhone/iPad:** Back navigation uses edge swipe gesture
- **tvOS:** Back navigation uses `XCUIRemote.shared.press(.menu)` (Siri Remote)
- **tvOS text input:** Uses the Siri Remote text entry flow
  (Select, type, Menu, Down, Select, type, Menu, Down, Select)

**Screenshot prefixes:** Each platform uses a unique prefix (`iphone`, `ipad`,
`tvos`) to prevent cross-platform screenshot filename collisions. Without
prefixes, the default `ios` prefix would cause overwrites.

### All Platforms

Run all 4 E2E suites sequentially:

```bash
make test-e2e-all
```

This runs Web (headless), iPhone, iPad, and tvOS in sequence. Parallel
execution (`-j4`) is intentionally avoided because it corrupts xcresult
bundles due to an Xcode `mkstemp` bug.

The target uses `-k` (continue on failures) so that one platform failing
does not block the others.

### E2E Configuration

| Setting | Source | Default |
|---------|--------|---------|
| E2E username | `E2E_USERNAME` env var in `.env` | (required) |
| E2E password | `E2E_PASSWORD` env var in `.env` | (required) |
| Web base URL | `E2E_BASE_URL` env var or `--e2e-base-url` flag | `https://langtools.fifosk.synology.me` |
| API base URL | Derived from Web base URL | `https://api.langtools.fifosk.synology.me` |

The shared user account (`playwright_e2e`) has the `admin` role.

### Adding New E2E Journeys

1. Create a new JSON file in `tests/e2e/journeys/` (e.g., `library_browse.json`)
2. Define the journey steps using the supported step types
3. The journey is automatically discovered by all 4 platform runners
4. No code changes are needed -- run `make test-e2e-all` to verify

```json
{
  "id": "library_browse",
  "name": "Browse Library",
  "description": "Login, navigate to Library, browse items",
  "steps": [
    { "action": "login", "screenshot": "after_login" },
    { "action": "navigate_tab", "tab": "Library", "screenshot": "library_tab" },
    { "action": "assert_visible", "selector": ".library-grid", "screenshot": "library_grid" }
  ]
}
```

## Test Reports

### Unit and Integration Tests

Standard pytest terminal output. Use `-v` for verbose or `--tb=short` for
shorter tracebacks:

```bash
pytest -m webapi -v --tb=short
```

### E2E Reports

E2E runs produce Markdown reports with embedded screenshots:

| Report | Generated By |
|--------|-------------|
| `test-results/web-e2e-report.md` | Playwright `--e2e-report` plugin |
| `test-results/iphone-e2e-report.md` | `scripts/ios_e2e_report.py` (parses xcresult) |
| `test-results/ipad-e2e-report.md` | `scripts/ios_e2e_report.py` |
| `test-results/tvos-e2e-report.md` | `scripts/ios_e2e_report.py` |

Reports include:

- Summary table (pass/fail/skip counts, total duration)
- Per-test results with error details in collapsible sections
- Screenshots at 300px width with per-platform filename prefixes
- Designed to render correctly on GitHub

### Coverage

```bash
# Generate coverage report
pytest --cov=modules

# HTML coverage report
pytest --cov=modules --cov-report=html
# Open htmlcov/index.html
```

## CLI Options for Tests

The test suite accepts custom CLI options for specialized scenarios:

| Option | Group | Description |
|--------|-------|-------------|
| `--sample-sentence-count` | epub-job | Number of sentences for sample EPUB generation |
| `--sample-input-language` | epub-job | Input language for generated EPUB |
| `--sample-target-language` | epub-job | Target language(s) (repeatable or comma-separated) |
| `--sample-topic` | epub-job | Topic for sample sentences |
| `--run-llm` | cjk-tokenization | Run tests requiring a real LLM connection |
| `--llm-model` | cjk-tokenization | LLM model for translation (e.g., `mistral:latest`) |
| `--save-report` | cjk-tokenization | Path to save JSON test report |
| `--e2e-base-url` | e2e | Base URL for the web app under test |
| `--e2e-report` | e2e | Generate Markdown E2E report (optional path) |
| `--e2e-report-title` | e2e | Title for the Markdown report |

## Troubleshooting

### Tests fail with import errors

Ensure dev dependencies are installed:

```bash
pip install -e .[dev]
```

### RAMDisk-related test failures

The session-scoped `_disable_ramdisk_globally` fixture patches RAMDisk
operations to no-ops. If a test needs to exercise RAMDisk logic, it should
use `monkeypatch` to override the session patch locally:

```python
def test_ramdisk_mount(monkeypatch):
    import modules.ramdisk_manager as rm
    monkeypatch.setattr(rm, "ensure_ramdisk", my_mock_impl)
    # ...
```

### E2E tests are skipped

Check that `E2E_USERNAME` and `E2E_PASSWORD` are set in your `.env` file:

```bash
E2E_USERNAME=playwright_e2e
E2E_PASSWORD=your_password_here
```

### Playwright browser not installed

```bash
pip install -e .[e2e]
playwright install
```

### XCUITest config not found

The Makefile writes config to
`/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_config.json`.
If tests fail with config errors, verify `.env` contains valid credentials or pass
`E2E_USERNAME`, `E2E_PASSWORD`, and `E2E_API_BASE_URL` in the process
environment, then try running the make target again.
