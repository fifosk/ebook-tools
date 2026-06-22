extension AppChangelogData {
    static let june22Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "library-row-metadata-file",
            title: "Library row metadata separated",
            detail: "Library row titles, language flags, media variants, summaries, duration, sentence counts, and TV metadata now live in a focused extension while the base row stays centered on layout and styling."
        ),
        AppChangelogEntry(
            id: "interactive-transcript-selection-file",
            title: "Transcript selection separated",
            detail: "Selection hit-testing, drag range updates, tap tolerance, and delayed lookup scheduling now live in a focused extension while the core transcript view stays centered on layout composition."
        ),
        AppChangelogEntry(
            id: "interactive-header-behavior-file",
            title: "Header behavior separated",
            detail: "Interactive player header scaling, top-padding, pinch magnification, and collapse toggles now live in a focused behavior file while the header overlay stays centered on visible badge and progress-pill layout."
        ),
        AppChangelogEntry(
            id: "jobs-offline-menu-filter-files",
            title: "Jobs controls separated",
            detail: "Jobs filter styling and Apple TV offline download menu actions now live in focused files while the Jobs screen stays centered on list routing, search, and resume state."
        ),
        AppChangelogEntry(
            id: "library-browse-chrome-file",
            title: "Library browse chrome separated",
            detail: "Browse tabs, refresh styling, and sidebar swipe chrome now live in a focused file so Jobs, Library, Search, and Settings can share the same shell controls safely across iPad and tvOS."
        ),
        AppChangelogEntry(
            id: "interactive-header-pills-file",
            title: "Header pills separated",
            detail: "Speed and jump header-pill UI now lives in a focused extension while reading-bed code stays centered on music source and ambient playback behavior."
        ),
        AppChangelogEntry(
            id: "job-playback-video-file",
            title: "Job video playback split",
            detail: "Job playback video presentation, preview gestures, fullscreen routing, and player construction now live in a focused video extension while the base view stays centered on lifecycle and layout composition."
        ),
        AppChangelogEntry(
            id: "library-playback-focused-extensions",
            title: "Library playback split",
            detail: "Library playback loading, Now Playing integration, and resume routing now live in focused extensions while the base view stays centered on layout composition."
        ),
        AppChangelogEntry(
            id: "video-subtitle-loading-file",
            title: "Subtitle loading split",
            detail: "Subtitle track selection, fetch, streaming parse, and cache persistence now live in a focused loading extension while subtitle display and navigation stay in the subtitles view extension."
        ),
        AppChangelogEntry(
            id: "subtitle-overlay-highlighting-file",
            title: "Subtitle highlighting split",
            detail: "Subtitle playback highlight and shadow-selection logic now lives in a focused extension while the overlay view stays centered on rendering, gestures, and token rows."
        ),
        AppChangelogEntry(
            id: "job-row-presentation-file",
            title: "Jobs rows split cleanly",
            detail: "Jobs row title, metadata, progress, status, and cover URL presentation helpers now live in a focused extension while the row view stays centered on layout and platform styling."
        ),
        AppChangelogEntry(
            id: "interactive-transcript-autoscale-file",
            title: "Transcript auto-scale separated",
            detail: "Track auto-scale measurement, resize handlers, and delayed fit recalculation now live in a focused extension while the core transcript view stays centered on layout composition."
        ),
        AppChangelogEntry(
            id: "text-player-active-display-file",
            title: "Text player active display separated",
            detail: "Timeline active-display builders and active-index resolution now live in a focused extension while the base timeline builder stays centered on sentence runtime construction."
        ),
        AppChangelogEntry(
            id: "library-playback-video-file",
            title: "Library video playback separated",
            detail: "Library video preview, fullscreen presentation, tvOS video body, and video resume/progress helpers now live in a focused video extension while the main library playback view keeps load and content state."
        ),
        AppChangelogEntry(
            id: "video-overlay-tv-layout-file",
            title: "Apple TV video overlay separated",
            detail: "The tvOS video playback header, timeline pills, summary ticker, and bottom controls now live in a focused TV layout extension while the shared overlay stays centered on subtitle orchestration."
        ),
        AppChangelogEntry(
            id: "interactive-transcript-tv-layout-file",
            title: "Apple TV transcript layout separated",
            detail: "The tvOS transcript overlay taps, long-press header toggle, and horizontal split layout now live in a focused TV layout extension while the core transcript view stays less platform-specific."
        ),
        AppChangelogEntry(
            id: "changelog-day-data-file",
            title: "Daily changelog data separated",
            detail: "The growing June 22 changelog entry list now lives in a focused daily data file while the shared changelog data source stays as a compact day index."
        ),
        AppChangelogEntry(
            id: "runtime-descriptor-sections",
            title: "Backend runtime contract clarified",
            detail: "The public runtime descriptor now builds auth, client config, and Apple pipeline sections from named non-secret definitions, with regression coverage that simulator and device preflight lists are fresh per response."
        ),
        AppChangelogEntry(
            id: "interactive-shortcut-focus-file",
            title: "iPad shortcut focus separated",
            detail: "Hardware-keyboard first-responder reclaim, software-keyboard guards, focus updates, and window-touch reclaim now live in a focused extension while shortcut support keeps controller lifecycle and key-command mapping."
        ),
        AppChangelogEntry(
            id: "text-player-reveal-state-helper",
            title: "Text player reveal rules unified",
            detail: "Live timeline display, active sentence rendering, and track-switch settling now share one helper for token reveal counts, current-token selection, and segment-end reveal tolerance."
        ),
        AppChangelogEntry(
            id: "text-player-sentence-view-file",
            title: "Text player sentences separated",
            detail: "Sentence track filtering, hidden-track controls, selection mapping, and playback shadow mapping now live in a focused sentence view while text player views keep the frame shell and shared styling helpers."
        ),
        AppChangelogEntry(
            id: "text-player-variant-view-file",
            title: "Text player variants separated",
            detail: "Variant headers, token flow composition, platform font sizing, seek lookup, and token color state now live in a focused variant view while text player views stay centered on frame and sentence orchestration."
        ),
        AppChangelogEntry(
            id: "text-player-token-flow-layout-file",
            title: "Text player token flow separated",
            detail: "The reusable token wrapping layout now lives in a focused SwiftUI layout file while text player views stay centered on sentence and variant composition."
        ),
        AppChangelogEntry(
            id: "text-player-token-word-view-file",
            title: "Text player token chips separated",
            detail: "Token chip rendering, tap gestures, context menu, and dictionary lookup presentation now live in a focused token view while text player views stay centered on flow and variant composition."
        ),
        AppChangelogEntry(
            id: "text-player-token-geometry-file",
            title: "Text player token geometry separated",
            detail: "Token coordinate-space and preference-key plumbing now live in a focused geometry file while text player rendering stays centered on sentence, variant, and token views."
        ),
        AppChangelogEntry(
            id: "interactive-shortcut-dispatch-file",
            title: "iPad shortcut dispatch separated",
            detail: "Shortcut identity, duplicate suppression, and UIKit fallback scheduling now live in a focused dispatch extension while keyboard support stays centered on responder ownership and key-command wiring."
        ),
        AppChangelogEntry(
            id: "interactive-shortcut-hardware-fallback-file",
            title: "iPad keyboard fallback separated",
            detail: "The GameController hardware-keyboard fallback now lives in a focused extension while shortcut support stays centered on responder ownership and UIKit key commands."
        ),
        AppChangelogEntry(
            id: "interactive-player-menu-controls-file",
            title: "Player menu controls separated",
            detail: "Player menu pickers and selection handlers now live in a focused controls extension while the menu file stays centered on header imagery, the control bar shell, and TV text-size controls."
        ),
        AppChangelogEntry(
            id: "interactive-player-content-file",
            title: "Player transcript composition separated",
            detail: "Interactive transcript composition now lives in a focused extension while the player layout file stays centered on the screen shell and overlay layers."
        ),
        AppChangelogEntry(
            id: "interactive-player-lifecycle-observers-file",
            title: "Player lifecycle observers separated",
            detail: "Interactive player lifecycle observers and playback side-effect handlers now live in a focused extension while the layout file stays centered on screen composition."
        ),
        AppChangelogEntry(
            id: "interactive-shortcut-host-views-file",
            title: "iPad keyboard host views separated",
            detail: "Hardware-keyboard input host views and the touch observer now live in a focused UIKit bridge file while shortcut dispatch stays centered on command routing."
        ),
        AppChangelogEntry(
            id: "video-overlay-tv-focus-file",
            title: "TV playback focus separated",
            detail: "Apple TV playback focus and Siri Remote navigation handlers now live in a focused tvOS extension while the video overlay view stays centered on composition and chrome rendering."
        ),
        AppChangelogEntry(
            id: "subtitle-overlay-models-file",
            title: "Subtitle overlay models separated",
            detail: "Subtitle selection, token frame reporting, and display-building models now live in a focused playback models file while the subtitle overlay keeps layout, gestures, and token rendering."
        ),
        AppChangelogEntry(
            id: "library-playback-metadata-file",
            title: "Library playback metadata separated",
            detail: "Library playback metadata, cover, language, media selection, subtitle track, and video metadata derivation now live in a focused playback metadata extension while the main playback view keeps lifecycle, layout, and actions."
        ),
        AppChangelogEntry(
            id: "video-overlay-interaction-file",
            title: "Video overlay interactions separated",
            detail: "Subtitle drag selection, phone subtitle positioning, and shared video overlay labels now live in a focused playback interaction extension while the main video overlay keeps composition and TV focus orchestration."
        ),
        AppChangelogEntry(
            id: "media-search-controls-file",
            title: "Media search controls separated",
            detail: "Search state, actions, pill buttons, and input controls now live in a focused shared SwiftUI controls file while the search panel and overlay own presentation."
        ),
        AppChangelogEntry(
            id: "platform-controls-file",
            title: "Platform controls separated",
            detail: "Shared slider, picker, button, focus, gesture, and list-background helpers now live in a focused platform controls file while platform detection and metrics stay in the adapter."
        ),
        AppChangelogEntry(
            id: "settings-sections-file",
            title: "Settings sections separated",
            detail: "Connection, playback, changelog, voice, and notification settings now render from a focused SwiftUI sections file while the Settings screen owns state, lifecycle, and backend checks."
        ),
        AppChangelogEntry(
            id: "changelog-data-file",
            title: "Changelog data separated",
            detail: "Daily changelog entries now live in a focused data source while the shared changelog model stays small and stable for every Apple surface."
        ),
        AppChangelogEntry(
            id: "linguist-bubble-content-controls-file",
            title: "Linguist bubble content controls separated",
            detail: "Answer rendering plus shared close and font controls now live in a focused SwiftUI extension file while the main bubble view owns state, measurement, and gestures."
        ),
        AppChangelogEntry(
            id: "linguist-bubble-picker-models-file",
            title: "Linguist bubble picker data separated",
            detail: "Picker option models and iOS/tvOS picker-data builders now live in their own file so the picker UI file stays focused on overlay rendering."
        ),
        AppChangelogEntry(
            id: "linguist-bubble-platform-header-files",
            title: "Linguist bubble platform headers split",
            detail: "iOS and tvOS bubble header controls now live in platform-specific SwiftUI extension files while shared selector menus stay in the common controls file."
        ),
        AppChangelogEntry(
            id: "tvos-changelog-focus-pager",
            title: "TV changelog pages with the remote",
            detail: "The tvOS changelog now uses a focus-paged entry window so the Siri Remote can move through older daily entries without depending on nested scroll gesture handling."
        ),
        AppChangelogEntry(
            id: "linguist-bubble-header-controls-file",
            title: "Linguist bubble header controls separated",
            detail: "Header rows, selector menus, and platform-specific bubble controls now live in their own SwiftUI extension file while the main bubble view stays focused on state, lifecycle, and content."
        ),
        AppChangelogEntry(
            id: "linguist-bubble-label-utilities",
            title: "Linguist bubble label helpers separated",
            detail: "Model grouping plus model and voice label parsing now live in the shared text utilities file, keeping the main linguist bubble view focused on SwiftUI layout and controls."
        ),
        AppChangelogEntry(
            id: "tvos-changelog-real-scroll",
            title: "TV changelog remote scroll made visible",
            detail: "The tvOS changelog now uses compact rows in a real bounded scroll view with focus-following movement, a wider login card, and an up/down position affordance so older entries can be revealed with the Siri Remote."
        ),
        AppChangelogEntry(
            id: "backend-runtime-pipeline-identity",
            title: "Backend identity check strengthened",
            detail: "The public backend runtime descriptor now includes non-secret Apple pipeline metadata so the shared pipeline can verify it is talking to the ebook-tools app runtime."
        ),
        AppChangelogEntry(
            id: "tv-controls-shared-time-format",
            title: "TV playback time labels shared",
            detail: "The TV playback scrubber now uses the shared video time formatter instead of carrying a duplicate local formatter in the controls view."
        ),
        AppChangelogEntry(
            id: "tv-timeline-pill-control",
            title: "TV playback header controls cleaned up",
            detail: "The TV playback timeline pill now lives with the rest of the tvOS playback controls, keeping the overlay focused on layout and focus orchestration."
        ),
        AppChangelogEntry(
            id: "tvos-changelog-window-helper",
            title: "TV changelog focus math cleaned up",
            detail: "The tvOS changelog now uses one focused window helper for visible rows, position labels, and remote movement so full-day changelog growth stays predictable."
        ),
        AppChangelogEntry(
            id: "tvos-full-changelog-scroll",
            title: "TV changelog shows the full day",
            detail: "Login and Settings now use a bounded remote-scroll changelog with a position counter, so the Siri Remote can move through the full current-day entry list."
        ),
        AppChangelogEntry(
            id: "tvos-changelog-regression-auto-anchor",
            title: "TV changelog test hardened",
            detail: "The TV remote-scroll regression now follows the newest daily changelog row automatically and still proves older rows can be revealed after version bumps."
        ),
        AppChangelogEntry(
            id: "api-client-endpoint-extensions",
            title: "API client endpoints separated",
            detail: "Backend endpoint calls now live in focused service extension files for Auth, Library/Jobs, Linguist, Notifications, Pipeline Media, and Playback State while shared transport stays centralized."
        ),
        AppChangelogEntry(
            id: "pipeline-timing-sentence-api-models-files",
            title: "Pipeline timing models separated",
            detail: "Sentence metadata and job timing payloads now live in their own Models files so media file and chunk decoding stays focused."
        ),
        AppChangelogEntry(
            id: "tvos-changelog-focus-buttons",
            title: "TV changelog remote focus fixed",
            detail: "Login and Settings changelog rows now use capped tvOS focus targets so the Siri Remote can move down through entries beyond the first visible rows."
        ),
        AppChangelogEntry(
            id: "e2e-disable-session-restore",
            title: "Simulator login tests stabilized",
            detail: "Debug UI tests can now force the login screen without reusing stored sessions, keeping TV changelog checks repeatable."
        ),
        AppChangelogEntry(
            id: "library-job-api-models-file",
            title: "Library and job API models separated",
            detail: "Library browse responses and Pipeline job status/progress payloads now live in a dedicated Models file."
        ),
        AppChangelogEntry(
            id: "linguist-api-models-file",
            title: "Linguist API models separated",
            detail: "Assistant lookup, structured linguist parsing, model-list, voice inventory, and audio synthesis payloads now live in a dedicated Models file."
        ),
        AppChangelogEntry(
            id: "auth-api-models-file",
            title: "Auth API models separated",
            detail: "Login, session, OAuth, and backend runtime descriptor payloads now live in a dedicated Models file instead of the broad API model file."
        ),
        AppChangelogEntry(
            id: "pipeline-media-api-models-file",
            title: "Pipeline media API models separated",
            detail: "Media files, chunks, and audio-track payloads now live in a dedicated Models file instead of the broad API model file."
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
}
