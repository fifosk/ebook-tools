# ebook-tools Changelog

Daily user-visible changes for the Apple app and shared home pipeline dogfood.

## 2026-06-21

### 2026.06.21.02

- Added a release-version contract check that keeps iOS/tvOS Info plists, in-app changelog data, Markdown changelog, and journey assertions aligned.
- Advanced the visible Apple app release badge to `v2026.06.21.02`.

### 2026.06.21.01

- Added visible release versioning across iPhone, iPad, and Apple TV surfaces with `v2026.06.21.01`.
- Added an in-app daily changelog summary on login and in Settings.
- Added Settings connection evidence for API host, signed-in session, Keychain token storage, and backend runtime descriptor status.
- Added the public backend runtime descriptor at `/api/system/runtime` so simulator and device workflows can verify the expected service without credentials.
- Added shared pipeline backend preflight checks for `/_health` and `/api/system/runtime`.
- Added app-owned journey assertions for stable navigation surfaces, Settings connection rows, changelog visibility, and visible version badge.
- Added Apple TV dogfood recovery guidance for reboot, clean reinstall, and manual launch after CoreDevice or tvOS foreground-state issues.
