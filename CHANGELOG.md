# ebook-tools Changelog

Daily user-visible changes for the Apple app and shared home pipeline dogfood.

## 2026-06-21

### 2026.06.21.05

- Hardened version badge layout so `v2026.06.21.05` owns its text width before decoration and cannot collapse into a tall narrow shape.
- Split crowded iPad browse headers into stable brand/account and status/action rows so toolbar controls do not squeeze the version.
- Let changelog headers fall back to a vertical title/date stack instead of compressing the full daily version label.

### 2026.06.21.04

- Reworked the login/header version badge so `v2026.06.21.04` owns enough horizontal space and cannot collapse into vertically stacked characters on iPad.
- Switched compact toolbar headers to `v06.21.04` while keeping the full daily version in the login and changelog surfaces.

### 2026.06.21.03

- Fixed the iPad release badge so `v2026.06.21.03` stays as a single horizontal pill in crowded headers.
- Aligned Apple bundle metadata with the daily release so device inventory can report `2026.6.21 (2026062103)` instead of `1.0 (1)`.

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
