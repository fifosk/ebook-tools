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
            version: "2026.06.22.93",
            entries: [
                AppChangelogEntry(
                    id: "auth-api-models-file",
                    title: "Auth API models separated",
                    detail: "Login, session, OAuth, and backend runtime descriptor payloads now live in a dedicated Models file instead of the broad API model file."
                ),
                AppChangelogEntry(
                    id: "pipeline-media-api-models-file",
                    title: "Pipeline media API models separated",
                    detail: "Media files, chunks, sentence metadata, audio tracks, and timing payloads now live in a dedicated Models file instead of the broad API model file."
                ),
                AppChangelogEntry(
                    id: "playback-state-api-models-file",
                    title: "Playback state API models separated",
                    detail: "Reading-bed, bookmark, and resume-position payloads now live in a dedicated Models file instead of the broad API model file."
                ),
                AppChangelogEntry(
                    id: "push-notification-api-models-file",
                    title: "Notification API models separated",
                    detail: "Push registration, preference, and test-notification payloads now live in a dedicated Models file instead of the broad API model file."
                ),
                AppChangelogEntry(
                    id: "lookup-cache-api-models-file",
                    title: "Lookup cache API models separated",
                    detail: "Dictionary cache response decoding now lives in a dedicated Models file instead of the broad API model file."
                ),
                AppChangelogEntry(
                    id: "media-search-api-models-file",
                    title: "Media search API models separated",
                    detail: "Search response decoding and its private logging now live in a dedicated Models file instead of the broad API model file."
                ),
                AppChangelogEntry(
                    id: "media-search-view-model-file",
                    title: "Media search state separated",
                    detail: "Async search state, debouncing, and result-target calculations now live outside the SwiftUI search controls file."
                ),
                AppChangelogEntry(
                    id: "media-search-results-views-file",
                    title: "Media search results separated",
                    detail: "Search result highlighting, result lists, and result rows now live outside the media search orchestration file."
                ),
                AppChangelogEntry(
                    id: "interactive-shortcut-help-overlay-file",
                    title: "Shortcut help overlay separated",
                    detail: "Interactive player keyboard shortcut help now lives in its own SwiftUI source file instead of the hardware input support file."
                ),
                AppChangelogEntry(
                    id: "linguist-bubble-compatibility-file",
                    title: "Linguist bubble adapters separated",
                    detail: "Backwards-compatible MyLinguist and video bubble state plus wrapper adapters now live outside the core bubble view."
                ),
                AppChangelogEntry(
                    id: "tvos-changelog-move-command-scroll",
                    title: "TV changelog remote scroll hardened",
                    detail: "The daily changelog now responds directly to Siri Remote up and down moves, keeping focus and scroll position aligned past the first visible rows."
                ),
                AppChangelogEntry(
                    id: "row-metadata-lookup-helper",
                    title: "Row metadata lookup shared",
                    detail: "Jobs and Library rows now share recursive metadata traversal and nested-path lookup helpers instead of carrying duplicate parsing code."
                ),
                AppChangelogEntry(
                    id: "job-row-cover-parsing-helper",
                    title: "Job row cover parsing separated",
                    detail: "YouTube thumbnail parsing and cover URL normalization now live outside the SwiftUI job row view."
                ),
                AppChangelogEntry(
                    id: "library-row-layout-component",
                    title: "Library row layout separated",
                    detail: "Library row compact and landscape shells now live with the shared library-row components, matching the job row layout pattern."
                ),
                AppChangelogEntry(
                    id: "job-row-layout-component",
                    title: "Job row layout separated",
                    detail: "Job row compact and landscape shells now live with the shared job-row components instead of the metadata resolver view."
                ),
                AppChangelogEntry(
                    id: "library-playback-chrome-views-file",
                    title: "Library playback chrome separated",
                    detail: "Library playback header, loading, error, unavailable, and image-reel UI now live in a dedicated SwiftUI source file."
                ),
                AppChangelogEntry(
                    id: "backend-runtime-descriptor-public-guard",
                    title: "Backend runtime descriptor guarded",
                    detail: "The public runtime descriptor now self-checks for secret-like metadata keys before serving Apple pipeline preflight details."
                ),
                AppChangelogEntry(
                    id: "tvos-changelog-row-focus",
                    title: "TV changelog remote scrolling fixed",
                    detail: "Daily changelog rows are now individual TV focus targets so the Siri Remote can move down and reveal the full entry list."
                ),
                AppChangelogEntry(
                    id: "language-flag-resolver-file",
                    title: "Language flag resolver separated",
                    detail: "Shared language flag roles, entries, and resolver tables now live outside the channel bug view file."
                ),
                AppChangelogEntry(
                    id: "player-artwork-views-file",
                    title: "Player artwork UI separated",
                    detail: "Shared YouTube, TV, and cover-stack artwork views now live outside the channel bug view file."
                ),
                AppChangelogEntry(
                    id: "player-language-flag-views-file",
                    title: "Language flag UI separated",
                    detail: "Shared player language flag rows, badges, and job glyph badges now live outside the channel bug view file."
                ),
                AppChangelogEntry(
                    id: "tvos-changelog-scroll-target",
                    title: "TV changelog scrolling fixed",
                    detail: "The TV login and settings changelog now use a bounded focusable scroll area so the remote can reveal the full daily entry list."
                ),
                AppChangelogEntry(
                    id: "player-channel-models-file",
                    title: "Player channel models separated",
                    detail: "Shared player channel variants and metrics now live outside the visual channel badge UI file."
                ),
                AppChangelogEntry(
                    id: "job-type-glyph-resolver-file",
                    title: "Job glyph mapping separated",
                    detail: "Job-type glyph mapping now lives outside the shared channel badge UI file."
                ),
                AppChangelogEntry(
                    id: "mylinguist-preferences-file",
                    title: "MyLinguist preferences separated",
                    detail: "Preference keys and TTS voice storage now live outside the shared channel badge UI file."
                ),
                AppChangelogEntry(
                    id: "changelog-summary-view-file",
                    title: "Changelog summary UI separated",
                    detail: "The visible changelog summary now lives in its own SwiftUI source file apart from changelog data."
                ),
                AppChangelogEntry(
                    id: "browse-collapse-interaction-file",
                    title: "Browse collapse gesture separated",
                    detail: "The shared iPad browse-list collapse gesture now lives in its own Swift source file."
                ),
                AppChangelogEntry(
                    id: "browse-resume-helpers-file",
                    title: "Browse resume helpers separated",
                    detail: "Shared browse resume helpers now live in their own Swift source file."
                ),
                AppChangelogEntry(
                    id: "shared-browse-resume-snapshot-provider",
                    title: "Browse resume refresh path shared",
                    detail: "Jobs, Library, and Search now use one provider for resume and iCloud snapshot refresh."
                ),
                AppChangelogEntry(
                    id: "backend-runtime-descriptor-helper",
                    title: "Backend runtime preflight contract cleaned up",
                    detail: "The public backend runtime descriptor now lives in a dedicated helper with direct contract coverage for Apple pipeline preflights."
                ),
                AppChangelogEntry(
                    id: "shared-browse-resume-refresh-helpers",
                    title: "Browse resume refresh logic cleaned up",
                    detail: "Jobs, Library, and Search now share helpers for resume notifications and resume availability checks."
                ),
                AppChangelogEntry(
                    id: "shared-browse-resume-status-formatter",
                    title: "Browse resume labels cleaned up",
                    detail: "Jobs, Library, and Search now share one formatter for resume badges and context-menu labels."
                ),
                AppChangelogEntry(
                    id: "shared-browse-list-collapse-interaction",
                    title: "Browse list gestures cleaned up",
                    detail: "Jobs and Library now share one SwiftUI modifier for the iPad split-view collapse gesture."
                ),
                AppChangelogEntry(
                    id: "job-playback-video-player-helper",
                    title: "Job video playback wiring cleaned up",
                    detail: "Job playback now builds its video player through one shared SwiftUI helper for preview, fullscreen, and tvOS paths."
                ),
                AppChangelogEntry(
                    id: "library-playback-video-player-helper",
                    title: "Library video playback wiring cleaned up",
                    detail: "Library playback now builds its video player through one shared SwiftUI helper for preview, fullscreen, and tvOS paths."
                ),
                AppChangelogEntry(
                    id: "language-flag-row-item-subview",
                    title: "Language flag row layout cleaned up",
                    detail: "Shared player language flag rows now render each flag item through a focused SwiftUI subview with a stable row structure."
                ),
                AppChangelogEntry(
                    id: "audio-mode-atomic-track-state",
                    title: "Audio toggles tightened up",
                    detail: "Original and translation audio toggles now switch through one normalized state path so playback never observes a no-track transition."
                ),
                AppChangelogEntry(
                    id: "jobs-offline-menu-handlers",
                    title: "Jobs offline menu cleaned up",
                    detail: "tvOS jobs offline menu actions now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "library-offline-menu-handlers",
                    title: "Library offline menu cleaned up",
                    detail: "tvOS library offline menu actions now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "interactive-header-language-flag-row-helper",
                    title: "Header language flag rows cleaned up",
                    detail: "Interactive player header language flag rows now share one SwiftUI helper and named role-toggle handler."
                ),
                AppChangelogEntry(
                    id: "language-flag-role-toggle-handler",
                    title: "Language flag toggles cleaned up",
                    detail: "Shared player language flag role toggles now route through a named SwiftUI handler."
                ),
                AppChangelogEntry(
                    id: "media-search-row-selection-handler",
                    title: "Media search row taps cleaned up",
                    detail: "Shared media search result rows now own their named SwiftUI selection handler."
                ),
                AppChangelogEntry(
                    id: "media-search-submit-handler",
                    title: "Media search submit cleaned up",
                    detail: "Shared media search submit events now route through a named SwiftUI handler."
                ),
                AppChangelogEntry(
                    id: "media-search-button-handlers",
                    title: "Media search controls cleaned up",
                    detail: "Shared media search clear and dismiss buttons now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "interactive-header-timeline-handlers",
                    title: "Header timeline controls cleaned up",
                    detail: "Interactive header timeline taps and tvOS header long-press toggles now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "phone-bubble-tap-handlers",
                    title: "iPhone bubble taps cleaned up",
                    detail: "iPhone transcript bubble backdrop and content taps now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "ipad-split-bubble-tap-handlers",
                    title: "iPad bubble taps cleaned up",
                    detail: "iPad split transcript bubble backdrop and content taps now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "interactive-player-bookmark-menu-row-helpers",
                    title: "Text-player bookmark menu cleaned up",
                    detail: "Interactive text-player bookmark menus now route add, jump, and remove rows through named SwiftUI helpers."
                ),
                AppChangelogEntry(
                    id: "interactive-player-tvos-directional-handlers",
                    title: "TV text-player navigation cleaned up",
                    detail: "Interactive text-player tvOS directional navigation now routes through named SwiftUI focus handlers."
                ),
                AppChangelogEntry(
                    id: "tvos-overlay-focus-handlers",
                    title: "TV overlay focus cleaned up",
                    detail: "tvOS overlay header, bubble, and timeline-pill focus events now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "tvos-playback-controls-focus-handlers",
                    title: "TV playback controls cleaned up",
                    detail: "tvOS playback button, scrubber, and controls-bar focus events now route through named SwiftUI handlers."
                ),
                AppChangelogEntry(
                    id: "bookmark-ribbon-menu-row-helpers",
                    title: "Bookmark ribbon menu cleaned up",
                    detail: "Bookmark ribbon menus now route add, jump, and remove rows through named SwiftUI helpers."
                ),
                AppChangelogEntry(
                    id: "video-bookmark-menu-row-helpers",
                    title: "Video bookmark menu cleaned up",
                    detail: "Video bookmark menus now route jump and remove rows through named SwiftUI helpers."
                ),
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
