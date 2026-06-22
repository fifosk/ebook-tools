enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-22",
            dateLabel: "June 22, 2026",
            version: "2026.06.22.145",
            entries: june22Entries
        ),
        AppChangelogDay(
            id: "2026-06-21",
            dateLabel: "June 21, 2026",
            version: "2026.06.21.11",
            entries: [
                AppChangelogEntry(
                    id: "root-lifecycle-modifiers",
                    title: "Root lifecycle cleaned up",
                    detail: "Notification registration, keyboard shortcuts, session restore, and offline sync now live in focused SwiftUI modifiers for safer cross-device iteration."
                ),
                AppChangelogEntry(
                    id: "explicit-version-badge-frame",
                    title: "Version badge frame hardened",
                    detail: "Version badges now render inside an explicit fixed-size shape so cramped iPad headers cannot reflow the release text into vertical characters."
                ),
                AppChangelogEntry(
                    id: "settings-section-refactor",
                    title: "Settings review surface cleaned up",
                    detail: "Connection, playback, changelog, voice, and notification settings now render through focused section components for safer iPad and tvOS iteration."
                ),
                AppChangelogEntry(
                    id: "wd-staging-pipeline-contract",
                    title: "WD staging pipeline aligned",
                    detail: "ebook-tools and Finance Review now share the same Mac Studio WD staging convention before backend maintenance."
                ),
                AppChangelogEntry(
                    id: "compact-version-build-token",
                    title: "iPad version chip fixed",
                    detail: "Compact browse headers now show the short daily build token while full release metadata remains visible in roomy surfaces."
                ),
                AppChangelogEntry(
                    id: "compact-version-chip-width",
                    title: "Compact version chip width",
                    detail: "Compact headers now use a shorter fixed-width chip with fixed-size monospaced text so the release cannot stack vertically in split view."
                ),
                AppChangelogEntry(
                    id: "version-layout-defensive-rows",
                    title: "Version layout hardened",
                    detail: "Version text now owns its ideal width before the pill is drawn, and changelog headers no longer squeeze full version labels beside the date."
                ),
                AppChangelogEntry(
                    id: "version-pill-owns-width",
                    title: "Version badge no longer squeezes",
                    detail: "The login badge now owns a full row and toolbar headers use a compact daily label so iPad cannot stack the version vertically."
                ),
                AppChangelogEntry(
                    id: "ipad-version-pill-layout",
                    title: "iPad version badge layout",
                    detail: "The release pill now stays on one line in crowded iPad headers instead of collapsing into vertical characters."
                ),
                AppChangelogEntry(
                    id: "apple-bundle-versioning",
                    title: "Device inventory versioning",
                    detail: "Installed device metadata now carries the daily build number so CoreDevice checks can identify the deployed app."
                ),
                AppChangelogEntry(
                    id: "release-contract-guard",
                    title: "Daily release contract guard",
                    detail: "A repo check now keeps Info plists, in-app changelog, Markdown changelog, and journey badge assertions in sync."
                ),
                AppChangelogEntry(
                    id: "backend-runtime-settings",
                    title: "Backend runtime visible in Settings",
                    detail: "Settings now verifies the public ebook-tools API descriptor and shows the service/version without exposing tokens."
                ),
                AppChangelogEntry(
                    id: "pipeline-backend-preflight",
                    title: "Pipeline backend preflight",
                    detail: "Simulator smoke profiles now fail fast on backend health and runtime identity before Xcode builds."
                ),
                AppChangelogEntry(
                    id: "settings-connection-keychain",
                    title: "Connection and Keychain state",
                    detail: "Settings shows API host, signed-in session, and Keychain token storage for attended device review."
                ),
                AppChangelogEntry(
                    id: "apple-tv-icon-remote",
                    title: "tvOS deployment polish",
                    detail: "Apple TV icon assets and remote-driven playback journeys are covered by the shared pipeline."
                )
            ]
        )
    ]
}
