# ebook-tools Changelog

Daily user-visible changes for the Apple app and shared home pipeline dogfood.

## 2026-06-21

### 2026.06.21.09

- Advanced visible Apple app versioning to `v2026.06.21.09`.
- Refactored Settings into focused connection, playback, changelog, voice, and notification sections so iPad and tvOS review surfaces can evolve with less layout risk.
- Restored the compact browse version chip to a journey-verified 96 pt width after the iPad geometry guard caught a too-narrow badge proposal.

### 2026.06.21.08

- Advanced visible Apple app versioning to `v2026.06.21.08`.
- Aligned ebook-tools with the shared WD staging convention at `/Volumes/WD-1TB/Data/staging/ebook-tools`, matching the Finance Review dogfood runtime staging path before backend maintenance.
- Updated the shared Apple pipeline manifest/docs/tests so both dogfood apps use storage preflights before disk-heavy Mac Studio work.

### 2026.06.21.07

- Replaced the compact browse-header version text with the short build token `b07`, while keeping the full `v2026.06.21.07` in login, Settings, changelog, metadata, and accessibility.
- Locked the compact badge to a fixed one-line text proposal so constrained iPad sidebars cannot stack release characters vertically.

### 2026.06.21.06

- Replaced the compact iPad header pill with a shorter fixed-width chip so `v2026.06.21.06` cannot collapse into vertical characters in split view.
- Switched version badge text to fixed-size monospaced rendering with an explicit chip width instead of relying on SwiftUI's compressed text proposal.

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
