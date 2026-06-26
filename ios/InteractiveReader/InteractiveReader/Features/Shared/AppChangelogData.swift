enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-26",
            dateLabel: "June 26, 2026",
            version: "2026.06.26.120",
            entries: [
                AppChangelogEntry(
                    id: "web-narrate-discovery-template-tab",
                    title: "Web discovery templates reopen clearly",
                    detail: "Web Narrate Ebook now switches back to the Discovery source tab when a saved discovery-backed template is applied, so the visible source mode matches the preserved provenance."
                ),
                AppChangelogEntry(
                    id: "web-narrate-template-discovery-resave",
                    title: "Web templates keep discovery context",
                    detail: "Web Narrate Ebook now preserves sanitized discovery source provenance when a saved discovery-backed template is applied and saved again."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-template-panel",
                    title: "Discovery templates reopen cleanly",
                    detail: "Apple Narrate EPUB templates now restore discovery-backed source choices on the Discovery panel while ordinary server and manual EPUB templates stay on Server."
                ),
                AppChangelogEntry(
                    id: "apple-dogfood-pipeline-gate",
                    title: "Dogfood pipeline gate is explicit",
                    detail: "The repo now has a non-physical dogfood pipeline command that runs the local Web and Apple cross-surface checkpoint before the shared Apple pipeline verification."
                ),
                AppChangelogEntry(
                    id: "tvos-reader-header-clearance",
                    title: "TV reader header gets full width",
                    detail: "Apple TV interactive reader headers now stretch the modern book banner across the top row and reserve more vertical clearance so the original sentence starts below the header."
                ),
                AppChangelogEntry(
                    id: "apple-cross-surface-checkpoint",
                    title: "Cross-surface checkpoint gate",
                    detail: "The repo now has a non-physical checkpoint command that builds Web production and export assets, then runs Apple local-surface verification before safe pushes or explicit attended device deploys."
                ),
                AppChangelogEntry(
                    id: "create-discovery-provider-readiness",
                    title: "Create discovery readiness is clearer",
                    detail: "Web and Apple Create now keep missing backend-advertised book and video discovery providers disabled with a clear message after provider inventory loads, while preserving fallback controls before the inventory arrives."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jump-render-target",
                    title: "Reader jumps render immediately",
                    detail: "Apple interactive reader slider, Jump To, search, chapter, and bookmark jumps now clear stale frozen transcript state and show the target sentence while audio seeks and starts playback."
                ),
                AppChangelogEntry(
                    id: "tvos-interactive-reader-header-width",
                    title: "TV reader header gets room",
                    detail: "Apple TV interactive reader headers now let the book banner stretch across the screen and reserve the measured header height so the original-language track does not render underneath it."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-target-resolver",
                    title: "Word taps use track-aware targets",
                    detail: "Apple interactive reader word taps now ask the sequence controller for the tapped track's sentence target before seeking, keeping track switches and fallback timing aligned."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-seek-stale-guard",
                    title: "Word taps rewind more reliably",
                    detail: "Apple interactive reader word taps now cancel older sequence audio transitions and drift-check same-track seeks, so tapping a word rewinds to that word without a stale track load moving playback back afterward."
                ),
                AppChangelogEntry(
                    id: "web-transcript-word-accessibility",
                    title: "Web transcript words expose playback state",
                    detail: "The Web interactive transcript now marks the active word with accessibility state and gives silent pause tokens a readable label, keeping word-sync controls clearer for assistive technologies."
                ),
                AppChangelogEntry(
                    id: "apple-pipeline-journey-list-target",
                    title: "Pipeline dry-runs are clearer",
                    detail: "The shared Apple pipeline now has an explicit app-owned journey list target, and orchestration dry-runs depend on that list plus true dry-runs so non-device preflights are easier to audit."
                ),
                AppChangelogEntry(
                    id: "apple-notification-toggle-unregisters",
                    title: "Notification toggles match the backend",
                    detail: "Apple settings now unregister the current device token when Job Notifications are turned off and skip sign-in re-registration while the toggle is disabled, so backend delivery follows the local preference."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-cross-file-rewind",
                    title: "Word taps rewind across language files",
                    detail: "Apple interactive reader word taps now reload the correct original or translation audio file when a previous combined-track seek rebuilt playback from the other file, so tapping back to a word can rewind and switch tracks reliably."
                ),
                AppChangelogEntry(
                    id: "apple-notification-signout-clears-session",
                    title: "Notifications forget signed-out sessions",
                    detail: "Apple clients now clear cached notification API state on sign-out, preventing a later push token callback from registering against a previous session."
                ),
                AppChangelogEntry(
                    id: "apple-notification-token-registration-order",
                    title: "Notifications register more reliably",
                    detail: "Apple clients now remember the authenticated API configuration before a push token arrives, so device registration works whether login or APNs registration finishes first."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-local-lane-seek",
                    title: "Word taps rewind to the intended lane",
                    detail: "Apple interactive reader word taps now normalize display sentence ids to the active chunk before seeking, and recompute tapped-lane timing when single-track playback switches between original and translation audio."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-sequence-track-seek",
                    title: "Word taps land on the tapped track",
                    detail: "Apple interactive reader word taps now compute sequence seeks from the tapped original or translation timing track directly, and combined single-track playback reloads the matching audio file before rewinding."
                ),
                AppChangelogEntry(
                    id: "apple-create-sentence-splitter-mode",
                    title: "Create can choose sentence splitting",
                    detail: "Web Narrate Ebook and Apple Create now expose the backend sentence splitter mode, preserve it in saved templates and recent-job defaults, and submit the same stable or modern pipeline override."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-audio-mode-sync",
                    title: "Word taps switch narration cleanly",
                    detail: "Apple interactive reader word taps outside sequence mode now sync the narration mode to the tapped language track before rewinding, so original, translation, and transliteration taps land on the matching audio."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-25",
            dateLabel: "June 25, 2026",
            version: "2026.06.25.109",
            entries: [
                AppChangelogEntry(
                    id: "apple-create-discovery-source-panel",
                    title: "Create discovery is easier to reach",
                    detail: "Apple Narrate EPUB now presents server EPUB selection and discovery as explicit source modes, Web Narrate Ebook mirrors that Source and Discovery split inside the source step, and interactive reader word taps in sequence playback switch language tracks when needed before rewinding to the tapped word."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-slider-draft-word-lookup",
                    title: "Reader slider and word taps stay live",
                    detail: "Apple interactive reader sentence sliders now clear stale draft positions when keyboard skips, jumps, bookmarks, chapters, search, or word taps move playback, and paused word taps rewind to the word, stay paused, and open lookup."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-slider-layout-sync",
                    title: "Reader slider stays in sync",
                    detail: "Apple interactive reader headers now reserve space for the sentence slider so the original track does not render underneath it, and the slider follows the active playback sentence instead of a stale manual selection."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-sentence-slider-word-taps",
                    title: "Reader jumps feel like media controls",
                    detail: "Apple interactive reader headers now include a sentence progress slider for fast jumps, word taps seek and play from the tapped word, double taps seek, pause, and open lookup, and sequence next/previous follows original-to-translation playback order."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jump-input-submit",
                    title: "Jump input and bookmarks land cleanly",
                    detail: "Apple interactive reader Jump To input now sanitizes numeric entry, clamps to available sentence bounds, offers keyboard Done and Go actions on iPad and iPhone, and bookmark jumps prefer stored chunk/time targets before falling back to sentence lookup."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-time-pill-tap",
                    title: "Header time pill and bookmarks respond",
                    detail: "Apple interactive reader headers now preserve the timeline tap action after moving progress and time pills inside the iPad book identity banner, and book bookmark adds update immediately during playback before backend reconciliation."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-progress-integrated",
                    title: "Reader header uses the full iPad row",
                    detail: "Apple interactive reader headers now carry the progress and time pills inside the book identity banner on iPad, let the header fill the available width, and open a book metadata overlay when the cover is tapped on iPad or iPhone."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-generic-hardening",
                    title: "Book-job headers avoid device crashes",
                    detail: "Apple interactive reader headers now avoid fit-based generic SwiftUI alternatives in the book-job overlay, reducing physical-device metadata instantiation pressure when opening older library jobs."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-device-crash-fix",
                    title: "Book loading is stable on iPad",
                    detail: "Apple interactive reader headers now choose their wide or compact identity-banner layout through explicit platform branching, avoiding a SwiftUI generic metadata crash seen on physical iPad when opening book jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-job-label",
                    title: "Book templates keep job labels",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now include trimmed title and job_label metadata, matching submitted Apple book jobs so Web handoff and template reuse show the same book title label."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-identity-banner-adaptive-layout",
                    title: "Reader header adapts more cleanly",
                    detail: "Apple interactive reader headers now give the identity banner a wide and compact layout, keeping the book cover, title, author, metadata pills, and inline controls composed across iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-cover-url",
                    title: "Book templates keep remote covers",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now preserve remote cover artwork as cover_url in Web-compatible book_metadata, while local/backend cover files stay in book_cover_file just like submitted Apple book jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-book-genres",
                    title: "Book templates keep genre lists",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now include normalized book_genres arrays in their Web-compatible book_metadata, matching submitted Apple book jobs and preserving genre metadata through Web handoff and template reuse."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-book-language",
                    title: "Book templates keep language metadata",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now include source-language metadata in their Web-compatible book_metadata, keeping Apple-to-Web draft handoff and later Apple template reuse aligned with submitted book jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-book-metadata-template-parity",
                    title: "Book templates carry metadata better",
                    detail: "Apple Create saved-template metadata loading now treats Web book_metadata JSON as a shared metadata source, keeping book-only Narrate Ebook templates useful across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-identity-component",
                    title: "Reader header is easier to verify",
                    detail: "Apple interactive reader headers now route the banner, book cover, title, metadata pills, and inline controls through a dedicated SwiftUI identity banner component with stable UI-test identifiers across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-chapter-end-placeholder",
                    title: "Chapter ranges are clearer",
                    detail: "Apple Narrate EPUB chapter controls now show a Same as start end-chapter placeholder, making loaded chapter ranges and manual-range fallback states easier to read across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-offline-export-row-busy-state",
                    title: "Offline exports stay row-focused",
                    detail: "Apple Jobs and Library now track offline export busy state per source row, preventing duplicate export taps for the active item without blocking export actions for other completed jobs or library entries."
                ),
                AppChangelogEntry(
                    id: "video-discovery-template-roundtrip",
                    title: "Video templates keep discovery context",
                    detail: "Web Video Dubbing and Apple YouTube Dub now restore token-free video discovery provenance when applying saved templates, so reviewed NAS, manual download, YouTube search, and indexer context survives apply/save loops."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-full-header-composition",
                    title: "Reader header feels unified",
                    detail: "Apple interactive playback now treats the full header as one media identity area: the banner carries the channel mark, book cover, title, author, item and model pills, plus controls, while progress pills adapt beside or below it without redundant outer chrome."
                ),
                AppChangelogEntry(
                    id: "video-discovery-template-provenance",
                    title: "Video discovery context survives templates",
                    detail: "Web Video Dubbing and Apple YouTube Dub templates now keep token-free discovery provenance for reviewed NAS, manual download, YouTube search, and indexer candidates, including provider, candidate id, selected paths, rights, and source kind without saving candidate tokens."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-banner-cover-pill-polish",
                    title: "Reader headers feel more native",
                    detail: "Apple interactive and video playback headers now present the banner, cover art, title, author, and info pills as one media identity area with stronger material styling, cover fallbacks, and fit-aware metadata rows across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-create-download-station-autoselect",
                    title: "Downloader results become selectable faster",
                    detail: "Apple YouTube Dub now matches completed Download Station filenames against the refreshed manual-download candidates and applies the matching video/subtitle source, reducing the handoff from indexer result to native job setup."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-identity-polish",
                    title: "Reader header identity is clearer",
                    detail: "Apple interactive playback now treats the banner, book cover, title, author, type, and model pills as one media identity block, with a fallback cover tile and fit-aware pills across iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "download-station-handoff-metadata-tolerance",
                    title: "Downloader handoff is more tolerant",
                    detail: "Web and Apple video discovery now recognize Download Station handoff metadata when the backend sends explicit providers, booleans, or legacy string flags, keeping reviewed indexer candidates visible across metadata encoding changes."
                ),
                AppChangelogEntry(
                    id: "apple-create-indexer-handoff-readiness",
                    title: "Create preflights indexer handoff",
                    detail: "Apple Create readiness now reports whether the backend registry can hand searchable Newznab/Torznab video candidates to Download Station, separating provider inventory health from the downloader handoff path used by Web and Apple discovery."
                ),
                AppChangelogEntry(
                    id: "apple-reader-identity-banner",
                    title: "Reader header feels more composed",
                    detail: "Apple interactive playback now groups the banner, book cover, title, author, item type, translation model, and controls into a modern media-style identity header with stable spacing across iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "acquisition-download-station-handoff-provider",
                    title: "Indexer handoff is clearer",
                    detail: "Web Video Dubbing and Apple YouTube Dub now use an explicit Download Station handoff marker from backend discovery candidates, keeping sensitive indexer URLs server-side while showing the reviewed handoff path in discovery results."
                ),
                AppChangelogEntry(
                    id: "apple-reader-header-lookup-speech-polish",
                    title: "Reader chrome feels more native",
                    detail: "Apple interactive playback now uses a translucent media-style header with unified control pills, and lookup read-aloud keeps the tapped track language and voice so target-language words are spoken correctly."
                ),
                AppChangelogEntry(
                    id: "apple-playback-diagnostics-compact-warning",
                    title: "Playback diagnostics are quieter",
                    detail: "Apple playback no longer shows the upper file, chunk, audio, timing, and image count strip; iPhone, iPad, Apple TV, and Mac Designed for iPad only show a compact warning when media gaps could affect playback."
                ),
                AppChangelogEntry(
                    id: "apple-browse-header-without-sync-strip",
                    title: "Browse headers are quieter",
                    detail: "Apple Library, Jobs, and combined search no longer show the redundant upper browse action row; section, search, and filter controls move to the top of the list, while resume sync and logout live in Settings."
                ),
                AppChangelogEntry(
                    id: "apple-video-sleep-timer",
                    title: "Video playback shares the sleep timer",
                    detail: "Apple video playback now uses the same sleep timer pill as interactive reading on iPhone, iPad, Apple TV, and Mac Designed for iPad; timer expiration pauses video playback, and TV remote focus moves through Search, Bookmarks, Sleep Timer, and timeline controls."
                ),
                AppChangelogEntry(
                    id: "apple-interactive-sleep-timer",
                    title: "Interactive playback adds a sleep timer",
                    detail: "Apple interactive playback now has a sleep timer pill with 5, 15, 30, and 45 minute presets on iPhone, iPad, Apple TV, and Mac Designed for iPad; when it expires, narration and the active reading bed pause together."
                ),
                AppChangelogEntry(
                    id: "apple-playback-diagnostics-warning-only",
                    title: "Playback chrome is quieter",
                    detail: "Apple playback now hides the media diagnostics file, chunk, timing, audio, and image count strip during healthy playback and only surfaces it when diagnostics report media gaps."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-cache-reset",
                    title: "Lock-screen timing resets cleanly",
                    detail: "Apple Now Playing now resets cached elapsed-time and duration state when playback metadata is cleared, so the next book or video republishes complete timing to lock-screen controls."
                ),
                AppChangelogEntry(
                    id: "apple-playback-pills-without-language-flags",
                    title: "Playback jump pills stay visible",
                    detail: "Apple interactive playback now keeps Jump, Search, and Bookmark controls visible across iPhone, iPad, Apple TV, and Mac Designed for iPad even when a book has no language flag metadata."
                ),
                AppChangelogEntry(
                    id: "apple-sentence-image-prefetch",
                    title: "Sentence images prefetch nearby",
                    detail: "Apple interactive playback now prefetches nearby sentence images around the active transcript position, so image-heavy book chunks feel smoother when revisited or advanced through quickly."
                ),
                AppChangelogEntry(
                    id: "apple-token-normalization-cache",
                    title: "Chunk revisits are lighter",
                    detail: "Apple interactive playback now reuses a bounded token normalization cache across live refreshes and chunk metadata rebuilds, making repeated chunk visits lighter without retaining stale sentence metadata."
                ),
                AppChangelogEntry(
                    id: "apple-bookmark-time-jump-ready-seek",
                    title: "Bookmark jumps wait for playback",
                    detail: "Apple interactive playback now defers time-based bookmark jumps until the target chunk audio is ready, so jumping from the bookmark pill preserves active playback on iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "apple-live-media-initial-fallback",
                    title: "Active job playback is more tolerant",
                    detail: "Apple Job playback still prefers live media for running jobs, but now falls back to the regular media snapshot if the first live-media request is temporarily unavailable."
                ),
                AppChangelogEntry(
                    id: "apple-audio-stream-recovery",
                    title: "Narration recovers from short stream failures",
                    detail: "Apple narration playback now retries one failed stream at the current file/time position and cleans up stall observers during player rebuilds, improving recovery from brief network interruptions."
                ),
                AppChangelogEntry(
                    id: "apple-timing-token-sanitization",
                    title: "Transcript timing is smoother",
                    detail: "Apple interactive playback now validates backend word timing windows before highlighting, dropping invalid timings and clamping overlaps inside each sentence/file group so reading stays fluid even with imperfect metadata."
                ),
                AppChangelogEntry(
                    id: "apple-transcript-metadata-retry",
                    title: "Transcript loading can be retried",
                    detail: "Apple interactive playback now records retryable chunk metadata failures and shows a transcript Retry action that reloads metadata and prepares audio again on iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "apple-playback-search-bookmark-focus",
                    title: "Playback search and bookmarks are easier to reach",
                    detail: "Apple playback now gives Search and Bookmark pills stable test identifiers and keeps the Apple TV video header focus path moving between Search, Bookmarks, and timeline controls while preserving jump-to-result and jump-to-bookmark behavior."
                ),
                AppChangelogEntry(
                    id: "apple-create-epub-picker-filter",
                    title: "Narrate EPUB choices stay book-focused",
                    detail: "Apple Narrate EPUB now filters server source choices to real EPUB paths and sorts them newest-first on device, matching the Web default picker while keeping manual-path fallback available."
                ),
                AppChangelogEntry(
                    id: "indexer-candidate-download-station-ui",
                    title: "Indexer handoff stays server-side",
                    detail: "Web Video Dubbing and Apple YouTube Dub can now send a selected Newznab/Torznab result to Download Station through the server-side candidate token, keeping API-key URLs hidden while the user confirms the task."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-audio-session-retry",
                    title: "TV lookup Read Aloud is reachable",
                    detail: "Apple TV lookup bubbles now cycle remote focus across visible controls so Read Aloud can be selected, then retry pronunciation audio-session setup with simpler playback options if tvOS rejects the richer spoken-audio session."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-output-follows-source",
                    title: "Narrate EPUB names follow the selected book",
                    detail: "Apple Narrate EPUB now refreshes the output/job name when the selected EPUB changes unless that output field was manually edited, preventing new jobs from inheriting another book's name."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-empty-audio-fallback",
                    title: "TV lookup avoids empty pronunciation audio",
                    detail: "Apple TV lookup read-aloud now rejects decoded-but-empty backend pronunciation audio and immediately falls back to platform speech, so the Read Aloud control does not go silent."
                ),
                AppChangelogEntry(
                    id: "lookup-pronunciation-audio-decode-fallback",
                    title: "Lookup audio falls back instead of going silent",
                    detail: "Apple lookup read-aloud now falls back to platform speech when backend pronunciation audio cannot start, so Apple TV, iPhone, iPad, and voice previews do not fail silently."
                ),
                AppChangelogEntry(
                    id: "lookup-read-aloud-audio-handoff",
                    title: "Lookup read-aloud gets a clear audio lane",
                    detail: "Apple TV and iPhone/iPad lookup read-aloud now pauses active playback before speaking, and cached narration playback stops pronunciation audio before resuming the book or video track."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-read-aloud-retry",
                    title: "TV lookup can speak again",
                    detail: "Apple TV lookup bubbles now include an explicit Read Aloud control that replays the current lookup through backend pronunciation with platform speech fallback, matching the selected source or translation track."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-pronunciation-language-fallback",
                    title: "TV read-aloud avoids silent language misses",
                    detail: "Apple TV lookup read-aloud now keeps a platform speech fallback even when the selected lookup language is a backend label that cannot be mapped to a specific AVSpeech voice code."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-pronunciation-timeout",
                    title: "TV lookup read-aloud is more reliable",
                    detail: "Apple TV lookup pronunciation now falls back to platform speech after a short backend timeout and keeps speech playback on the main actor, so slow backend TTS no longer leaves lookup audio silent."
                ),
                AppChangelogEntry(
                    id: "lookup-cache-permission-fallbacks",
                    title: "Lookup cache permissions are clearer",
                    detail: "Lookup-cache endpoints now preserve authorization failures while missing caches still fall back gracefully to live MyLinguist lookup in Web and Apple playback."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-settings-selected-source",
                    title: "Chapter loading shows the selected book",
                    detail: "Narrate EPUB now resolves the selected server EPUB through one shared helper, so the right-side Job Settings chapter controls show the same selected-book detail as the source picker."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-picker-context",
                    title: "EPUB choices are easier to trust",
                    detail: "Apple Narrate EPUB keeps the server picker usable for manual-path fallback, adds folder context to nested NAS EPUB choices, and shows which selected server book Load Chapters will query."
                ),
                AppChangelogEntry(
                    id: "post-export-timing-validation",
                    title: "Timing validation is recorded",
                    detail: "Generated chunk metadata now records post-export timing validation for original and translation tracks, making overlap and duration drift visible to Web and Apple playback diagnostics."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-button-provider-readiness",
                    title: "TV lookup and Create gates are steadier",
                    detail: "Apple TV lookup read-aloud controls now activate through native focusable buttons, and Apple Create readiness validates the backend acquisition provider registry before simulator journeys."
                ),
                AppChangelogEntry(
                    id: "video-discovery-provider-registry",
                    title: "Video discovery follows backend providers",
                    detail: "Web Video Dubbing and Apple YouTube Dub discovery now derive video-capable provider choices from the backend registry while preserving NAS, manual downloads, YouTube search, and Indexers ordering."
                ),
                AppChangelogEntry(
                    id: "apple-create-readiness-discovery-provider-policy",
                    title: "Create readiness checks discovery policy",
                    detail: "Apple Create readiness now opens Narrate EPUB discovery, selects the attended Z-Library provider from the backend-driven source picker, and asserts the disabled-policy message before continuing through language and media-job defaults."
                ),
                AppChangelogEntry(
                    id: "registry-driven-ebook-discovery-tv-read-aloud",
                    title: "Discovery and TV read-aloud are steadier",
                    detail: "Web and Apple ebook discovery now derive book-capable source choices from the backend registry while preserving familiar ordering and policy messages, and Apple TV lookup read-aloud configures the tvOS playback audio session before pronunciation."
                ),
                AppChangelogEntry(
                    id: "ebook-discovery-zlibrary-attended-import",
                    title: "Ebook discovery explains attended imports",
                    detail: "Web and Apple ebook discovery now show Z-Library as an attended-import-only path with direct automation disabled, guiding authorized EPUBs through Manual downloads or the backend books folder."
                ),
                AppChangelogEntry(
                    id: "apple-create-server-epub-picker-chapter-skip",
                    title: "Narrate EPUB source loading is clearer",
                    detail: "Apple Create keeps the server EPUB picker visible with a loaded-source summary and skips generated/runtime chapter lookups that cannot resolve through the backend EPUB folder."
                ),
                AppChangelogEntry(
                    id: "create-source-metadata-reset-tv-lookup-playback",
                    title: "Create metadata and TV lookup are steadier",
                    detail: "Narrate EPUB now clears stale source metadata when the selected book changes, chapter loading states are clearer, and Apple TV video lookup can play from cached narration timing again."
                ),
                AppChangelogEntry(
                    id: "create-discovery-prepare-handoff",
                    title: "Discovery sources use prepared handoff",
                    detail: "Web Narrate Ebook and Apple Narrate EPUB now ask the backend to prepare selected discovery artifacts before filling source paths, keeping local and acquired EPUB handoffs consistent."
                ),
                AppChangelogEntry(
                    id: "acquisition-artifact-prepare",
                    title: "Discovery sources prepare cleanly",
                    detail: "Reviewed discovery artifacts now resolve through a shared prepare endpoint, giving Web and Apple Create the same source fields for local EPUBs, acquired public EPUBs, and local video candidates."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-lowercase-dialogue",
                    title: "Sentence splits read more naturally",
                    detail: "Sentence splitting now recognizes lowercase starts and quoted dialogue after terminal punctuation while keeping ellipsis continuations and inline dialogue tags together; refined sentence caches invalidate with splitter version regex-v5."
                ),
                AppChangelogEntry(
                    id: "apple-openlibrary-provenance-payload",
                    title: "Catalog provenance stays with jobs",
                    detail: "Apple generated-book and Narrate EPUB submissions now preserve applied Open Library work IDs, edition IDs, lookup hints, and cover URLs in job metadata while keeping visible form edits authoritative."
                ),
                AppChangelogEntry(
                    id: "openlibrary-apply-metadata",
                    title: "Discovery applies book metadata",
                    detail: "Open Library discovery candidates can now fill Web Narrate Ebook metadata JSON and Apple Narrate EPUB metadata fields without choosing or acquiring an EPUB source."
                ),
                AppChangelogEntry(
                    id: "openlibrary-metadata-discovery",
                    title: "Open Library metadata joins Create",
                    detail: "Web Narrate Ebook and Apple Narrate EPUB can now search Open Library as a metadata-only source, showing reviewable catalog matches without attempting EPUB acquisition."
                ),
                AppChangelogEntry(
                    id: "internet-archive-acquire-contract",
                    title: "Public acquire contract is traced",
                    detail: "The shared acquisition route and Apple DTO checks now cover Internet Archive artifact responses, preserving source metadata such as the archive identifier after reviewed EPUB acquisition."
                ),
                AppChangelogEntry(
                    id: "ebook-discovery-provider-controls",
                    title: "Discovery providers scale better",
                    detail: "Web Narrate Ebook now renders ebook discovery sources from one provider descriptor list, and Apple Narrate EPUB uses a menu picker so Local, Manual, Gutenberg, and Internet Archive options stay readable."
                ),
                AppChangelogEntry(
                    id: "internet-archive-ebook-discovery",
                    title: "Public EPUB discovery expands",
                    detail: "Backend, Web Narrate Ebook, and Apple Narrate EPUB now search Internet Archive text items for ordinary downloadable EPUB files and acquire reviewed candidates into the shared server EPUB root."
                ),
                AppChangelogEntry(
                    id: "web-apple-indexer-discovery",
                    title: "Create surfaces search indexers",
                    detail: "Web Video Dubbing and Apple YouTube Dub can now search configured Newznab/Torznab indexer metadata as review-only candidates without filling playable source paths or exposing raw download URLs."
                ),
                AppChangelogEntry(
                    id: "newznab-torznab-review-discovery",
                    title: "Indexer discovery is safer",
                    detail: "The backend can now search configured Newznab/Torznab video indexers as review-only metadata, keeping API keys and raw download URLs server-side."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-dub-download-station-handoff",
                    title: "Apple Create queues Download Station",
                    detail: "Apple YouTube Dub can now submit authorized Download Station links or magnets, poll the shared acquisition job, and refresh manual-download/NAS sources when the task completes."
                ),
                AppChangelogEntry(
                    id: "web-video-download-station-handoff",
                    title: "Web Video queues Download Station",
                    detail: "Web Video Dubbing can now submit authorized Download Station source links or magnets, poll the shared task endpoint, and continue final file selection through manual-download discovery."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-smart-quotes-cache",
                    title: "Reading splits are steadier",
                    detail: "Sentence splitting now handles smart closing quotes and initials more fluidly, and content-index caches include splitter identity plus refined sentence hashes to avoid stale chapter ranges."
                ),
                AppChangelogEntry(
                    id: "download-station-acquisition-jobs",
                    title: "Download Station handoff starts",
                    detail: "The shared acquisition backend now exposes reviewed Download Station job submit and poll endpoints, keeping NAS credentials server-side while Apple and Web clients get a common task-status contract."
                ),
                AppChangelogEntry(
                    id: "apple-video-manual-download-discovery",
                    title: "Downloaded videos are easier to pick",
                    detail: "Apple YouTube Dub discovery can now search configured manual download folders for user-authorized NAS or Download Station video files and reuse discovered subtitle hints."
                ),
                AppChangelogEntry(
                    id: "apple-ebook-discovery-provider-readiness",
                    title: "Ebook source readiness is clearer",
                    detail: "Apple Narrate EPUB discovery now uses the shared acquisition provider registry to disable unavailable ebook source searches and explain missing backend source roots before showing an empty result list."
                ),
                AppChangelogEntry(
                    id: "apple-translation-timing-local-fallback",
                    title: "Translation highlights stay aligned",
                    detail: "Apple interactive playback now falls back to chunk-local translation timing tracks when job-level timing is unavailable, matching original-track highlighting for multi-sentence chunks."
                ),
                AppChangelogEntry(
                    id: "manual-download-discovery",
                    title: "Manual downloads are discoverable",
                    detail: "Apple and Web Narrate Ebook discovery can now search configured manual download folders for user-authorized EPUBs downloaded through Safari, Download Station, or another attended workflow."
                ),
                AppChangelogEntry(
                    id: "youtube-search-provider-errors",
                    title: "YouTube search errors are clearer",
                    detail: "YouTube acquisition discovery now returns token-safe quota, rate-limit, and authorization messages for configured providers instead of collapsing API failures into a generic provider error."
                ),
                AppChangelogEntry(
                    id: "youtube-search-provider-readiness",
                    title: "YouTube search readiness is visible",
                    detail: "Web and Apple YouTube search surfaces now read the token-safe acquisition provider registry, disable YouTube search when the backend is not configured, and keep direct URL or NAS paths usable."
                ),
                AppChangelogEntry(
                    id: "web-youtube-download-search-handoff",
                    title: "Web YouTube downloads search first",
                    detail: "Web YouTube downloads can now search configured YouTube metadata results from the backend, select a result into the existing URL field, and continue through subtitle inspection, subtitle selection, and video download review."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-search-discovery-handoff",
                    title: "Apple Create reviews YouTube search",
                    detail: "Apple YouTube Dub discovery can now switch between NAS videos and configured YouTube search metadata, routing selected YouTube results into the existing metadata review flow before any download or dubbing step."
                ),
                AppChangelogEntry(
                    id: "web-youtube-search-discovery-handoff",
                    title: "Web Video search reviews YouTube results",
                    detail: "Web Video Dubbing discovery can now switch between NAS videos and configured YouTube search metadata, routing selected YouTube results into the existing metadata review flow before any download or dubbing step."
                ),
                AppChangelogEntry(
                    id: "apple-gutenberg-discovery-handoff",
                    title: "Apple Create acquires public EPUBs",
                    detail: "Apple Narrate EPUB discovery can now switch between local EPUBs and Gutenberg catalog results, acquiring reviewed Gutenberg EPUBs before filling the standard server EPUB path."
                ),
                AppChangelogEntry(
                    id: "web-gutenberg-discovery-handoff",
                    title: "Web Create acquires public EPUBs",
                    detail: "Web Narrate Ebook discovery can now switch between local EPUBs and Gutenberg catalog results, acquiring reviewed Gutenberg EPUBs before filling the standard input path."
                ),
                AppChangelogEntry(
                    id: "gutenberg-reviewed-acquisition",
                    title: "Public EPUB acquisition added",
                    detail: "Reviewed Gutenberg candidates can now be acquired into the backend books root through the shared acquisition endpoint, with Web and Apple clients aware of the new handoff path."
                ),
                AppChangelogEntry(
                    id: "gutenberg-acquisition-discovery",
                    title: "Public ebook discovery added",
                    detail: "The backend now exposes Project Gutenberg/Gutendex as an explicit discovery provider, returning public catalog ebook metadata and EPUB links for reviewed acquisition."
                ),
                AppChangelogEntry(
                    id: "acquisition-discovery-contract-hardening",
                    title: "Discovery contract tightened",
                    detail: "Acquisition discovery now caps backend result limits, skips provider scans for zero-limit internal calls, and rejects providers that are not yet real discovery sources."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-state-split",
                    title: "Discovery state stays scoped",
                    detail: "Apple Create now keeps EPUB and YouTube Dub discovery responses and errors separate, so switching modes cannot show stale book or video candidates."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-dub-video-discovery",
                    title: "Apple Create discovers videos",
                    detail: "Apple YouTube Dub now offers Discover Video Sources from the shared acquisition endpoint, filling existing NAS video and subtitle fields from backend-visible candidates."
                ),
                AppChangelogEntry(
                    id: "web-video-discovery-picker",
                    title: "Web Video Dubbing discovers NAS videos",
                    detail: "Web Video Dubbing now offers a Discover video sources panel backed by the shared acquisition endpoint, filling the existing video and subtitle selection from backend-visible NAS candidates."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-discovery-picker",
                    title: "Apple Create discovers EPUBs",
                    detail: "Apple Narrate EPUB now offers a Discover Sources control backed by the shared acquisition discovery endpoint, filling the existing server EPUB path from backend-visible local candidates."
                ),
                AppChangelogEntry(
                    id: "web-narrate-ebook-discovery-picker",
                    title: "Web Create discovers EPUBs",
                    detail: "Web Narrate Ebook now offers a Discovery sources dialog backed by the shared acquisition contract, filling the existing input path from local EPUB candidates without changing the job payload."
                ),
                AppChangelogEntry(
                    id: "acquisition-discovery-and-splitter-quotes",
                    title: "Discovery search starts",
                    detail: "The backend now exposes editor/admin source discovery for local EPUBs, NAS videos with subtitle hints, and configured YouTube metadata search, while sentence splitting preserves closing quotes after punctuation."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-contract",
                    title: "Discovery providers listed",
                    detail: "The backend now exposes a token-safe acquisition provider contract for local EPUBs, NAS videos, YouTube URL and search workflows, reviewed downloader handoff, and planned public or open ebook sources."
                ),
                AppChangelogEntry(
                    id: "sequence-playback-per-sentence-fallback",
                    title: "Sequence playback keeps sentences",
                    detail: "Web and Apple sequence playback now fills missing per-sentence gates from that sentence's phase durations, so mixed chunks keep every original and translation sentence in the plan."
                ),
                AppChangelogEntry(
                    id: "discovery-acquisition-plan",
                    title: "Discovery layer planned",
                    detail: "The shared pipeline now has a lawful discovery acquisition plan for YouTube search, NAS and Download Station handoff, public or open ebook catalogs, metadata enrichment, and Web/Apple Create source handoff."
                ),
                AppChangelogEntry(
                    id: "apple-original-timing-local-index",
                    title: "Original highlights align",
                    detail: "Apple interactive playback now reads chunk-local original timing tokens before legacy global fallback so iPad, iPhone, and Apple TV preserve per-word original highlights from chunk metadata."
                ),
                AppChangelogEntry(
                    id: "pipeline-llm-model-threadpool",
                    title: "Model picker stays responsive",
                    detail: "The shared pipeline LLM model inventory route now runs provider discovery on FastAPI's threadpool so Web and Apple Create model pickers do not block the async server."
                ),
                AppChangelogEntry(
                    id: "creation-template-delete-canonical-id",
                    title: "Draft cleanup ids align",
                    detail: "Saved creation-template deletes now return the canonical template id and skip storage reads for empty normalized ids, keeping Web and Apple draft cleanup predictable."
                ),
                AppChangelogEntry(
                    id: "release-contract-date-lock",
                    title: "Changelog date locked",
                    detail: "The release contract now requires the latest Markdown changelog day, Apple in-app changelog day, visible date label, and shipped release version to agree on today's build date."
                ),
                AppChangelogEntry(
                    id: "youtube-library-picker-token-reuse",
                    title: "Video picker loads lighter",
                    detail: "The shared YouTube NAS library picker now prefilters unrelated stored jobs by filename before path normalization and reuses discovered video tokens while building Web and Apple Create source rows."
                ),
                AppChangelogEntry(
                    id: "apple-create-shared-chapter-range-control",
                    title: "Create shares chapter controls",
                    detail: "Apple Create now uses one Narrate EPUB chapter-range control in both the source pane and wide job-settings pane, keeping Load Chapters, pickers, summaries, and sentence-window updates consistent."
                ),
                AppChangelogEntry(
                    id: "web-create-chapter-loading-pipeline-coverage",
                    title: "Create chapter gate expanded",
                    detail: "The shared Web pipeline now directly covers Narrate Ebook content-index chapter loading, generated-source skips, consecutive chapter selection, backend error surfacing, and estimated range and duration labels."
                ),
                AppChangelogEntry(
                    id: "apple-changelog-latest-version-contract",
                    title: "Changelog version stays current",
                    detail: "The Daily Changelog header now follows the latest changelog day, and the release contract requires that Swift day to match the shipped app release so today's version cannot silently drift."
                ),
                AppChangelogEntry(
                    id: "web-create-voice-inventory-pipeline-coverage",
                    title: "Create voice gate expanded",
                    detail: "The shared Web pipeline now directly covers Narrate Ebook backend voice inventory matching, region/base language-code normalization, per-language preview overrides, and inventory load failures."
                ),
                AppChangelogEntry(
                    id: "web-create-file-discovery-pipeline-coverage",
                    title: "Create source gate expanded",
                    detail: "The shared Web pipeline now directly covers Narrate Ebook server EPUB discovery, newest backend book defaults, generated-source skips, upload validation, and history-derived start defaults."
                ),
                AppChangelogEntry(
                    id: "web-job-settings-pipeline-coverage",
                    title: "Job settings gate expanded",
                    detail: "The shared Web pipeline now keeps book and subtitle job settings summaries covered alongside JobProgress rendering, stage health, and generated-file utilities."
                ),
                AppChangelogEntry(
                    id: "web-library-pipeline-coverage",
                    title: "Library pipeline gate expanded",
                    detail: "The shared Web pipeline now runs focused Library metadata, LibraryList helper, media cell, action, status badge, and resume badge coverage before the broader Vitest and build checks."
                ),
                AppChangelogEntry(
                    id: "apple-create-epub-picker-scoped-list",
                    title: "Create keeps EPUB choices",
                    detail: "Apple Create now trusts the backend-scoped EPUB list even when filename metadata omits the .epub suffix, so iPad, iPhone, and Apple TV server book pickers keep valid available books visible."
                ),
                AppChangelogEntry(
                    id: "apple-create-nas-epub-picker",
                    title: "Create finds NAS EPUBs",
                    detail: "Apple Create and Web source pickers now follow visible symlinked NAS folders and Apple chapter loading accepts zero-based backend chapter indexes, restoring server EPUB choices and Load Chapters for more book collections."
                ),
                AppChangelogEntry(
                    id: "apple-create-image-node-check",
                    title: "Create checks image nodes",
                    detail: "Apple Create generated-book image settings can now check configured image API nodes and show aggregate availability before submitting illustrated jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-infers-chapter-ends",
                    title: "Create loads chapter ranges",
                    detail: "Apple Create now infers missing chapter end sentences from the next chapter or total sentence count when loading a server EPUB index, preventing chapter selections from collapsing to a one-sentence range."
                ),
                AppChangelogEntry(
                    id: "apple-create-decodes-server-options",
                    title: "Create loads server options",
                    detail: "Apple Create now decodes backend Create option, EPUB picker, and chapter-index responses through the same snake-case strategy as the API client, restoring full language/default lists and backend-visible server books on iPad and iPhone."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-24",
            dateLabel: "June 24, 2026",
            version: "2026.06.24.27",
            entries: [
                AppChangelogEntry(
                    id: "apple-create-save-native-templates",
                    title: "Create saves templates",
                    detail: "Apple Create can now save current generated-book, Narrate EPUB, subtitle, and YouTube dubbing settings as reusable Web-compatible creation templates, then hand the selected template to Web Create."
                ),
                AppChangelogEntry(
                    id: "apple-web-template-handoff",
                    title: "Web handoff carries templates",
                    detail: "Apple Create now includes the selected saved creation template when opening Web Create, so iPad and iPhone can continue book, subtitle, and YouTube dubbing drafts in the advanced Web forms."
                ),
                AppChangelogEntry(
                    id: "apple-create-delete-saved-templates",
                    title: "Create manages templates",
                    detail: "Apple Create can now delete the selected saved creation template after confirmation, keeping Web-authored book, subtitle, and YouTube dubbing presets tidy from iPad, iPhone, and Apple TV."
                ),
                AppChangelogEntry(
                    id: "apple-create-nas-ebook-metadata",
                    title: "Create labels NAS books",
                    detail: "Apple Create now shows backend-visible EPUB size and modified date in the server book picker, making the latest NAS source easier to verify before starting Narrate EPUB jobs."
                ),
                AppChangelogEntry(
                    id: "apple-tvos-create-tuning-controls",
                    title: "TV Create gets tuning",
                    detail: "Apple TV Create now exposes subtitle typography, subtitle batch tuning, and YouTube dubbing mix, flush, and batch controls through remote-friendly value steppers."
                ),
                AppChangelogEntry(
                    id: "web-media-provider-defaults",
                    title: "Web media defaults align",
                    detail: "Web Subtitle Tool and Video Dubbing now use the same backend translation provider and transliteration defaults that Apple Create reads from /api/books/options."
                ),
                AppChangelogEntry(
                    id: "apple-create-media-default-readiness",
                    title: "Create checks media defaults",
                    detail: "Apple Create readiness now verifies that the backend advertises shared subtitle and YouTube dubbing processing defaults before simulator journeys run."
                ),
                AppChangelogEntry(
                    id: "apple-create-ass-server-sources",
                    title: "Create lists ASS subtitles",
                    detail: "Apple Create now keeps backend-visible ASS subtitle files selectable for subtitle jobs while still preferring SRT and VTT as default server sources when they are available."
                ),
                AppChangelogEntry(
                    id: "apple-create-right-pane-job-type",
                    title: "Create moves job type right",
                    detail: "On iPad and local Mac Designed for iPad, Apple Create now keeps the job type picker with the right-hand job settings pane so the left setup pane can stay focused on source and metadata."
                ),
                AppChangelogEntry(
                    id: "apple-create-advanced-metadata-json",
                    title: "Create edits full metadata",
                    detail: "Apple Create now gives subtitle and YouTube jobs an advanced metadata JSON editor, so iPad and iPhone can review and apply full nested metadata payloads in addition to the high-value native fields."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-source-labels",
                    title: "Generated books clarify sources",
                    detail: "Apple Create generated-book fields now label continuation context as source-book title, author, genre, and summary so it is clear what belongs to the existing book versus the new generated book."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-source-context",
                    title: "Generated books get source context",
                    detail: "Apple Create generated-book jobs now accept source-book title, author, genre, and summary context so iPad and iPhone can start continuation-style books with explicit source metadata."
                ),
                AppChangelogEntry(
                    id: "apple-device-update-preflight",
                    title: "Device updates preflight first",
                    detail: "The guarded Apple physical-device update helper now runs a non-mutating CoreDevice health preflight before confirmed installs, while keeping installed-app metadata verification as a separate post-install check."
                ),
                AppChangelogEntry(
                    id: "apple-offline-export-progress",
                    title: "Exports show progress",
                    detail: "Apple Jobs and Library now show a visible offline-export progress overlay while the backend prepares an offline player archive."
                ),
                AppChangelogEntry(
                    id: "apple-job-health-row",
                    title: "Jobs show running health",
                    detail: "Apple Jobs rows now show a compact running-job health line with the latest backend stage, elapsed runtime, and ETA from progress events."
                ),
                AppChangelogEntry(
                    id: "apple-create-opens-created-job",
                    title: "Create opens new jobs",
                    detail: "Apple Create now routes successful submissions directly to the created job in Jobs, selects the matching Jobs category, and starts Jobs auto-refresh so newly submitted book, subtitle, and video jobs are immediately visible."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-history-settings",
                    title: "Narrate EPUB remembers settings",
                    detail: "Apple Create Narrate EPUB now reuses prior narration job audio, output, translation, transliteration, lookup-cache, and chunking settings while still preserving fields edited in the current form."
                ),
                AppChangelogEntry(
                    id: "apple-shared-pipeline-make-wrappers",
                    title: "Shared pipeline gets local commands",
                    detail: "The repo now exposes Make wrappers for the shared Apple device app pipeline contract, backend, source-sync, and non-physical shared preflight commands so ebook-tools can dogfood the reusable pipeline from its own checkout."
                ),
                AppChangelogEntry(
                    id: "apple-local-surface-verification-gate",
                    title: "Local Apple checks get one command",
                    detail: "The repo now has a single non-physical verification gate that runs Apple contracts and then compiles all local Apple surfaces before any attended physical-device update."
                ),
                AppChangelogEntry(
                    id: "apple-local-surface-build-gate",
                    title: "Local Apple builds get one gate",
                    detail: "The repo now has a single non-physical build gate that chains iPhone simulator, iPad simulator, Apple TV simulator, and local Mac Designed for iPad/iPhone compile checks before attended device deploys."
                ),
                AppChangelogEntry(
                    id: "apple-ios-simulator-build-lanes",
                    title: "Phone and iPad builds get gates",
                    detail: "The repo now has quick iPhone and iPad simulator compile lanes, plus a combined iOS simulator target, so pipeline dogfood can verify handheld and tablet builds without launching full journeys or touching physical devices."
                ),
                AppChangelogEntry(
                    id: "apple-tvos-simulator-build-lane",
                    title: "TV builds get a gate",
                    detail: "The repo now has a quick tvOS simulator compile lane for the Apple TV app, so pipeline dogfood can catch tvOS-only Swift regressions before a full journey run or physical-device deploy."
                ),
                AppChangelogEntry(
                    id: "apple-library-source-diagnostics",
                    title: "Library shows sources",
                    detail: "Apple Library rows now expose read-only Source Details on iPhone, iPad, and Apple TV with stored-source, file, type, path, status, and media diagnostics."
                ),
                AppChangelogEntry(
                    id: "apple-library-source-upload-review",
                    title: "Library reviews sources",
                    detail: "Apple Library source replacement now opens a review sheet before upload and accepts the same common book and video source extensions as Web."
                ),
                AppChangelogEntry(
                    id: "apple-create-ipad-job-settings-pane",
                    title: "Create shifts job settings",
                    detail: "iPad and local Mac Designed for iPad Create now keep generated-book sentence count plus Narrate EPUB output and sentence-range settings in the right-hand job settings pane instead of the left setup pane."
                ),
                AppChangelogEntry(
                    id: "apple-library-metadata-editor",
                    title: "Library edits metadata",
                    detail: "Apple Library rows on iPhone and iPad now expose an Edit Metadata sheet for title, author, genre, language, and ISBN, using the same backend PATCH contract as Web."
                ),
                AppChangelogEntry(
                    id: "apple-library-metadata-enrichment",
                    title: "Library enriches metadata",
                    detail: "Apple Library rows can now call the shared backend external metadata enrichment endpoint and refresh the row with the returned title, cover, genre, ISBN, and source details."
                ),
                AppChangelogEntry(
                    id: "apple-library-job-offline-export",
                    title: "Apple exports players",
                    detail: "Jobs and Library rows on Apple surfaces can now request the shared backend offline-player export zip and open the returned download URL, matching the Web export action for completed media."
                ),
                AppChangelogEntry(
                    id: "apple-create-ipad-wide-settings-pane",
                    title: "Create widens settings",
                    detail: "On iPad and local Mac Designed for iPad, Apple Create now keeps the navigation rail compact and reserves the wide right-hand detail area for language, narration, output, status, and submit settings."
                ),
                AppChangelogEntry(
                    id: "apple-create-tv-metadata-artwork",
                    title: "Create previews TV artwork",
                    detail: "Apple Create subtitle and YouTube TV metadata now show and edit TVMaze poster and episode-still artwork URLs, expose the YouTube thumbnail URL, and include TMDB and IMDb ID fields before submission."
                ),
                AppChangelogEntry(
                    id: "apple-create-metadata-cache-clear",
                    title: "Create clears metadata caches",
                    detail: "Apple Create now gives iPad job settings more of the right-hand detail area and adds subtitle, TV, and YouTube metadata cache clearing controls that use the shared backend runtime contract."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-metadata-lookup-name",
                    title: "Create edits metadata lookup",
                    detail: "Apple Create subtitle metadata lookup now exposes an editable lookup filename before Lookup or Refresh, matching the Web metadata loader for renamed or manually selected subtitle sources."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-metadata-preview",
                    title: "Create loads subtitle metadata",
                    detail: "Apple Create subtitle jobs can now load TV metadata before submission, edit job label, show, season, episode, title, and airdate fields on iPad, and send the enriched metadata JSON with the job."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-metadata-preview",
                    title: "Create loads video metadata",
                    detail: "Apple Create YouTube Dub can now load TV and YouTube metadata before submission, edit the key title, channel, series, and episode fields on iPad, and send the enriched metadata payload with the job."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-inline-subtitles",
                    title: "Create extracts subtitles",
                    detail: "Apple Create YouTube Dub can now inspect embedded subtitle streams in a selected NAS video, extract text subtitle tracks through the backend, refresh the NAS library, and select the extracted subtitle for the job."
                ),
                AppChangelogEntry(
                    id: "apple-create-ipad-two-column-detail",
                    title: "Create uses iPad space",
                    detail: "iPad and local Mac Designed for iPad Create now use a two-column detail editor, keeping source/setup fields on the left and narration, output, status, and submit settings on the right."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-23",
            dateLabel: "June 23, 2026",
            version: "2026.06.23.96",
            entries: [
                AppChangelogEntry(
                    id: "apple-create-ipad-detail-settings",
                    title: "Create settings moved right",
                    detail: "On iPad and local Mac Designed for iPad, Apple Create now keeps the job type and creation settings in the detail panel instead of spending sidebar space on job settings."
                ),
                AppChangelogEntry(
                    id: "apple-create-generated-book-history-defaults",
                    title: "Create remembers generated books",
                    detail: "Apple Create generated-book mode now reuses recent generated-book prompt, language, voice, narration, output, lookup, and image defaults without borrowing Narrate EPUB history."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-video-history-defaults",
                    title: "Create reuses job defaults",
                    detail: "Apple Create now mirrors Web rerun behavior for untouched subtitle and YouTube dubbing jobs by reusing recent sources, time offsets, translation settings, and video tuning defaults."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-show-original-memory",
                    title: "Create remembers subtitles",
                    detail: "Apple Create subtitle jobs now remember the Show Original preference per API/user scope, matching Web's returning-user subtitle default."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-base-dir",
                    title: "Create browses video roots",
                    detail: "Apple Create YouTube dubbing now exposes and remembers the NAS base directory, matching Web's alternate video-root refresh flow."
                ),
                AppChangelogEntry(
                    id: "apple-create-shared-language-defaults",
                    title: "Create remembers languages",
                    detail: "Apple Create now remembers shared input language, target languages, and lookup-cache defaults per API/user scope across generated book, Narrate EPUB, subtitle, and video jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-source-memory",
                    title: "Create remembers videos",
                    detail: "Apple Create now remembers the last YouTube dubbing NAS video and subtitle selection per API/user scope and restores it when those files are still available."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-newest-playable",
                    title: "Create picks latest videos",
                    detail: "Apple Create YouTube dubbing now defaults to the newest NAS video with a playable subtitle track, matching Web's server-backed video ordering."
                ),
                AppChangelogEntry(
                    id: "apple-create-latest-subtitle-source",
                    title: "Create picks latest subtitles",
                    detail: "Apple Create subtitle jobs now decode source modification timestamps and default to the latest usable SRT/VTT source, matching Web source-selection behavior."
                ),
                AppChangelogEntry(
                    id: "apple-create-recent-job-defaults",
                    title: "Create remembers narration",
                    detail: "Apple Create now reuses recent book and narration job history for untouched Narrate EPUB defaults, including source paths, resume start sentence, languages, and lookup-cache preference."
                ),
                AppChangelogEntry(
                    id: "apple-create-epub-picker-tolerant",
                    title: "Create shows server EPUBs",
                    detail: "Apple Create Narrate EPUB now keeps backend-visible server EPUBs in the picker even when source entries arrive with older or incomplete file-type metadata."
                ),
                AppChangelogEntry(
                    id: "apple-create-newest-nas-ebook",
                    title: "Create picks latest EPUB",
                    detail: "Web and Apple Create now receive newest-first EPUB listings with file metadata, so Narrate EPUB defaults to the latest backend-visible NAS ebook when the source has not been edited."
                ),
                AppChangelogEntry(
                    id: "apple-create-voice-preview",
                    title: "Create previews voices",
                    detail: "Apple Create now loads the shared TTS voice inventory, adds language-matched voice choices for source and target narration, and previews selected voices through backend audio synthesis."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-video-source-pickers",
                    title: "Create finds video sources",
                    detail: "Apple Create now loads backend subtitle sources and NAS YouTube/video library entries, with pickers that prefill subtitle jobs and YouTube dubbing jobs without manual path entry."
                ),
                AppChangelogEntry(
                    id: "apple-local-macos-ipad-style",
                    title: "Local Mac build destination",
                    detail: "The Apple pipeline now includes a repeatable local macOS Designed for iPad/iPhone build target and a guarded command-line helper for unattended iPhone/iPad updates when explicitly confirmed."
                ),
                AppChangelogEntry(
                    id: "apple-create-server-ebook-picker",
                    title: "Create finds server EPUBs",
                    detail: "Apple Create Narrate EPUB now loads backend-visible EPUBs, offers a server EPUB picker, and auto-fills the preferred or first NAS EPUB when the source is still empty."
                ),
                AppChangelogEntry(
                    id: "create-cache-source-identity",
                    title: "Create cache isolation",
                    detail: "Web and Apple Create chapter loading now keeps runtime ingestion caches separate for same-named EPUBs in different folders, preventing stale chapter data from another source file."
                ),
                AppChangelogEntry(
                    id: "create-refined-cache-invalidation",
                    title: "Create chapter freshness",
                    detail: "Web and Apple Create chapter loading now invalidates cached refined sentences when the source EPUB changes, keeping chapter ranges fresh after file edits or replacements."
                ),
                AppChangelogEntry(
                    id: "create-content-index-cache",
                    title: "Create chapters load faster",
                    detail: "Web and Apple Create chapter loading now reuses a validated backend content-index cache, avoiding repeated EPUB section parsing when users reopen the chapter picker."
                ),
                AppChangelogEntry(
                    id: "apple-create-default-aliases",
                    title: "Create defaults aligned",
                    detail: "Apple Create now accepts the same backend default aliases as Web creation surfaces for translation providers and transliteration modes, including gtrans, googletranslate, ollama, and python-module."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-job-presentation",
                    title: "Subtitle Jobs presentation",
                    detail: "Web Subtitle Tool Jobs presentation now lives in a focused module with direct pipeline coverage for download-link resolution, metadata labels, retry summaries, and narrated-library move eligibility."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-job-utils",
                    title: "Subtitle Jobs helpers",
                    detail: "Web Subtitle Tool Jobs helpers now live in a focused module with direct pipeline coverage for retry summaries, generated subtitle files, missing-result selection, and newest-first ordering."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-metadata-utils",
                    title: "Subtitle metadata helpers",
                    detail: "Web Subtitle Tool TV metadata draft helpers now live in a focused module with direct pipeline coverage for record coercion, editable metadata copying, text cleanup, and episode-code formatting."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-source-utils",
                    title: "Subtitle source selection",
                    detail: "Web Subtitle Tool source selection now lives in a focused module with direct pipeline coverage for ASS avoidance, latest-source picking, and metadata source labels."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-feedback-utils",
                    title: "Subtitle submit feedback",
                    detail: "Web Subtitle Tool submitted-job feedback formatting now lives in a focused module so user-visible creation summaries stay pinned independently from the page shell."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-language-defaults-utils",
                    title: "Subtitle language defaults",
                    detail: "Web Subtitle Tool backend language-default mapping now lives in a focused module so target-language options and default input language stay pinned outside the page shell."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-prefill-utils",
                    title: "Subtitle prefill utilities",
                    detail: "Web Subtitle Tool rerun and prefill mapping now lives in a focused module so existing-job recreation stays pinned independently from the page shell."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-utils",
                    title: "Subtitle submit utilities",
                    detail: "Web Subtitle Tool submit and timecode normalization helpers now live in a focused module so creation payload tests target the Web-to-Apple parity contract directly."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-hook",
                    title: "Subtitle submit flow",
                    detail: "Web Subtitle Tool submit orchestration now lives in a focused hook with coverage for backend request handoff, field normalization, success feedback, intake refresh, and failure cleanup."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-status-hook",
                    title: "Subtitle submit refactor",
                    detail: "Web Subtitle Tool submit status now lives in a focused hook with coverage for queue-capacity rejection, request failures, and submit busy-state transitions."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-tab-state-hook",
                    title: "Subtitle tab refactor",
                    detail: "Web Subtitle Tool tab state and newest-first job sorting now live in a focused hook with coverage for tab changes and Jobs panel ordering."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-processing-options-hook",
                    title: "Subtitle options refactor",
                    detail: "Web Subtitle Tool processing options now live in a focused hook with coverage for form defaults and prefill or normalization setters."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-source-mode-hook",
                    title: "Subtitle source refactor",
                    detail: "Web Subtitle Tool source mode and upload-file state now live in a focused hook with coverage for ASS-source detection, upload labels, and stale error clearing."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-feedback-hook",
                    title: "Subtitle feedback refactor",
                    detail: "Web Subtitle Tool submit feedback now lives in a focused hook with coverage for submitted summary formatting and empty optional details."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-language-state-hook",
                    title: "Subtitle language refactor",
                    detail: "Web Subtitle Tool language state now lives in a focused hook with coverage for shared preferences, backend target-language options, and normalized input and target handlers."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-prefill-hook",
                    title: "Subtitle prefill refactor",
                    detail: "Web Subtitle Tool rerun and prefill application now lives in a focused hook with coverage for full, partial, absent, and updated parameter snapshots."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-show-original-hook",
                    title: "Subtitle preference refactor",
                    detail: "Web Subtitle Tool show-original subtitle preference now lives in a focused hook with coverage for stored values, persistence, and storage failures."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-language-defaults-hook",
                    title: "Subtitle defaults refactor",
                    detail: "Web Subtitle Tool backend language-default loading now lives in a focused hook with coverage for target lists, default input language, failed fetches, and stale responses."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-models-hook",
                    title: "Subtitle model refactor",
                    detail: "Web Subtitle Tool model-option loading now lives in a focused hook with coverage for success, empty, failed, and late-response flows."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-results-hook",
                    title: "Subtitle result refactor",
                    detail: "Web Subtitle Tool completed-result fetching now lives in a focused hook with coverage for dedupe, partial failures, and late-response cancellation."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-sources-hook",
                    title: "Subtitle source refactor",
                    detail: "Web Subtitle Tool source listing, selection preservation, refresh, and delete state now live in a focused hook with coverage for empty, failed, cancelled, and confirmed flows."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-metadata-hook",
                    title: "Subtitle metadata refactor",
                    detail: "Web Subtitle Tool TV metadata lookup state now lives in a focused hook with stale-request and draft-edit coverage, preserving the existing metadata workflow."
                ),
                AppChangelogEntry(
                    id: "web-create-intake-shared-callout",
                    title: "Web intake parity",
                    detail: "Web Subtitle Tool and Video Dubbing now reuse the Create job-intake status callout and disable new submissions when the backend queue is at capacity."
                ),
                AppChangelogEntry(
                    id: "create-intake-limit-details",
                    title: "Create queue limits",
                    detail: "Web and Apple Create now show delayed job count plus soft and hard queue limits in the job intake status."
                ),
                AppChangelogEntry(
                    id: "create-intake-loading-state",
                    title: "Create intake loading",
                    detail: "Web and Apple Create now show a visible Checking job intake state while the queue snapshot is loading."
                ),
                AppChangelogEntry(
                    id: "web-create-intake-refresh-success",
                    title: "Create refresh accuracy",
                    detail: "Web Create now refreshes backend job intake status only after a successful enqueue, matching the Apple Create behavior and avoiding misleading refreshes after rejected submissions."
                ),
                AppChangelogEntry(
                    id: "create-intake-status-refresh",
                    title: "Create queue refresh",
                    detail: "Web and Apple Create now refresh backend job intake status after successful submission, keeping queue pressure counts current after enqueue."
                ),
                AppChangelogEntry(
                    id: "create-intake-status",
                    title: "Create checks intake",
                    detail: "Web and Apple Create now show backend job intake status before submission, warning under queue pressure and blocking submit when the backend is at capacity."
                ),
                AppChangelogEntry(
                    id: "web-backend-queue-pressure",
                    title: "Queue pressure status",
                    detail: "Web admin System status now shows backend job intake pressure, pending depth, and running jobs before long job submissions."
                ),
                AppChangelogEntry(
                    id: "apple-web-create-handoff",
                    title: "Web create handoff",
                    detail: "Apple Create on iPhone and iPad now includes an Open Web Create action that deep-links to the matching advanced Web creation surface."
                ),
                AppChangelogEntry(
                    id: "apple-book-default-target-languages",
                    title: "Apple target defaults",
                    detail: "Apple generated-book and Narrate EPUB creation now preserve multi-target backend defaults in the visible Additional target languages field."
                ),
                AppChangelogEntry(
                    id: "web-book-default-target-languages",
                    title: "Web target defaults",
                    detail: "Web book narration now preserves multi-target defaults from persisted preferences, backend defaults, and latest-job settings in the visible Additional target languages field."
                ),
                AppChangelogEntry(
                    id: "web-book-prefill-target-languages",
                    title: "Web multi-target reuse",
                    detail: "Web book narration rerun and prefill now preserve additional target languages instead of collapsing multi-target history back to a single target."
                ),
                AppChangelogEntry(
                    id: "web-book-additional-target-languages",
                    title: "Web multi-target books",
                    detail: "Web book narration now exposes additional target languages and submits selected plus manual targets as a de-duplicated multi-target list, matching Apple Create behavior."
                ),
                AppChangelogEntry(
                    id: "apple-per-language-voice-overrides",
                    title: "Target voice overrides",
                    detail: "Apple generated-book and Narrate EPUB creation now expose per-target-language voice override pickers, matching the Web voice override payload shape while preserving the global target voice fallback."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-offset-keyboard",
                    title: "Narrate EPUB offsets",
                    detail: "Apple Narrate EPUB end-sentence entry now uses punctuation-capable input on iPhone and iPad, making Web-aligned +offset windows practical from the software keyboard."
                ),
                AppChangelogEntry(
                    id: "apple-create-audio-duration-estimate",
                    title: "Apple duration estimate",
                    detail: "Apple generated-book and Narrate EPUB creation now show Web-aligned estimated audio duration, and Narrate EPUB accepts +offset end-sentence windows before submit."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-chapter-ranges",
                    title: "Narrate EPUB chapter ranges",
                    detail: "Apple Narrate EPUB chapter selection now supports a consecutive start-to-end chapter range, matching the Web processing-window behavior."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-chapters",
                    title: "Narrate EPUB chapters",
                    detail: "Apple Narrate EPUB creation can now load a server EPUB chapter index and apply a selected chapter range to the submitted sentence window."
                ),
                AppChangelogEntry(
                    id: "apple-base-output-slugs",
                    title: "Apple output slugs",
                    detail: "Apple Create now derives Web-aligned output slugs from source filenames, stripping final file extensions from EPUB, subtitle, and video paths before submission."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-metadata",
                    title: "Narrate EPUB metadata",
                    detail: "Apple Narrate EPUB creation now exposes optional title, author, and genre metadata fields and submits them through Web-aligned book metadata and config aliases."
                ),
                AppChangelogEntry(
                    id: "apple-web-book-genres",
                    title: "Book genre lists",
                    detail: "Web and Apple book creation now submit structured book_genres arrays alongside visible book_genre text, keeping edited and lookup genres aligned across surfaces."
                ),
                AppChangelogEntry(
                    id: "active-book-request-aliases",
                    title: "Active request metadata",
                    detail: "In-memory book lookup enrichment now keeps book_isbn, book_genre, and book_genres aligned in active pipeline request config after metadata persistence."
                ),
                AppChangelogEntry(
                    id: "persisted-book-lookup-aliases",
                    title: "Persisted book metadata",
                    detail: "Persisted book lookup metadata now keeps book_isbn, book_genre, and book_genres in job media metadata and config after lookup enrichment."
                ),
                AppChangelogEntry(
                    id: "backend-book-lookup-aliases",
                    title: "Book lookup aliases",
                    detail: "Backend book lookup payloads now emit book_isbn, book_genre, and book_genres aliases directly across OpenLibrary, Google Books fallback, and unified metadata results."
                ),
                AppChangelogEntry(
                    id: "google-books-language-genre",
                    title: "Google Books metadata",
                    detail: "Google Books fallback metadata now preserves language, book_language, and genre aliases so creation forms receive the same enriched lookup shape when OpenLibrary falls through."
                ),
                AppChangelogEntry(
                    id: "book-language-metadata",
                    title: "Book language metadata",
                    detail: "Web and Apple book creation now preserve book_language in metadata and config payloads, and OpenLibrary lookup can carry source language hints into Web submissions."
                ),
                AppChangelogEntry(
                    id: "web-book-lookup-genre",
                    title: "Web lookup genre",
                    detail: "Web book metadata lookup now persists preview genres into book_genre, so submitted config overrides carry the selected lookup genre without manual editing."
                ),
                AppChangelogEntry(
                    id: "web-book-genre-isbn-config",
                    title: "Web metadata parity",
                    detail: "Web book narration now promotes edited genre and ISBN metadata into config overrides, matching the Apple book_genre and book_isbn payload shape."
                ),
                AppChangelogEntry(
                    id: "apple-book-isbn-metadata",
                    title: "Apple ISBN metadata",
                    detail: "Generated-book and Narrate EPUB metadata now expose ISBN and submit Web-aligned book_genre and book_isbn aliases."
                ),
                AppChangelogEntry(
                    id: "apple-web-shape-voice-overrides",
                    title: "Apple voice payloads",
                    detail: "Generated-book and Narrate EPUB voice overrides now mirror the Web payload shape in both pipeline inputs and pipeline overrides."
                ),
                AppChangelogEntry(
                    id: "apple-multi-target-voice-overrides",
                    title: "Apple target voices",
                    detail: "Generated-book and Narrate EPUB target voice overrides now apply across every submitted target language."
                ),
                AppChangelogEntry(
                    id: "apple-multi-target-books",
                    title: "Apple multi-target books",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned additional target languages and submit multi-target pipeline arrays."
                ),
                AppChangelogEntry(
                    id: "apple-image-api-url-overrides",
                    title: "Apple image API URLs",
                    detail: "Generated-book creation now exposes Web-aligned image API URL overrides for selecting home Draw Things and image worker nodes."
                ),
                AppChangelogEntry(
                    id: "apple-book-performance-overrides",
                    title: "Apple book performance",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned worker threads, queue size, and max job worker overrides for backend performance tuning."
                ),
                AppChangelogEntry(
                    id: "apple-book-cover-file",
                    title: "Apple book cover path",
                    detail: "Generated-book and Narrate EPUB creation now expose a Web-aligned cover file path field, submitting book_cover_file through metadata and config."
                ),
                AppChangelogEntry(
                    id: "apple-book-metadata-fields",
                    title: "Apple book metadata",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned metadata summary and year fields, submitting them through book_metadata and matching book config keys."
                ),
                AppChangelogEntry(
                    id: "apple-book-llm-model-picker",
                    title: "Apple book LLM model",
                    detail: "Generated-book and Narrate EPUB creation now expose the Web-aligned optional LLM model picker and submit ollama_model when selected."
                ),
                AppChangelogEntry(
                    id: "apple-target-voice-overrides",
                    title: "Apple target voice overrides",
                    detail: "Generated-book and Narrate EPUB creation now expose a target-language voice override that submits the backend voice_overrides payload when selected."
                ),
                AppChangelogEntry(
                    id: "apple-book-output-chunking",
                    title: "Apple output chunking",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned sentences-per-file and stitch-full-book output controls before submit."
                ),
                AppChangelogEntry(
                    id: "apple-book-translation-tuning",
                    title: "Apple translation tuning",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned translation provider, translation batch, transliteration mode/model, and lookup cache batch controls before submit."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-sentence-range",
                    title: "Apple Narrate EPUB ranges",
                    detail: "Narrate EPUB creation on iPhone and iPad now exposes Web-aligned start and end sentence range controls before submit."
                ),
                AppChangelogEntry(
                    id: "apple-create-narration-controls",
                    title: "Apple narration controls",
                    detail: "Generated-book and Narrate EPUB creation on iPhone and iPad now expose Web-aligned narration controls for audio generation, audio mode, audio quality, written mode, and tempo before submit."
                ),
                AppChangelogEntry(
                    id: "apple-create-html-pdf-output",
                    title: "Apple HTML and PDF outputs",
                    detail: "Generated-book and Narrate EPUB creation on iPhone and iPad now expose Web-aligned HTML and PDF output toggles before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-performance",
                    title: "Apple image performance",
                    detail: "Generated-book creation on iPhone and iPad now lets illustration jobs optionally set image worker concurrency and image API timeout before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-continuity",
                    title: "Apple image continuity",
                    detail: "Generated-book creation on iPhone and iPad now lets illustration jobs seed from the previous generated image and enable backend blank-image detection before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-tuning",
                    title: "Apple image tuning",
                    detail: "Generated-book creation on iPhone and iPad now lets illustration jobs optionally set image steps, CFG scale, and sampler name before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-batching",
                    title: "Apple image batching",
                    detail: "Generated-book creation on iPhone and iPad now lets Prompt plan illustration jobs group sentences into shared images and tune prompt-plan batch size before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-dimensions",
                    title: "Apple image dimensions",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs set backend image width and height before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-prompt-pipeline",
                    title: "Apple image prompt pipeline",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs choose Prompt plan or Visual canon before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-prompt-context",
                    title: "Apple image prompt context",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs tune the backend image prompt context count before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-style",
                    title: "Apple illustration styles",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs choose the backend image style template before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-illustrations-toggle",
                    title: "Apple generated-book illustrations",
                    detail: "Generated-book creation on iPhone and iPad now includes an Illustrations toggle that follows backend defaults and submits add_images with the job payload."
                ),
                AppChangelogEntry(
                    id: "backend-search-match-summary",
                    title: "Search backend allocation trimmed",
                    detail: "Generated-media search now keeps the first match span and occurrence count without building a large tuple list for repeated common terms, preserving Web and Apple search results."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-source-refresh-selection",
                    title: "Web Subtitle source selection fixed",
                    detail: "Subtitle Tool refresh now uses a tested source-selection rule that clears stale selections after deletes and chooses the latest usable subtitle source when needed."
                ),
                AppChangelogEntry(
                    id: "pipeline-subtitle-tool-web-check",
                    title: "Subtitle Tool Web check added",
                    detail: "The shared pipeline now runs the Subtitle Tool focused Web check for ebook-tools alongside Create, Library, Video Dubbing, and production/export build checks."
                ),
                AppChangelogEntry(
                    id: "web-video-dubbing-delete-selection",
                    title: "Web Video Dubbing selection hardened",
                    detail: "Deleting a NAS or YouTube video now uses a tested fallback that keeps the current selection when possible and chooses the next default subtitle when needed."
                ),
                AppChangelogEntry(
                    id: "pipeline-video-dubbing-web-check",
                    title: "Video Dubbing Web check added",
                    detail: "The shared pipeline now runs the Video Dubbing focused Web check for ebook-tools alongside Create, Library, and production/export build checks."
                ),
                AppChangelogEntry(
                    id: "web-library-metadata-update-plan",
                    title: "Web Library metadata saves hardened",
                    detail: "Library metadata edits now use a tested update plan that preserves source upload ordering, changed-ISBN apply behavior, and explicit ISBN clears."
                ),
                AppChangelogEntry(
                    id: "pipeline-web-library-check-redaction",
                    title: "Pipeline Web check hygiene",
                    detail: "The shared pipeline now runs a Library-focused Web check for ebook-tools and collapses Vite environment debug dumps while keeping generated build artifacts cleaned up."
                ),
                AppChangelogEntry(
                    id: "apple-job-creation-summary",
                    title: "Creation summaries in Jobs",
                    detail: "Job rows on iPhone, iPad, and Apple TV now surface generated-book creation messages, warnings, sample sentences, or seed EPUB context from backend metadata."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-22",
            dateLabel: "June 22, 2026",
            version: "2026.06.22.170",
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
