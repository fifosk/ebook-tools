enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-25",
            dateLabel: "June 25, 2026",
            version: "2026.06.25.4",
            entries: [
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
