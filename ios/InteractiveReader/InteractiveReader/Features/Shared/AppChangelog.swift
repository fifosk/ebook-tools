import SwiftUI

struct AppChangelogEntry: Identifiable, Equatable {
    let id: String
    let title: String
    let detail: String
}

struct AppChangelogDay: Identifiable, Equatable {
    let id: String
    let dateLabel: String
    let version: String
    let entries: [AppChangelogEntry]
}

enum AppChangelog {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-22",
            dateLabel: "June 22, 2026",
            version: "2026.06.22.41",
            entries: [
                AppChangelogEntry(
                    id: "video-subtitle-settings-selection-handlers",
                    title: "Subtitle settings cleaned up",
                    detail: "Video subtitle settings now route close, segment, subtitles-off, and track selection work through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "video-speed-menu-row-handlers",
                    title: "Video speed menu cleaned up",
                    detail: "Shared video speed menus now route rate rows and selection work through named SwiftUI helpers."
                ),
                AppChangelogEntry(
                    id: "interactive-player-menu-row-helpers",
                    title: "Player menu rows cleaned up",
                    detail: "Interactive player audio, speed, reading-bed, and settings menu rows now use named SwiftUI helpers, and the shared pipeline now keeps physical installs on-request only."
                ),
                AppChangelogEntry(
                    id: "interactive-player-keyboard-command-handlers",
                    title: "iPad keyboard commands cleaned up",
                    detail: "Interactive player keyboard shortcut commands now route through named SwiftUI handlers shared by the iPad input layers."
                ),
                AppChangelogEntry(
                    id: "interactive-player-layout-handlers",
                    title: "Player layout updates cleaned up",
                    detail: "Interactive player music-picker, bookmark-identity, and reading-bed URL reactions now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "interactive-transcript-layout-handlers",
                    title: "Transcript layout updates cleaned up",
                    detail: "Interactive transcript bubble geometry and iPad split layout updates now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "subtitle-overlay-frame-handlers",
                    title: "Subtitle frame updates cleaned up",
                    detail: "Subtitle overlay token-frame preference and clear-state updates now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "text-player-frame-preference-handlers",
                    title: "Text frame updates cleaned up",
                    detail: "Text-player token-frame and tap-exclusion preference changes now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "text-player-track-toggle-handlers",
                    title: "Text track toggles cleaned up",
                    detail: "Text-player visible and hidden track header toggles now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "shortcut-help-dismiss-handlers",
                    title: "Shortcut help dismissals cleaned up",
                    detail: "Text and video shortcut-help overlays now route backdrop and close-button dismissals through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "browse-row-filter-handlers",
                    title: "Browse row taps cleaned up",
                    detail: "Jobs and Library browse rows now route row taps and tvOS filter long-press refresh actions through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "tvos-transcript-track-handlers",
                    title: "TV transcript focus cleaned up",
                    detail: "The tvOS transcript track now routes tap and long-press focus actions through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "video-overlay-subtitle-handlers",
                    title: "Video subtitle overlay cleaned up",
                    detail: "The video overlay now routes subtitle settings, phone bubble backdrop, playback-change, token-frame, and drag work through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "browse-row-menu-handlers",
                    title: "Browse row actions cleaned up",
                    detail: "Jobs and Library browse rows now route selection, delete, search, and tvOS offline menu commands through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "playback-host-video-handlers",
                    title: "Playback video hosts cleaned up",
                    detail: "Job and Library playback hosts now route fullscreen video dismissal, edge-swipe back, and preview dragging through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "backend-request-token-parser",
                    title: "Backend token parsing centralized",
                    detail: "Backend request identity now uses one token parser for Authorization headers and access_token query fallback."
                ),
                AppChangelogEntry(
                    id: "bookmark-ribbon-command-handlers",
                    title: "Bookmark ribbon cleaned up",
                    detail: "The bookmark ribbon now routes add, jump, remove, and tvOS focus movement work through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "tvos-offline-menu-command-handlers",
                    title: "TV offline menu actions cleaned up",
                    detail: "Library and Jobs offline remove and download commands on tvOS now run through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "library-row-builder-alignment",
                    title: "Library rows cleaned up",
                    detail: "The Library browse list now matches the Jobs row-builder structure, making iPad and tvOS row actions easier to audit."
                ),
                AppChangelogEntry(
                    id: "offline-sync-badge-command-handlers",
                    title: "Offline controls cleaned up",
                    detail: "Offline download, retry, and remove-copy menu work now runs through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "apple-music-picker-command-handlers",
                    title: "Apple Music picker cleaned up",
                    detail: "Apple Music picker dismiss, authorization, search, clear, stop, tab, suggestion-load, and result-selection work now runs through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "text-search-command-handlers",
                    title: "Text search controls cleaned up",
                    detail: "Interactive text search overlay toggle, dismiss, submit, query-change, and result-selection work now runs through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "video-search-command-handlers",
                    title: "Video search controls cleaned up",
                    detail: "Video search overlay toggle, dismiss, submit, query-change, and result-selection work now runs through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "bookmark-command-handlers",
                    title: "Bookmark controls cleaned up",
                    detail: "Interactive player and video bookmark menu commands plus remote bookmark create/delete work now run through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "player-menu-command-handlers",
                    title: "Player menu controls cleaned up",
                    detail: "Interactive player menu selection, playback-rate, reading-bed, text-size, seek, and voice-reset commands now run through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "music-overlay-command-handlers",
                    title: "Music overlay controls cleaned up",
                    detail: "Background music transport, volume, scrubbing, and song-selection commands now run through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "browse-list-lifecycle-handlers",
                    title: "Browse lists cleaned up",
                    detail: "Jobs and Library browse lists now route lifecycle, resume-store updates, and sidebar-collapse drag handling through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "combined-search-action-handlers",
                    title: "Browse search cleaned up",
                    detail: "Combined browse search now routes focus, resume-store updates, search clearing, and result selection through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "media-search-action-handlers",
                    title: "Search actions cleaned up",
                    detail: "Shared media search now routes submit, clear, dismiss, result selection, tvOS focus, and async search/debounce work through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "transcript-lifecycle-handlers",
                    title: "Transcript lifecycle cleaned up",
                    detail: "Transcript audio-duration recording, auto-scale measurement, bubble-change recalculation, playback cleanup, and disappear cleanup now run through named SwiftUI lifecycle handlers."
                ),
                AppChangelogEntry(
                    id: "playback-host-lifecycle-handlers",
                    title: "Playback hosts cleaned up",
                    detail: "Job and library playback hosts now route load, start-over, now-playing, scene-phase, and teardown reactions through named SwiftUI lifecycle handlers."
                ),
                AppChangelogEntry(
                    id: "video-player-lifecycle-handlers",
                    title: "Video player lifecycle cleaned up",
                    detail: "The video player now routes setup, URL changes, subtitle updates, bookmark refreshes, and playback state changes through named SwiftUI lifecycle handlers instead of inline body closures."
                ),
                AppChangelogEntry(
                    id: "typed-tv-video-control-menus",
                    title: "TV video controls typed",
                    detail: "The tvOS video overlay now passes bookmark and speed menus through typed SwiftUI controls instead of erasing those menu views before focus layout."
                ),
                AppChangelogEntry(
                    id: "typed-transcript-track-layout",
                    title: "Transcript track layout typed",
                    detail: "Phone, iPad split, and tvOS transcript layouts now pass the measured track view through typed SwiftUI helpers instead of erasing it before layout."
                ),
                AppChangelogEntry(
                    id: "typed-player-lifecycle-chain",
                    title: "Player lifecycle chain typed",
                    detail: "The interactive player layout now uses staged SwiftUI modifier chains with named lifecycle handlers instead of repeatedly erasing and rebuilding the player stack."
                ),
                AppChangelogEntry(
                    id: "typed-player-header-overlay",
                    title: "Player header overlay typed",
                    detail: "The interactive player header now uses focused SwiftUI builders instead of an erased header view, preserving phone, iPad, and tvOS layout branches while making future overlay work safer."
                ),
                AppChangelogEntry(
                    id: "typed-browse-section-picker",
                    title: "Browse header type erasure removed",
                    detail: "Jobs, Library, Search, and Settings now share a typed SwiftUI section picker instead of passing erased header views through the browse shell."
                ),
                AppChangelogEntry(
                    id: "version-changelog-split",
                    title: "Version and changelog code split",
                    detail: "Release badge metadata and daily changelog rendering now live in focused SwiftUI files instead of the shared theme primitive."
                ),
                AppChangelogEntry(
                    id: "pytest-hf-cache-fallback",
                    title: "MacBook backend tests hardened",
                    detail: "Pytest now uses a local HuggingFace cache when workstation env points at offline external model storage, while production still fails visibly on bad runtime paths."
                ),
                AppChangelogEntry(
                    id: "browse-row-action-refactor",
                    title: "Browse row actions cleaned up",
                    detail: "Library and Jobs row selection, delete, and move-to-library commands now route through named SwiftUI actions instead of inline row-builder closures."
                ),
                AppChangelogEntry(
                    id: "browse-shell-action-refactor",
                    title: "Browse shell actions cleaned up",
                    detail: "Refresh, selection, search, sign-out, and split-view navigation now route through named SwiftUI actions so the iPad browse surface is safer to iterate."
                ),
                AppChangelogEntry(
                    id: "auth-duration-metrics",
                    title: "Auth timing is observable",
                    detail: "Backend login and session checks now record token-safe duration metrics so slow sign-in reports can be diagnosed without exposing credentials."
                )
            ]
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

struct AppChangelogSummaryView: View {
    let maxEntries: Int?
    let showBuildMetadata: Bool
    let usesDarkBackground: Bool

    init(
        maxEntries: Int? = nil,
        showBuildMetadata: Bool = true,
        usesDarkBackground: Bool = true
    ) {
        self.maxEntries = maxEntries
        self.showBuildMetadata = showBuildMetadata
        self.usesDarkBackground = usesDarkBackground
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ViewThatFits(in: .horizontal) {
                ChangelogTitleRow(
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
                ChangelogTitleStack(
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
            }

            if showBuildMetadata {
                Text(AppVersion.buildLabel)
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)
                    .accessibilityIdentifier("appBuildMetadataText")
            }

            ForEach(displayEntries) { entry in
                AppChangelogEntryRow(
                    entry: entry,
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
            }
        }
        .padding(12)
        .background(backgroundStyle, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(borderStyle, lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("appChangelogSummaryView")
    }

    private var displayEntries: [AppChangelogEntry] {
        let entries = AppChangelog.days.first?.entries ?? []
        guard let maxEntries else { return entries }
        return Array(entries.prefix(maxEntries))
    }

    private var primaryStyle: Color {
        usesDarkBackground ? .white : .primary
    }

    private var secondaryStyle: Color {
        usesDarkBackground ? .white.opacity(0.72) : .secondary
    }

    private var backgroundStyle: Color {
        #if os(tvOS)
        return usesDarkBackground ? Color.white.opacity(0.07) : Color.black.opacity(0.08)
        #else
        usesDarkBackground ? Color.white.opacity(0.07) : Color(.secondarySystemBackground)
        #endif
    }

    private var borderStyle: Color {
        #if os(tvOS)
        return usesDarkBackground ? Color.white.opacity(0.12) : Color.primary.opacity(0.16)
        #else
        usesDarkBackground ? Color.white.opacity(0.12) : Color(.separator).opacity(0.4)
        #endif
    }
}

private struct ChangelogTitleRow: View {
    let primaryStyle: Color
    let secondaryStyle: Color

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            ChangelogVersionText(primaryStyle: primaryStyle)
            Spacer(minLength: 8)
            ChangelogDateText(secondaryStyle: secondaryStyle)
        }
    }
}

private struct ChangelogTitleStack: View {
    let primaryStyle: Color
    let secondaryStyle: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            ChangelogVersionText(primaryStyle: primaryStyle)
            ChangelogDateText(secondaryStyle: secondaryStyle)
        }
    }
}

private struct ChangelogVersionText: View {
    let primaryStyle: Color

    var body: some View {
        Text(AppVersion.displayLabel)
            .font(.headline)
            .monospacedDigit()
            .foregroundStyle(primaryStyle)
            .lineLimit(1)
            .minimumScaleFactor(0.9)
            .fixedSize(horizontal: true, vertical: false)
    }
}

private struct ChangelogDateText: View {
    let secondaryStyle: Color

    var body: some View {
        Text(AppChangelog.days.first?.dateLabel ?? "Latest")
            .font(.caption)
            .foregroundStyle(secondaryStyle)
            .lineLimit(1)
            .fixedSize(horizontal: true, vertical: false)
    }
}

private struct AppChangelogEntryRow: View {
    let entry: AppChangelogEntry
    let primaryStyle: Color
    let secondaryStyle: Color

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(Color.green)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(primaryStyle)
                Text(entry.detail)
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}
