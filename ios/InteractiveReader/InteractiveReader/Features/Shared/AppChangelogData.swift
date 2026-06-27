enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-27",
            dateLabel: "June 27, 2026",
            version: "2026.06.27.001",
            entries: [
                AppChangelogEntry(
                    id: "ipad-playback-command-readiness",
                    title: "iPad playback commands start audio",
                    detail: "Interactive Reader now sets autoplay intent before presenting job or library playback and routes Space/tap play through a player-aware command that prepares the selected chunk when no audio item is active, so autoplay and Space can start playback instead of only toggling an already-loaded player."
                ),
                AppChangelogEntry(
                    id: "ipad-keyboard-responder-chain-backstop",
                    title: "iPad keyboard has an app backstop",
                    detail: "Interactive Reader now keeps the shared player keyboard broker active from the player controller and exposes Space, Enter, Left, and Right through the app delegate responder chain, so paused lookup focus has another hardware-key route before falling back to touch controls."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-bubble-key-bridge",
                    title: "Lookup bubble keeps keyboard control",
                    detail: "Paused iPad lookup bubbles now include a bubble-scoped hardware-key bridge for Space, Enter, Left, and Right. It forwards through the shared player broker first, then falls back to the current player callbacks so lookup focus cannot strand word navigation or play/pause."
                ),
                AppChangelogEntry(
                    id: "ipad-keyboard-stale-modifier-resync",
                    title: "iPad arrows recover from stuck modifiers",
                    detail: "Interactive Reader now rechecks live hardware-keyboard Control and Shift state before routing Left, Right, or Space, so lookup Read Aloud focus changes cannot leave plain arrows acting like sentence skips or block Space play/pause."
                ),
                AppChangelogEntry(
                    id: "ipad-keyboard-fail-open-dispatch",
                    title: "iPad keyboard controls fail open",
                    detail: "Interactive Reader now lets UIKeyCommand, raw iPad key presses, text fallback, app broker, and GameController paths all reach the same callbacks immediately, so Space play/pause, Enter lookup, and Left/Right word movement keep working even when one keyboard source goes quiet."
                ),
                AppChangelogEntry(
                    id: "created-jobs-autoplay-reader",
                    title: "New jobs start playback",
                    detail: "Jobs opened directly from Create now enter the Jobs player with autoplay enabled, while ordinary browse-row resume behavior stays unchanged."
                ),
                AppChangelogEntry(
                    id: "book-discovery-default-sources",
                    title: "Book discovery can search defaults",
                    detail: "Web Narrate Ebook and Apple Narrate EPUB now expose a Default sources discovery option when the backend advertises multiple available book defaults, letting local EPUB and manual download folders be searched together."
                ),
                AppChangelogEntry(
                    id: "ipad-plain-arrow-single-dispatch",
                    title: "iPad arrows stop double-firing",
                    detail: "Interactive reader hardware Left and Right keys now use a physical-arrow latch across broker, GameController, and first-responder paths, so paused word navigation cannot also skip sentence batches from a duplicate event."
                ),
                AppChangelogEntry(
                    id: "default-video-source-group",
                    title: "Video discovery can search defaults",
                    detail: "Web and Apple Create now expose a Default sources video discovery option that lets the backend search its configured NAS, manual, YouTube, and indexer defaults in one pass."
                ),
                AppChangelogEntry(
                    id: "default-video-indexer-discovery",
                    title: "Indexer search joins video discovery",
                    detail: "When the backend has a Newznab, Torznab, or Prowlarr endpoint configured, Web and Apple Create now include review-only indexer metadata in the default video discovery pass without exposing raw URLs or starting downloads."
                ),
                AppChangelogEntry(
                    id: "apple-gate-seek-helper-contract",
                    title: "Sentence gates have a real guard",
                    detail: "The Apple reader now resolves original-only and translation-only sentence gates through the shared sentence-position helper, with executable coverage for original, translated, mixed, invalid, and out-of-range gate cases."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-gate-first-skips",
                    title: "Dutch-only skips use sentence gates",
                    detail: "Interactive reader skips now share one explicit sentence-row jump path and single-track original or translation seeks prefer per-sentence gates before token timelines, reducing Dutch-only drift and batch skips after jumps."
                ),
                AppChangelogEntry(
                    id: "content-index-span-coverage",
                    title: "Chapter maps expose text coverage",
                    detail: "Backend content indexes now include token-safe per-section span coverage so Web and Apple playback debugging can detect skipped EPUB text without logging source passages."
                ),
                AppChangelogEntry(
                    id: "apple-golden-runtime-ssh-check",
                    title: "Golden pipeline remembers Mac Studio",
                    detail: "The Apple golden pipeline now verifies the remembered fifo@192.168.1.9 runtime checkout path and Git head before source-sync, without pulling, building, installing, or launching devices."
                ),
                AppChangelogEntry(
                    id: "apple-local-timing-context-regression",
                    title: "Late-chapter Dutch playback is guarded",
                    detail: "Apple playback now has an executable regression check for late-chapter chunks whose display sentence numbers are global but timing tokens are chunk-local, protecting Dutch-only jumps from losing the rendered sentence."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-keyboard-reclaim-after-speech",
                    title: "Lookup arrows survive Read Aloud",
                    detail: "iPad playback now reactivates the shared keyboard broker whenever lookup pronunciation starts or finishes, so paused bubble Left and Right keys keep moving the highlighted word."
                ),
                AppChangelogEntry(
                    id: "apple-video-visible-progress-sliders",
                    title: "Video playback gets sliders",
                    detail: "iPhone and iPad video playback now show a bottom progress slider, while Apple TV exposes a focusable scrubber above transport controls for direct remote seeking."
                ),
                AppChangelogEntry(
                    id: "tvos-progress-slider-remote-steps",
                    title: "TV sliders scrub with arrows",
                    detail: "Apple TV book and video progress sliders now honor focused Left and Right remote clicks: books move by one sentence and videos move in 15-second steps."
                ),
                AppChangelogEntry(
                    id: "translation-only-book-sync-tightening",
                    title: "Translation-only sync is tighter",
                    detail: "Book playback now clears stale sequence plans before loading a single translation track and seeks sentence jumps against the enabled track, preventing Dutch-only playback from drifting onto original timing."
                ),
                AppChangelogEntry(
                    id: "sentence-skip-targets-distinct-sentences",
                    title: "Sentence skip avoids batch jumps",
                    detail: "Interactive sentence skipping now targets the next distinct sentence on the preferred track instead of stepping through stale sequence segments, so one skip no longer jumps a batch of translated sentences."
                ),
                AppChangelogEntry(
                    id: "single-track-skip-rendered-index",
                    title: "Dutch-only skips stay local",
                    detail: "Single-track book playback now skips from the rendered sentence index instead of the next raw timestamp, keeping Dutch translation-only navigation from jumping whole batches when timing gates drift."
                ),
                AppChangelogEntry(
                    id: "single-track-same-url-plan-reset",
                    title: "Dutch-only reloads clear old plans",
                    detail: "Switching to an already-loaded single Dutch track now clears stale sequence plans too, preventing same-URL reloads from reusing old original/translation timing state."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-arrows-global-broker",
                    title: "Lookup arrows survive focus steals",
                    detail: "iPad lookup-bubble Left and Right keys now route through the global keyboard broker as word navigation, so Read Aloud focus changes no longer strand the highlighted word."
                ),
                AppChangelogEntry(
                    id: "ipad-read-aloud-arrow-debounce-reset",
                    title: "Read Aloud arrows recover faster",
                    detail: "iPad lookup Read Aloud now clears shared keyboard broker and player debounce state when pronunciation starts, finishes, or player focus is reclaimed, so the first Left or Right press can keep moving lookup words."
                ),
                AppChangelogEntry(
                    id: "ipad-video-lookup-debounce-reset",
                    title: "Video lookup keys recover too",
                    detail: "Video lookup Read Aloud now clears stale subtitle keyboard dispatch state before pronunciation and reactivates the shared broker with a fresh debounce window, matching book playback."
                ),
                AppChangelogEntry(
                    id: "pipeline-metadata-label-normalization",
                    title: "Job labels stay cleaner",
                    detail: "Apple and Web job creation now normalize source and provider metadata at the pipeline service boundary, keeping job cards, destination pills, and reader metadata from inheriting mixed-case discovery labels."
                ),
                AppChangelogEntry(
                    id: "create-intake-status-safe-errors",
                    title: "Create queue checks fail cleaner",
                    detail: "If the backend cannot inspect job-intake pressure, Apple and Web Create now receive a generic unavailable response with token-safe telemetry instead of raw queue backend details."
                ),
                AppChangelogEntry(
                    id: "create-content-index-safe-telemetry",
                    title: "Chapter loading is easier to diagnose",
                    detail: "EPUB chapter loading now records token-safe success, validation, missing-file, and parser-error outcomes for Apple and Web Create without logging source filenames or paths."
                ),
                AppChangelogEntry(
                    id: "pipeline-job-action-route-id-normalization",
                    title: "Job actions tolerate padded IDs",
                    detail: "Apple and Web pause, resume, cancel, delete, and restart controls now trim padded job IDs and reject blank IDs before touching backend job storage."
                ),
                AppChangelogEntry(
                    id: "playback-timing-route-id-normalization",
                    title: "Timing lookups tolerate padded IDs",
                    detail: "Apple and Web playback timing resolvers now trim padded job IDs and return generic authorization failures without exposing backend paths or user details."
                ),
                AppChangelogEntry(
                    id: "storage-media-stream-route-id-normalization",
                    title: "Media streams tolerate padded IDs",
                    detail: "Apple and Web audio, video, and text file streams now trim padded job IDs and return generic authorization failures without exposing backend paths."
                ),
                AppChangelogEntry(
                    id: "job-media-manifest-route-id-normalization",
                    title: "Media manifests tolerate padded IDs",
                    detail: "Apple and Web playback setup now trims padded job IDs for completed, live, and chunk media manifests and returns generic authorization failures without exposing backend paths."
                ),
                AppChangelogEntry(
                    id: "shared-media-root-route-id-normalization",
                    title: "Media helpers share cleaner access",
                    detail: "Sentence-image and lookup-cache media helpers now trim padded job IDs and return generic authorization failures without exposing backend paths."
                ),
                AppChangelogEntry(
                    id: "resume-response-validation-safe-errors",
                    title: "Resume sync fails cleaner",
                    detail: "Resume-position response validation now keeps returning stable generic errors instead of logging success before malformed Apple and Web playback resume payloads are rejected."
                ),
                AppChangelogEntry(
                    id: "create-template-response-validation-safe-errors",
                    title: "Template sync fails cleaner",
                    detail: "Creation-template storage and response validation now return stable generic errors instead of exposing template IDs, user IDs, local paths, or malformed Apple and Web Create template payloads."
                ),
                AppChangelogEntry(
                    id: "audio-voice-response-validation-safe-errors",
                    title: "Voice pickers fail cleaner",
                    detail: "Audio voice inventory and match responses now validate before success telemetry, keeping malformed Apple and Web Create voice payloads behind stable generic errors."
                ),
                AppChangelogEntry(
                    id: "subtitle-picker-safe-errors",
                    title: "Subtitle pickers fail cleaner",
                    detail: "Subtitle source and model pickers now return generic errors for scan, permission, and malformed payload failures instead of exposing NAS paths, source filenames, user IDs, or private model data."
                ),
                AppChangelogEntry(
                    id: "assistant-lookup-response-validation-safe-errors",
                    title: "Lookup errors stay cleaner",
                    detail: "Assistant lookup now validates responses before success telemetry and keeps bad-request details generic, so lookup bubbles do not expose selected words, prompts, models, or malformed token-usage payloads."
                ),
                AppChangelogEntry(
                    id: "offline-export-response-validation-safe-errors",
                    title: "Offline exports fail cleaner",
                    detail: "Offline export creation and download failures now keep malformed responses and unexpected resolver errors behind generic messages without exposing export IDs, filenames, or storage paths."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-discovery-validation-safe-errors",
                    title: "Discovery pickers fail cleaner",
                    detail: "Acquisition provider and discovery responses now validate before success telemetry, keeping malformed Apple and Web Create discovery payloads behind generic errors without exposing provider IDs, source paths, or candidate tokens."
                ),
                AppChangelogEntry(
                    id: "acquisition-handoff-validation-safe-errors",
                    title: "Discovery handoffs fail cleaner",
                    detail: "Acquisition acquire, artifact-prepare, and downloader job responses now validate before success telemetry so malformed artifact or task payloads stay behind generic errors."
                ),
                AppChangelogEntry(
                    id: "create-defaults-safe-errors",
                    title: "Create defaults fail cleaner",
                    detail: "Pipeline defaults loading now uses the same generic unavailable response and token-safe telemetry, so Apple and Web Create never expose local config paths when defaults cannot be resolved."
                ),
                AppChangelogEntry(
                    id: "create-image-node-safe-errors",
                    title: "Image-node checks fail cleaner",
                    detail: "Illustration node availability checks now return a generic unavailable response if Draw Things URL normalization or probing fails, keeping configured node URLs out of Apple and Web Create errors."
                ),
                AppChangelogEntry(
                    id: "create-audio-voice-safe-errors",
                    title: "Voice picker errors stay private",
                    detail: "Audio voice inventory and voice-match failures now return generic unavailable responses with token-safe telemetry, keeping local voice paths, language parameters, and model names out of Apple and Web Create errors."
                ),
                AppChangelogEntry(
                    id: "create-audio-preview-safe-errors",
                    title: "Voice previews fail cleaner",
                    detail: "Audio preview setup failures now return a generic unavailable response with token-safe telemetry, keeping config paths, sample text, language parameters, and voice identifiers out of Apple and Web Create errors."
                ),
                AppChangelogEntry(
                    id: "create-acquisition-provider-safe-errors",
                    title: "Discovery setup fails cleaner",
                    detail: "Acquisition provider registry setup failures now return a generic unavailable response with token-safe telemetry, keeping local config paths and provider secrets out of Apple and Web Create errors."
                ),
                AppChangelogEntry(
                    id: "assistant-lookup-safe-errors",
                    title: "Lookup errors stay private",
                    detail: "Assistant lookup backend failures now return a generic error with token-safe telemetry, keeping selected words, prompts, model names, provider details, and local paths out of Web and Apple playback errors."
                ),
                AppChangelogEntry(
                    id: "library-isbn-preview-safe-errors",
                    title: "ISBN previews fail cleaner",
                    detail: "Library ISBN metadata preview failures now return a generic lookup error with token-safe telemetry, keeping ISBNs, Open Library/provider messages, local paths, and tokens out of Web and Apple Library errors."
                ),
                AppChangelogEntry(
                    id: "youtube-actions-no-traceback-logs",
                    title: "Video errors log less",
                    detail: "YouTube discovery, download, cleanup, and dubbing failures no longer attach raw tracebacks to token-safe logs, keeping URLs, NAS paths, titles, languages, voices, and tokens out of Web and Apple video Create diagnostics."
                ),
                AppChangelogEntry(
                    id: "auth-oauth-registration-safe-errors",
                    title: "Sign-in errors stay private",
                    detail: "OAuth and registration setup failures now return stable generic errors, keeping provider configuration, identity-token text, email addresses, and local user-store paths out of Apple and Web sign-in responses."
                ),
                AppChangelogEntry(
                    id: "offline-export-safe-errors",
                    title: "Offline export errors stay private",
                    detail: "Offline export create and download failures now return generic route errors, keeping source IDs, export IDs, storage paths, and export template locations out of Apple and Web offline-sync responses."
                ),
                AppChangelogEntry(
                    id: "resume-sync-safe-telemetry",
                    title: "Resume sync is easier to diagnose",
                    detail: "Resume-position list, get, save, and delete routes now emit token-safe timing results and use generic storage-failure responses, keeping user IDs, job IDs, and resume storage paths out of Apple and Web playback sync diagnostics."
                ),
                AppChangelogEntry(
                    id: "bookmark-sync-safe-errors",
                    title: "Bookmark sync errors stay private",
                    detail: "Bookmark list, add, and delete storage failures now return a generic unavailable response while preserving token-safe route metrics, keeping job IDs, bookmark IDs, user IDs, and storage paths out of Apple and Web playback sync errors."
                ),
                AppChangelogEntry(
                    id: "reading-bed-safe-errors",
                    title: "Reading-bed errors stay private",
                    detail: "Reading-bed catalog, stream, upload, update, and delete storage failures now return generic unavailable responses, keeping bed IDs, upload labels, filenames, and storage paths out of Apple and Web background-music errors."
                ),
                AppChangelogEntry(
                    id: "reading-bed-route-id-normalization",
                    title: "Reading-bed controls resolve cleaner",
                    detail: "Reading-bed stream, update, and delete routes now trim padded IDs and reject blank IDs before storage access, keeping Apple and Web background-music controls aligned."
                ),
                AppChangelogEntry(
                    id: "notification-sync-safe-telemetry",
                    title: "Notification sync is easier to diagnose",
                    detail: "Notification registration, removal, test send, rich test send, and preference routes now emit token-safe timing results and return generic failure responses, keeping device tokens, user IDs, titles, cover URLs, and storage paths out of Apple diagnostics."
                ),
                AppChangelogEntry(
                    id: "notification-device-token-normalization",
                    title: "Notification devices sync cleaner",
                    detail: "Apple push device registration and removal now trim padded tokens, reject blank removals before storage access, and keep malformed preference-device payloads behind generic sync errors."
                ),
                AppChangelogEntry(
                    id: "subtitle-models-safe-telemetry",
                    title: "Subtitle model checks stay private",
                    detail: "Subtitle Create model inventory now emits token-safe timing results and avoids logging user IDs, model tags, provider paths, or backend exception text when Apple and Web pickers refresh."
                ),
                AppChangelogEntry(
                    id: "acquisition-async-provider-safe-errors",
                    title: "Downloader handoff errors stay private",
                    detail: "Acquisition async-job provider validation no longer echoes submitted provider strings, URLs, or token-like query parameters when Apple and Web downloader handoffs reject unsupported providers."
                ),
                AppChangelogEntry(
                    id: "library-source-upload-safe-errors",
                    title: "Source replacement fails cleaner",
                    detail: "Library source replacement now returns generic upload errors with token-safe timing, keeping backend paths, job IDs, and selected filenames out of Apple and Web source-upload diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-metadata-edit-safe-errors",
                    title: "Metadata edits fail cleaner",
                    detail: "Library metadata edits now return stable generic errors with token-safe timing, keeping edited titles, authors, job IDs, and library paths out of Apple and Web edit-sheet diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-isbn-apply-safe-errors",
                    title: "ISBN apply fails cleaner",
                    detail: "Library ISBN apply now returns stable generic errors with token-safe timing, keeping ISBNs, job IDs, cache paths, and provider details out of Apple and Web metadata diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-metadata-enrich-safe-errors",
                    title: "Metadata enrichment fails cleaner",
                    detail: "Library metadata enrichment now returns stable generic errors with token-safe timing, keeping provider messages, job IDs, cache paths, and tokens out of Apple and Web enrichment diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-metadata-refresh-safe-errors",
                    title: "Metadata refresh fails cleaner",
                    detail: "Library metadata refresh now returns stable generic errors with token-safe timing, keeping source paths, provider messages, job IDs, and tokens out of Web refresh diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-remove-safe-errors",
                    title: "Library deletes fail cleaner",
                    detail: "Library item deletion now returns stable generic errors with token-safe timing, keeping job IDs, library paths, and backend storage details out of Apple and Web delete diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-move-safe-errors",
                    title: "Library moves fail cleaner",
                    detail: "Move-to-Library now returns stable generic errors with token-safe timing, keeping permission text, job IDs, library paths, and queue storage details out of Apple and Web move diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-media-remove-safe-errors",
                    title: "Media cleanup fails cleaner",
                    detail: "Library media-removal now returns stable generic errors with token-safe timing, keeping job IDs, library paths, media folders, and serialization details out of Web cleanup diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-list-safe-errors",
                    title: "Library lists fail cleaner",
                    detail: "Library item-list failures now return a stable generic error with token-safe timing, keeping search terms, user IDs, index paths, and serialization details out of Apple and Web Library diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-media-manifest-safe-errors",
                    title: "Playback manifests fail cleaner",
                    detail: "Library media-manifest failures now return stable generic errors with token-safe timing, keeping job IDs, media filenames, library paths, and manifest serialization details out of Apple and Web playback diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-media-file-safe-errors",
                    title: "Playback file errors stay private",
                    detail: "Library media-file resolver failures now return stable generic errors with token-safe timing, keeping job IDs, encoded file paths, filenames, and library storage paths out of Apple and Web stream diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-access-policy-safe-errors",
                    title: "Sharing errors stay private",
                    detail: "Library access-policy load and update failures now return stable generic errors with token-safe timing, keeping user IDs, grant subjects, job IDs, library paths, and policy serialization details out of Web sharing diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-reindex-safe-errors",
                    title: "Reindex errors stay private",
                    detail: "Library reindex failures now return stable generic errors with token-safe timing, keeping index database paths and library storage details out of admin maintenance diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-metadata-edit-serialization-safe-errors",
                    title: "Metadata edit errors stay private",
                    detail: "Library metadata edit access-check and serialization failures now keep returning stable generic errors, keeping job IDs, edited titles, authors, genres, and library storage paths out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-isbn-apply-serialization-safe-errors",
                    title: "ISBN apply errors stay private",
                    detail: "Library ISBN apply access-check and serialization failures now keep returning stable generic errors, keeping ISBNs, job IDs, cache paths, and library storage details out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-refresh-serialization-safe-errors",
                    title: "Refresh errors stay private",
                    detail: "Library metadata refresh access-check and serialization failures now keep returning stable generic errors, keeping job IDs, source paths, cache paths, and library storage details out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-enrich-serialization-safe-errors",
                    title: "Enrichment errors stay private",
                    detail: "Library metadata enrichment access-check and serialization failures now keep returning stable generic errors, keeping job IDs, provider cache paths, tokens, and library storage details out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-delete-access-safe-errors",
                    title: "Delete errors stay private",
                    detail: "Library delete access-check failures now keep returning stable generic errors, keeping job IDs, policy lookup paths, and library storage details out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-source-upload-serialization-safe-errors",
                    title: "Source upload errors stay private",
                    detail: "Library source-upload access-check and serialization failures now keep returning stable generic errors, keeping filenames, job IDs, temporary upload paths, and library storage details out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-move-validation-safe-errors",
                    title: "Move errors stay private",
                    detail: "Library move-to-library payload validation failures now keep returning stable generic errors, keeping job IDs, queue paths, and library storage details out of diagnostics."
                ),
                AppChangelogEntry(
                    id: "library-media-response-validation-safe-errors",
                    title: "Playback manifests fail cleaner",
                    detail: "Library media-manifest final payload validation now keeps returning stable generic errors instead of logging success before malformed Apple and Web playback manifests are rejected."
                ),
                AppChangelogEntry(
                    id: "library-reindex-response-validation-safe-errors",
                    title: "Reindex errors stay private",
                    detail: "Library reindex response validation now keeps returning stable generic errors instead of logging success before malformed admin maintenance counts are rejected."
                ),
                AppChangelogEntry(
                    id: "library-list-response-validation-safe-errors",
                    title: "Library lists fail cleaner",
                    detail: "Library list response validation now keeps returning stable generic errors instead of logging success before malformed Apple and Web Library result envelopes are rejected."
                ),
                AppChangelogEntry(
                    id: "bookmark-response-validation-safe-errors",
                    title: "Bookmark sync fails cleaner",
                    detail: "Bookmark response validation now keeps returning stable generic errors instead of logging success before malformed Apple and Web playback bookmark payloads are rejected."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-26",
            dateLabel: "June 26, 2026",
            version: "2026.06.26.183",
            entries: [
                AppChangelogEntry(
                    id: "ipad-read-aloud-keeps-arrow-navigation",
                    title: "Read Aloud keeps arrow keys",
                    detail: "iPad lookup Read Aloud now reclaims the shared player keyboard path after pronunciation audio or fallback speech starts, finishes, or cancels, and duplicate bubble-local arrow shortcuts were removed so Left and Right keep moving lookup words."
                ),
                AppChangelogEntry(
                    id: "ipad-video-lookup-keyboard-single-path",
                    title: "Video lookup keys match books",
                    detail: "iPad video playback now uses the same shared player keyboard path after lookup Read Aloud starts and no longer registers duplicate hidden SwiftUI arrow shortcuts over the video subtitle bubble."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-bubble-arrows-own-transport",
                    title: "Lookup bubble owns arrow keys",
                    detail: "When an iPad lookup bubble is open, plain Left and Right now navigate lookup words before playback transport checks run, avoiding stale AVPlayer playing-state from stealing paused word navigation."
                ),
                AppChangelogEntry(
                    id: "apple-create-acquisition-contract-readiness",
                    title: "Create discovery routes are guarded",
                    detail: "Apple Settings and Create readiness now surface acquisition provider, discover, acquire, job, artifact-prepare, and template route contracts so iPhone, iPad, Apple TV, and Web creation handoffs stay aligned."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-arrow-repeat-stability",
                    title: "iPad lookup arrows keep repeating",
                    detail: "Paused iPad lookup-bubble Left and Right keys now route each word move through a single definition refresh, avoiding duplicate lookup state churn after the first arrow press."
                ),
                AppChangelogEntry(
                    id: "reader-gate-only-dutch-sync",
                    title: "Translation-only chunks hold sync",
                    detail: "Interactive Reader now trusts sentence gate boundaries even when a job has no per-word timing tokens, keeping Dutch-only playback, slider jumps, and rendered sentences aligned around chunk edges."
                ),
                AppChangelogEntry(
                    id: "apple-create-preference-scope",
                    title: "Create preferences are scoped cleaner",
                    detail: "Apple Create now routes YouTube base directory, remembered source selections, subtitle original-display, language defaults, and YouTube library cache keys through one API/user-scoped preference wrapper."
                ),
                AppChangelogEntry(
                    id: "reader-language-sync-keyboard-hardening",
                    title: "Reader sync fixes tightened",
                    detail: "Apple playback now accepts generated-book target languages from book metadata, avoids source-language destination pills, keeps translation-only timing on the active audio lane, and refreshes paused lookup definitions from every arrow-key word navigation path."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-template-application-helper",
                    title: "YouTube templates apply cleaner",
                    detail: "Apple Create now resolves saved YouTube Dub template source, language, timing, model, tuning, output, and lookup settings through the shared template settings helper before applying them to the native form."
                ),
                AppChangelogEntry(
                    id: "reader-target-language-authoritative-fields",
                    title: "Destination pills avoid stale metadata",
                    detail: "Interactive Reader now resolves destination language pills from authoritative job target fields and known request/config containers instead of broad nested metadata scans that could surface an unrelated book language."
                ),
                AppChangelogEntry(
                    id: "reader-single-track-combined-sync",
                    title: "Translation-only playback stays aligned",
                    detail: "When Original is disabled on a combined-track book, Apple playback now treats the active audio role and timing as translation-only so the header, slider, rendered sentence, and narration stay together."
                ),
                AppChangelogEntry(
                    id: "ipad-paused-bubble-selection-lookup",
                    title: "Paused lookup arrows refresh directly",
                    detail: "Paused iPad lookup-bubble Left and Right keys now refresh definitions from the newly selected word directly, even when the bubble's local keyboard shortcut path handles the arrow event."
                ),
                AppChangelogEntry(
                    id: "reader-playback-language-sync-hardening",
                    title: "Reader track sync is tighter",
                    detail: "Interactive Reader now prefers target_languages metadata for destination pills, ignores stale selected audio tracks when Original or Translation is disabled, and refreshes paused lookup definitions from the exact word moved to by iPad arrow keys."
                ),
                AppChangelogEntry(
                    id: "reader-target-language-pill-source-fix",
                    title: "Reader language pills stay honest",
                    detail: "Apple playback now treats book_language as source metadata only, so the destination pill comes from target or translation fields instead of showing the source language for newly generated jobs."
                ),
                AppChangelogEntry(
                    id: "reader-text-audio-track-sync",
                    title: "Track toggles keep audio aligned",
                    detail: "When Original or Translation text tracks are hidden, Apple playback now aligns the narration audio mode to the visible track and clears stale lookup selections that pointed at hidden text."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-arrow-definition-refresh",
                    title: "Lookup arrows update definitions",
                    detail: "Paused iPad lookup-bubble Left and Right keys now refresh the definition immediately after moving the highlighted word instead of waiting for the delayed auto-lookup timer."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-bubble-arrow-dispatch-refresh",
                    title: "Lookup arrows refresh words",
                    detail: "Paused iPad lookup-bubble Left and Right keys now route through the bubble word-navigation path across UIKit, SwiftUI, app-command, and hardware-keyboard fallback sources, so the highlighted word and lookup definition advance together."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-bubble-local-arrow-shortcuts",
                    title: "iPad bubble arrows are steadier",
                    detail: "The lookup bubble now owns local iPad Left and Right keyboard shortcuts too, so paused word navigation keeps working even when the bubble itself has hardware-keyboard focus."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-keyboard-fallback-mounted",
                    title: "iPad lookup arrows work",
                    detail: "Interactive Reader now mounts the SwiftUI hardware-keyboard fallback layer, so plain Left and Right move the highlighted lookup word while paused even after the lookup bubble or other controls shift focus."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-keyboard-debug-breadcrumbs",
                    title: "iPad keyboard debugging is clearer",
                    detail: "DEBUG builds now record Interactive Reader shortcut dispatch and word-selection breadcrumbs, making future physical-iPad hardware-key regressions traceable from device logs."
                ),
                AppChangelogEntry(
                    id: "ipad-video-keyboard-fallback-layer",
                    title: "Video lookup keys match books",
                    detail: "iPad video playback now has its own hardware-keyboard fallback layer, keeping paused lookup bubble previous/next word navigation aligned with Interactive Reader."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-tab-content-component",
                    title: "Subtitle tabs render cleaner",
                    detail: "Web Subtitle Tool now routes source, options, tuning, metadata, and jobs tabs through a focused tab-content component with coverage that preserves the shared submit form for Apple parity work."
                ),
                AppChangelogEntry(
                    id: "video-footer-slider-stays-hidden",
                    title: "Video keeps one scrubber",
                    detail: "Video playback now keeps the shared footer slider out of the video surface and drops stale overlay scrubber bindings, leaving iPhone and iPad to the native player timeline."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-creation-defaults-hook",
                    title: "Subtitle defaults load cleaner",
                    detail: "Web Subtitle Tool now loads backend creation defaults through a focused hook with coverage for template/prefill skips, failures, and late responses before Apple parity checks reuse the form."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-template-save-hook",
                    title: "Subtitle templates save cleaner",
                    detail: "Web Subtitle Tool now saves reusable subtitle creation templates through a focused hook with coverage for validation, sanitized payloads, and save-error state before Apple Create reuse."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-template-handoff-hook",
                    title: "Subtitle templates apply cleaner",
                    detail: "Web Subtitle Tool now applies saved creation-template handoffs through a focused hook with coverage for compatible templates, incompatible templates, and metadata draft replacement before Apple reuse."
                ),
                AppChangelogEntry(
                    id: "apple-template-selection-helper",
                    title: "Create templates select cleaner",
                    detail: "Apple Create now resolves saved-template picker display and refresh/delete fallback selection through the shared template helper, keeping native picker and Web handoff compatibility rules aligned."
                ),
                AppChangelogEntry(
                    id: "apple-web-handoff-template-filter",
                    title: "Web handoff keeps matching templates",
                    detail: "Apple Create now resolves the selected Web handoff template through the shared template helper, so stale ids from another Create mode are not added to Open Web Create links."
                ),
                AppChangelogEntry(
                    id: "apple-template-discovery-apply-helper",
                    title: "Templates restore discovery cleaner",
                    detail: "Apple Create now restores saved book discovery state through the shared template helper, keeping source-panel selection and catalog metadata extras aligned with Web templates."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-completion-helper",
                    title: "Download handoff reconnects cleaner",
                    detail: "Apple Create now matches completed Download Station tasks back to refreshed manual-download videos through a shared helper that reads top-level completed files and older metadata hints."
                ),
                AppChangelogEntry(
                    id: "video-ios-native-scrubber-only",
                    title: "Video uses the native scrubber",
                    detail: "iPhone and iPad video playback now hides the custom overlay timeline pill when native AVPlayer controls are available, avoiding duplicate progress controls."
                ),
                AppChangelogEntry(
                    id: "create-api-backed-splitter-picker",
                    title: "Create uses backend splitter labels",
                    detail: "Web and Apple Create now build sentence-splitter pickers from the backend capability contract, with local fallbacks for older options payloads."
                ),
                AppChangelogEntry(
                    id: "create-readiness-splitter-capabilities",
                    title: "Create preflight checks splitters",
                    detail: "Apple Create readiness now validates the backend sentence splitter capability contract, including supported modes, cache versions, and no-skip comparison metric fields."
                ),
                AppChangelogEntry(
                    id: "create-options-splitter-capabilities",
                    title: "Create advertises splitter capabilities",
                    detail: "The shared Create options payload now includes supported sentence splitter modes, cache versions, and comparison metric keys so Web and Apple can dogfood splitter quality from the same backend contract."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-contiguous-coverage",
                    title: "Splitter checks skipped text",
                    detail: "Backend sentence-splitter dry runs now report contiguous source-span coverage, skipped text, and unmatched sentence counts so modern splitter trials can catch no-skip/no-overlap regressions before reader jobs are created."
                ),
                AppChangelogEntry(
                    id: "apple-auth-runtime-contract",
                    title: "Auth routes join preflight",
                    detail: "Apple Settings now validates login, OAuth, session, and token-transport runtime metadata, and Create readiness checks auth descriptor drift before simulator or device runs."
                ),
                AppChangelogEntry(
                    id: "tvos-video-native-scrubber-only",
                    title: "Video uses native scrubbing",
                    detail: "Video playback no longer draws custom footer or header progress controls over native Apple video transport, keeping remote focus on playback buttons, captions, bookmarks, and segment status."
                ),
                AppChangelogEntry(
                    id: "apple-playback-media-linguist-runtime-contract",
                    title: "Playback routes join preflight",
                    detail: "The public runtime descriptor now advertises Apple playback media, timing, lookup-cache, assistant lookup, and audio synthesis routes, and Settings validates them before simulator or device use."
                ),
                AppChangelogEntry(
                    id: "apple-pipeline-jobs-runtime-contract",
                    title: "Jobs routes join preflight",
                    detail: "The public runtime descriptor now advertises Apple Jobs list, status, live update, delete, and restart routes, and Settings validates them before simulator or device use."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jumps-wait-for-transcript",
                    title: "Reader jumps keep text and audio together",
                    detail: "Interactive Reader sentence jumps now wait for renderable chunk metadata before preparing audio, so iPad and iPhone no longer keep the loading wheel visible while the jumped sentence is already playing."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-tv-slider-scrubs",
                    title: "TV slider scrubs sentences",
                    detail: "Apple TV Interactive Reader now consumes left and right remote presses while the footer progress slider is focused, moving the sentence slider instead of falling through to previous or next word highlighting."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-metadata-sanitizer",
                    title: "Create templates stay token-free",
                    detail: "Apple Create now strips token, password, secret, authorization, and API-key metadata extras before they can be saved into Narrate EPUB or generated-book templates."
                ),
                AppChangelogEntry(
                    id: "apple-job-event-stream-route-helper",
                    title: "Job live updates share routes",
                    detail: "Apple job live-update streams now use the shared pipeline job runtime route helper and encoded job-id path contract instead of carrying an inline events URL."
                ),
                AppChangelogEntry(
                    id: "apple-create-immediate-epub-import",
                    title: "Create imports EPUBs sooner",
                    detail: "Apple Create now uploads a chosen local EPUB into the shared server EPUB folder immediately, refreshes the server picker, and submits Narrate EPUB jobs using the uploaded backend path."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-dense-token-taps",
                    title: "Dense text taps are steadier",
                    detail: "Interactive Reader now treats near-token taps on dense iPhone and iPad text as word taps, preserving seek and lookup behavior instead of letting those taps fall through as background playback toggles."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-tv-progress-focus",
                    title: "TV reader progress focus is explicit",
                    detail: "Apple TV Interactive Reader now has a dedicated progress focus area, so pressing down from the transcript can reach the sentence footer while Video keeps its existing native overlay scrubber focus path."
                ),
                AppChangelogEntry(
                    id: "iphone-reader-progress-footer-hide",
                    title: "iPhone reader progress gets out of the way",
                    detail: "Interactive Reader now keeps the full sentence slider hidden on iPhone until it is surfaced from a compact progress pill, reserves bottom transcript space while it is visible, keeps renderable tracks visible during slider jumps, and lets the slider be dismissed after seeking."
                ),
                AppChangelogEntry(
                    id: "tvos-video-single-scrubber",
                    title: "Video keeps one scrubber",
                    detail: "Video playback on Apple devices now uses the native player scrubber without also drawing the shared bottom footer, removing duplicate timeline controls."
                ),
                AppChangelogEntry(
                    id: "cross-surface-progress-footer",
                    title: "Progress stays handy",
                    detail: "Interactive Reader now keeps its thin sentence progress footer across iPhone, iPad, Apple TV, and Mac Designed for iPad, while video playback stays with the native scrubber."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-tightened",
                    title: "Reader header is tighter",
                    detail: "The Interactive Reader identity header now keeps title, author, category/type, and model metadata on one compact line where possible, with sentence scrubbing kept in the footer."
                ),
                AppChangelogEntry(
                    id: "now-playing-resume-existing",
                    title: "Now Playing returns in place",
                    detail: "Return to Now Playing now reopens the active book or job in a resume-only continue mode, so it resumes the rendered position when available instead of falling back to the beginning."
                ),
                AppChangelogEntry(
                    id: "apple-music-reading-bed-requested-playback",
                    title: "Apple Music follows narration",
                    detail: "Apple Music background beds now resume as soon as sentence playback is requested, covering startup and track-switch timing while still respecting manually paused music."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-overlay-pause-transition",
                    title: "TV return and pause are tighter",
                    detail: "Apple TV now shows a focused bottom Now Playing return overlay after backing out of playback, and interactive sentence track switches respect a pause made while the next track is loading."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-time-abbreviation-losslessness",
                    title: "Book sentence splitting is safer",
                    detail: "Backend book splitting now treats a.m. and p.m. as sentence endings only before clear new sentences, keeps lowercase continuations together, and invalidates refined caches with splitter version regex-v8."
                ),
                AppChangelogEntry(
                    id: "apple-runtime-preflight-playback-return",
                    title: "Preflight and playback return tighten",
                    detail: "Apple Create readiness now checks Library action, offline export, playback-state, and notification runtime contracts; Apple TV keeps Return to Now Playing in the browse list; Apple Music reading-bed sentence switches respect paused music."
                ),
                AppChangelogEntry(
                    id: "apple-offline-export-download-route-helper",
                    title: "Offline export route is ready",
                    detail: "Apple offline-export downloads now have a shared helper for the advertised runtime template, keeping future native download handling aligned with Settings and Create-readiness preflight."
                ),
                AppChangelogEntry(
                    id: "apple-create-route-template-helpers",
                    title: "Create routes align with preflight",
                    detail: "Saved-template detail routes and acquisition job polling now substitute the same Create runtime templates that Settings validates before Apple Create journeys run."
                ),
                AppChangelogEntry(
                    id: "apple-library-metadata-route-templates",
                    title: "Library metadata routes align",
                    detail: "Apple Library item edits, source uploads, ISBN apply, and metadata enrichment now substitute the same runtime route templates that Settings validates before simulator or device use."
                ),
                AppChangelogEntry(
                    id: "apple-library-media-file-route-helper",
                    title: "Library media routes share helpers",
                    detail: "Apple playback and offline sync now build and parse Library media file URLs through the shared media route contract, keeping encoded asset paths consistent across iPhone, iPad, Apple TV, and local Mac."
                ),
                AppChangelogEntry(
                    id: "apple-music-toggle-play-intent",
                    title: "Music toggle follows play intent",
                    detail: "Turning Background Music back on with Apple Music selected now uses the same play-requested guard as sentence switches, so paused readers stay quiet until narration resumes."
                ),
                AppChangelogEntry(
                    id: "apple-notification-runtime-contract",
                    title: "Notification routes join preflight",
                    detail: "Notification device registration, device removal, test notification, rich-test notification, and preference endpoints now appear in the public Apple runtime contract and use shared Apple route helpers."
                ),
                AppChangelogEntry(
                    id: "apple-auth-reading-bed-runtime-contract",
                    title: "Auth and reading-bed routes join preflight",
                    detail: "OAuth login and reading-bed catalog paths now appear in the public Apple runtime contract, and Apple auth, session, runtime descriptor, bookmark, resume, and reading-bed calls use shared route helpers for stronger drift checks."
                ),
                AppChangelogEntry(
                    id: "apple-media-linguist-route-contracts",
                    title: "Playback routes share helpers",
                    detail: "Apple playback media, timing, subtitle metadata, lookup-cache, assistant lookup, and audio synthesis endpoints now use shared route helpers so iPhone, iPad, Apple TV, and local Mac avoid inline API string drift."
                ),
                AppChangelogEntry(
                    id: "apple-job-library-action-runtime-contract",
                    title: "Job and Library actions join preflight",
                    detail: "Apple Jobs and Library move/remove endpoints now live in shared runtime contract helpers and the public backend descriptor, so Settings and readiness checks catch action route drift before simulator or device deployment."
                ),
                AppChangelogEntry(
                    id: "apple-runtime-descriptor-payload-check-full-create",
                    title: "Runtime payload check is stricter",
                    detail: "The standalone Swift runtime-descriptor payload check now mirrors the backend camelCase descriptor and decodes every advertised Create route, so descriptor additions stay covered by the shared Apple contract lane."
                ),
                AppChangelogEntry(
                    id: "apple-media-search-runtime-contract",
                    title: "Playback search contract shared",
                    detail: "The backend runtime descriptor now advertises the media-search endpoint used by Apple playback, and Apple Create readiness validates the full Create route contract before simulator journeys run."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-return-selector",
                    title: "TV Now Playing return is testable",
                    detail: "The Apple TV floating Now Playing dock now exposes the same Return to Now Playing automation target as the browse strip, keeping the Back/Menu return path visible and covered by unattended playback journeys."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-bullet-unicode-starts",
                    title: "Sentence splitting keeps more text",
                    detail: "Book sentence splitting now preserves leading bullet markers, recognizes Unicode lowercase starts after terminal punctuation, and invalidates refined sentence caches with splitter version regex-v7."
                ),
                AppChangelogEntry(
                    id: "apple-chapter-jumps-keep-play-intent",
                    title: "Chapter jumps keep playback intent",
                    detail: "Apple chapter menu and range-selector jumps now preserve requested playback during sentence transitions, matching Search, Bookmarks, and the header progress slider across iPhone, iPad, Apple TV, and local Mac."
                ),
                AppChangelogEntry(
                    id: "apple-music-disabled-source-stays-idle",
                    title: "Music stays idle when off",
                    detail: "Selecting Apple Music as the reading-bed source no longer claims playback mixing or Now Playing ownership while Background Music is off, keeping paused sentence switches quiet until music is enabled again."
                ),
                AppChangelogEntry(
                    id: "apple-music-external-pause-intent",
                    title: "Music respects external pauses",
                    detail: "Apple Music reading-bed playback now treats Control Center or lock-screen pauses as manual pause intent, so sentence switches do not restart music until the user resumes it."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-mini-return",
                    title: "TV gets a Now Playing mini control",
                    detail: "Apple TV now keeps a compact Now Playing return control floating in the browse shell after backing out of playback, while the existing return strip remains available for list-based journeys."
                ),
                AppChangelogEntry(
                    id: "apple-api-path-component-encoding",
                    title: "Apple routes encode IDs safely",
                    detail: "Apple playback, Library, media, lookup, event-stream, and notification calls now encode path components with route separators escaped, matching the safer Web and template handoff behavior."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-search-return",
                    title: "Search keeps Now Playing nearby",
                    detail: "The iPad and Mac-style Search surface now keeps the Return to Now Playing strip visible after leaving playback, so the active job or library item has a direct return action."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-menu-return",
                    title: "TV menu shows Now Playing",
                    detail: "Apple TV now shows the Return to Now Playing row at the top of the browse menu after backing out of playback, giving the remote a direct focused path back to the active item."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-completed-file-message",
                    title: "Apple download completion names files",
                    detail: "Apple Create now names completed Download Station files from the same top-level and metadata fallback hints used by Web, so the handoff panel and status message agree."
                ),
                AppChangelogEntry(
                    id: "web-download-station-metadata-fallback",
                    title: "Web downloads use fallback hints",
                    detail: "Web Video Dubbing now reads Download Station completed-file hints from acquisition job metadata, matching the Apple fallback path when top-level status fields are missing."
                ),
                AppChangelogEntry(
                    id: "download-station-completed-file-metadata",
                    title: "Downloads reconnect consistently",
                    detail: "Completed Download Station file hints now appear in acquisition job metadata as well as status fields, giving Web and Apple Create the same fallback path for finished downloads."
                ),
                AppChangelogEntry(
                    id: "apple-music-auto-resume-play-intent",
                    title: "Music follows play intent",
                    detail: "Apple Music used as the reading bed now auto-resumes only when narration playback is still requested and active, so paused jumps and sentence switches do not restart music unexpectedly."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-job-metadata-hints",
                    title: "Downloads reconnect more reliably",
                    detail: "Apple Create now preserves Download Station job metadata and uses safe completed-file hints as a fallback when matching finished downloads back to manual video discovery."
                ),
                AppChangelogEntry(
                    id: "apple-create-readiness-discovery-route",
                    title: "Create checks discovery search",
                    detail: "Apple Create readiness now makes bounded book and video discovery calls against backend-owned default providers, validating response shape before simulator or device journeys start."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-return-overlay",
                    title: "TV can return to Now Playing",
                    detail: "Apple TV now keeps a floating Now Playing return control in the browse shell after backing out of playback, giving the current job or library item a direct re-entry point."
                ),
                AppChangelogEntry(
                    id: "apple-create-readiness-acquisition-defaults",
                    title: "Create checks discovery defaults",
                    detail: "Apple Create readiness now validates backend-owned book and video acquisition default provider ids before simulator or device journeys start."
                ),
                AppChangelogEntry(
                    id: "web-narrate-discovery-provider-helper",
                    title: "Discovery provider checks are focused",
                    detail: "Web Narrate Ebook discovery-provider ordering, availability messages, and backend default selection now live in a focused helper covered by the shared Create-intake pipeline gate."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-default-selection",
                    title: "Discovery defaults drive Create",
                    detail: "Web and Apple Create now adopt backend-owned default book and video discovery providers for the initial picker choice while keeping any provider the user selects manually."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-defaults",
                    title: "Discovery defaults are shared",
                    detail: "The acquisition provider API now advertises backend-owned default book and video discovery providers so Web and Apple Create can stay aligned with server behavior."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-discovery-media-kinds",
                    title: "Discovery providers are clearer",
                    detail: "The backend now marks which acquisition providers support book or video discovery, and Web plus Apple Create prefer that shared contract before falling back to older capability hints."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-return-command",
                    title: "Now Playing return is clearer",
                    detail: "Apple browse surfaces now label the Now Playing control as a return action and use an action-oriented symbol so the path back to active playback is easier to spot."
                ),
                AppChangelogEntry(
                    id: "apple-pause-safe-sequence-transitions",
                    title: "Paused playback stays paused",
                    detail: "Apple sentence-sequence transitions now respect the current pause intent across dwell, track switches, and direct jumps, keeping narration and Apple Music from restarting unexpectedly."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-return-focus",
                    title: "Now Playing stays reachable",
                    detail: "Apple browse surfaces now remember the active playback target and refocus the Now Playing return control on Apple TV after backing out of playback."
                ),
                AppChangelogEntry(
                    id: "apple-resume-menu-freshest-entry",
                    title: "Resume actions match the badge",
                    detail: "Apple Library, Jobs, and search menus now choose the freshest local or cloud resume point, matching the resume badge shown on the row."
                ),
                AppChangelogEntry(
                    id: "apple-create-shared-draft-submit",
                    title: "Create drafts stay consistent",
                    detail: "Apple Create submission and template saving now use the same current draft builders for generated books, Narrate EPUB, subtitles, and YouTube Dub jobs, including video discovery metadata."
                ),
                AppChangelogEntry(
                    id: "apple-cross-surface-now-playing-return",
                    title: "Now Playing return is cross-surface",
                    detail: "The browse shell now shows a Now Playing return strip on compact iPhone/iPad, Mac-style, and Apple TV surfaces when playback is active and you navigate away."
                ),
                AppChangelogEntry(
                    id: "apple-create-settings-content-refactor",
                    title: "Create settings are easier to evolve",
                    detail: "Apple Create now keeps mode-specific settings section ordering in a dedicated SwiftUI view, making the shared iPhone, iPad, Mac-style, and TV creation surface safer to keep aligned."
                ),
                AppChangelogEntry(
                    id: "cross-surface-manifest-gate",
                    title: "Checkpoint mirrors shared manifest",
                    detail: "The repo-owned cross-surface checkpoint now runs the full shared backend slice set, focused Web checks, full Vitest, Web builds, and Apple local-surface verification before safe checkpoints."
                ),
                AppChangelogEntry(
                    id: "cross-surface-library-playback-gate",
                    title: "Checkpoint covers playback surfaces",
                    detail: "The repo-owned cross-surface checkpoint now includes Library, playback, Sidebar, Job Progress, and app-view checks alongside Create, video, subtitle, Web build, and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "cross-surface-subtitle-video-gate",
                    title: "Checkpoint covers video and subtitles",
                    detail: "The repo-owned cross-surface checkpoint now covers backend subtitle and YouTube dubbing slices plus focused Web Video Dubbing and Subtitle Tool tests before Web builds and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "apple-music-pause-now-playing-return",
                    title: "Music pause and TV return improve",
                    detail: "Apple Music used as the reading bed now respects a manual pause across sentence transitions, and Apple TV shows a Now Playing return control above the browse menu for the current job or library item."
                ),
                AppChangelogEntry(
                    id: "apple-deploy-stable-artifact-guard",
                    title: "Device deploys handle stale artifacts",
                    detail: "Unattended Apple deploys now verify stable signed artifacts before CoreDevice preflight or install, and locked-device launch denials after a verified install are reported without failing the deploy."
                ),
                AppChangelogEntry(
                    id: "cross-surface-backend-create-gate",
                    title: "Cross-surface gate covers backend Create",
                    detail: "The repo-owned cross-surface checkpoint now runs backend creation-template and acquisition route tests before the Web Create checks, Web build, and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "cross-surface-web-create-gate",
                    title: "Cross-surface gate covers Web Create",
                    detail: "The repo-owned cross-surface checkpoint now runs focused Web Create intake and saved-template tests before the Web build and Apple local-surface verification."
                ),
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
                    id: "ipad-lookup-arrow-space-reliability",
                    title: "iPad keyboard playback controls are steadier",
                    detail: "Paused lookup bubbles now keep Left/Right and Ctrl+Left/Ctrl+Right on word navigation before sentence transport, while Space remains on the shared play/pause dispatch path after lookup read-aloud focus changes."
                ),
                AppChangelogEntry(
                    id: "apple-video-discovery-prepared-selection",
                    title: "Video discovery uses prepared sources",
                    detail: "Apple YouTube Dub now prepares NAS and manual video discovery candidates through the shared acquisition artifact endpoint before filling video and subtitle paths, matching the safer Narrate EPUB handoff."
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
                    id: "apple-create-youtube-template-discovery-paths",
                    title: "Create templates restore videos",
                    detail: "Apple Create YouTube Dub templates now fall back to saved discovery-state video and subtitle paths, so Web-authored discovery templates reopen with the intended NAS selections."
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
