extension AppChangelogData {
    static let june27Entries: [AppChangelogEntry] = [
                AppChangelogEntry(
                    id: "apple-pipeline-helper-e2e-preflight-guard",
                    title: "Apple pipeline guards preflight tests",
                    detail: "The shared Apple pipeline helper now checks that E2E config preflight parser tests stay in the Apple contract gate, and TV Music-bed notes name the remote Play/Pause assertion."
                ),
                AppChangelogEntry(
                    id: "apple-e2e-config-preflight-contract",
                    title: "Apple E2E preflight stays guarded",
                    detail: "The regular Apple contract gate now runs the E2E config preflight parser tests, so reusable pipeline checks cover credential and API URL validation before simulator journeys launch."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-remote-e2e",
                    title: "TV remote pause is covered",
                    detail: "The Apple TV Music-bed simulator journey now presses the remote Play/Pause button after the bed is playing and verifies one press pauses and resumes both sentence narration and Apple Music."
                ),
                AppChangelogEntry(
                    id: "apple-e2e-config-preflight",
                    title: "Apple E2E config fails faster",
                    detail: "iPhone, iPad, and Apple TV simulator journeys now validate E2E credentials and API URL before launching Xcode, so missing configuration stops with a clear token-safe message."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-sync-e2e",
                    title: "TV music bed sync is tested",
                    detail: "The Apple TV simulator pipeline now has a dedicated Music-bed journey that opens a Library book, simulates MusicKit pause/play observations, and verifies sentence playback mirrors the bed."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-scene-reassert",
                    title: "TV reader reclaims Music surfaces",
                    detail: "Job and Library playback now reassert reader Now Playing ownership on scene phase changes while Apple Music is only the reading bed, reducing fullscreen Music artwork takeovers."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-resumes-after-reader-pause",
                    title: "TV music bed resumes with reader",
                    detail: "Apple Music pauses mirrored from the TV remote now remember that they came from reader transport, so resuming narration can bring the Music bed back instead of leaving only sentence audio playing."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-external-pause-mirrors-reader",
                    title: "TV remote pause stops the reader",
                    detail: "When tvOS routes the first remote pause to Apple Music while it is only the reading bed, book playback now mirrors that external Music pause to narration so one press stops both layers."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-transport-stays-reader-owned",
                    title: "TV Music bed follows reader controls",
                    detail: "Apple TV book playback now registers reader transport commands on both the sentence player session and shared media command center, so play/pause targets narration and the Apple Music bed together instead of letting Music take over fullscreen playback."
                ),
                AppChangelogEntry(
                    id: "apple-create-source-section-factory-split",
                    title: "Create source setup is isolated",
                    detail: "Apple Create now builds the EPUB, subtitle, YouTube, discovery, and Download Station source setup pane from a focused source-section factory extension."
                ),
                AppChangelogEntry(
                    id: "apple-create-derived-state-split",
                    title: "Create derived state is isolated",
                    detail: "Apple Create now keeps language inventories, voice options, model lists, tuning labels, and duration estimates in a focused derived-state extension."
                ),
                AppChangelogEntry(
                    id: "apple-create-metadata-action-wrappers-split",
                    title: "Create metadata actions are isolated",
                    detail: "Apple Create now keeps metadata lookup, cache clearing, voice preview, image-node checks, and retry callbacks in a focused view extension so the main screen stays layout-oriented."
                ),
                AppChangelogEntry(
                    id: "apple-create-view-model-template-actions-split",
                    title: "Create templates are isolated",
                    detail: "Apple Create now keeps saved-template loading, saving, deleting, cache invalidation, and status messages in a focused view-model extension."
                ),
                AppChangelogEntry(
                    id: "apple-create-view-model-source-actions-split",
                    title: "Create source loading is isolated",
                    detail: "Apple Create now keeps source discovery, Download Station, server EPUB/subtitle updates, NAS subtitle extraction, and chapter loading in a focused view-model extension."
                ),
                AppChangelogEntry(
                    id: "apple-create-source-actions-split",
                    title: "Create source actions are isolated",
                    detail: "Apple Create now keeps server EPUB, subtitle, YouTube discovery, Download Station, and source-delete side effects in a focused extension while preserving the same Create source controls."
                ),
                AppChangelogEntry(
                    id: "web-player-stacked-controls-split",
                    title: "Web player controls are easier to tune",
                    detail: "The Web interactive reader's legacy stacked advanced controls now live in a focused tested component, keeping the player navigation shell smaller before the next cross-surface playback polish pass."
                ),
                AppChangelogEntry(
                    id: "library-apple-music-lock-screen-parity",
                    title: "Library playback respects Music ownership",
                    detail: "Library book playback now matches job playback when Apple Music is the foreground lock-screen owner while still reasserting reader sentence controls when Music is only the reading bed."
                ),
                AppChangelogEntry(
                    id: "apple-create-control-bindings-split",
                    title: "Create control bindings are isolated",
                    detail: "Apple Create now keeps clamped output values and reusable state bindings in a focused extension, reducing the main Create view while preserving edited-field tracking."
                ),
                AppChangelogEntry(
                    id: "apple-create-metadata-bindings-split",
                    title: "Create metadata bindings are isolated",
                    detail: "Apple Create now keeps YouTube and subtitle media metadata JSON binding adapters in a focused extension, leaving the main Create view centered on layout and orchestration."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-session-reassert-after-resume",
                    title: "Reader reasserts after Music resumes",
                    detail: "Apple Music reading-bed play and resume now emit delayed surface revisions, and Job/Library playback explicitly reactivates the reader Now Playing session after publishing sentence metadata and transport state."
                ),
                AppChangelogEntry(
                    id: "apple-create-draft-actions-split",
                    title: "Create draft builders are isolated",
                    detail: "Apple Create now keeps generated-book, Narrate EPUB, subtitle, and YouTube Dub state-to-draft builders in a focused extension while preserving the same submit and template-save payloads."
                ),
                AppChangelogEntry(
                    id: "apple-create-options-actions-split",
                    title: "Create defaults apply in one place",
                    detail: "Apple Create now keeps backend option loading, stored language preference application, and default state assignment in a focused extension while preserving edited-field behavior."
                ),
                AppChangelogEntry(
                    id: "apple-create-history-actions-split",
                    title: "Create history defaults are isolated",
                    detail: "Apple Create now keeps recent-job default application for generated-book, Narrate EPUB, subtitle, and YouTube Dub modes in a focused extension while preserving the same edited-field guards."
                ),
                AppChangelogEntry(
                    id: "reader-now-playing-public-state",
                    title: "Reader states Control Center playback",
                    detail: "Interactive book playback now publishes the reader sentence player's public Now Playing playback state to both the default media center and its MPNowPlayingSession, giving Control Center a stronger signal than metadata alone while Apple Music is used as the bed."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-application-split",
                    title: "Create template application is isolated",
                    detail: "Apple Create now keeps the detailed Web-template application engine in a focused extension, leaving the main Create view centered on state and layout wiring."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-actions-split",
                    title: "Create templates are easier to maintain",
                    detail: "Apple Create now keeps saved-template refresh, save, apply, and delete orchestration in a focused extension while preserving the same Web-template reuse behavior."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-surface-reassert",
                    title: "Music bed no longer steals Control Center",
                    detail: "Apple Music reading-bed playback now signals every MusicKit playback-surface change so Job and Library playback can immediately reassert the reader sentence track in Control Center."
                ),
                AppChangelogEntry(
                    id: "apple-create-import-actions-split",
                    title: "Create imports are easier to maintain",
                    detail: "Apple Create now keeps local EPUB/subtitle import handling and server EPUB upload handoff in a focused file while preserving the same picker and source-selection behavior."
                ),
                AppChangelogEntry(
                    id: "apple-create-submit-actions-split",
                    title: "Create submit actions are clearer",
                    detail: "Apple Create now keeps generated-book, Narrate EPUB, subtitle, and YouTube Dub submit actions in a focused extension while preserving the same draft builders and shared submission wrapper."
                ),
                AppChangelogEntry(
                    id: "apple-create-presentation-state-split",
                    title: "Create view state is slimmer",
                    detail: "Apple Create now keeps submit eligibility, template picker state, Web handoff URLs, and source-label presentation wiring in a focused extension instead of the main Create view."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-control-center-autoplay",
                    title: "Autoplay reclaims Control Center",
                    detail: "When narration autoplay starts while Apple Music is the bed, book playback now forces a fresh reader Now Playing snapshot on the active sentence player so Control Center prefers the sentence track instead of the Music song."
                ),
                AppChangelogEntry(
                    id: "apple-create-preferences-split",
                    title: "Create preferences are easier to maintain",
                    detail: "Apple Create now keeps source-selection and language preference scope wiring in the shared preferences helper, shrinking the main Create view without changing remembered defaults."
                ),
                AppChangelogEntry(
                    id: "shared-pipeline-dry-runs-dogfooded",
                    title: "Shared Apple pipeline dry-runs verified",
                    detail: "The reusable Apple pipeline contract runner and orchestration dry-runs were dogfooded for ebook-tools, confirming simulator smoke commands and all app-owned journey profiles expand without touching physical devices."
                ),
                AppChangelogEntry(
                    id: "gitignore-changes-run-makefile-contract",
                    title: "Tracked artifact rules get tested",
                    detail: "The changed-test selector now sends .gitignore edits through the makefile contract lane, keeping offline export bundle tracking and shared build wiring covered during source-sync checkpoints."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-now-playing-live-reassert",
                    title: "Reader keeps Control Center during Music",
                    detail: "Apple Music reading-bed playback now keeps reasserting reader Now Playing metadata while narration or the Music bed is active, and active iPad view handoffs no longer clear sentence controls prematurely."
                ),
                AppChangelogEntry(
                    id: "export-player-check-joins-build-target",
                    title: "Export checks run with Web builds",
                    detail: "The Web production build target now runs the offline export bundle contract after Vite finishes, and the changed-test selector treats that contract as part of the makefile pipeline gate."
                ),
                AppChangelogEntry(
                    id: "export-player-bundle-tracked",
                    title: "Offline export bundle stays intact",
                    detail: "The Web production/export gate now keeps the tracked offline player HTML tied to a present export JavaScript bundle, so default offline exports do not point at ignored build output after source sync."
                ),
                AppChangelogEntry(
                    id: "video-default-sources-ignore-explicit-url",
                    title: "Video defaults stay deliberate",
                    detail: "Web Video Dubbing and Apple YouTube Dub now ignore explicit YouTube URL handoff entries when choosing backend default video sources, keeping pasted-link lookup separate from blind NAS/manual/search discovery."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-reasserts-reader-session",
                    title: "Reader reclaims Control Center",
                    detail: "When Apple Music starts as the reading bed, Job and Library playback now reassert the narration spoken-audio session before publishing the reader Now Playing snapshot so Control Center has the sentence player as the active owner."
                ),
                AppChangelogEntry(
                    id: "reader-now-playing-session",
                    title: "Reader asks for active Now Playing session",
                    detail: "Interactive book playback now binds the active sentence AVPlayer to an MPNowPlayingSession and logs whether iOS lets that reader session become active while Apple Music is used as the bed."
                ),
                AppChangelogEntry(
                    id: "apple-music-station-queue-restore",
                    title: "Remembered Apple Music stations resume",
                    detail: "Apple Music reading-bed restore now reloads the persisted catalog queue before play or auto-resume, so a remembered station label no longer leaves MusicKit with nothing playable."
                ),
                AppChangelogEntry(
                    id: "reader-now-playing-public-transport-metadata",
                    title: "Control Center handoff avoids private state",
                    detail: "Reader Now Playing now relies on public transport metadata, elapsed time, playback rate, and remote commands instead of the MediaRemote playback-state setter that iOS ignores without private entitlement."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-ownership-device-logs",
                    title: "Control Center testing gets clearer logs",
                    detail: "Device launch logs now record reader Now Playing transport metadata, remote-command ownership, and Apple Music bed handoffs without exposing book text, titles, artists, or media URLs."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-spoken-now-playing-owner",
                    title: "Reader owns Control Center during music bed",
                    detail: "Apple Music reading-bed playback now keeps narration in a spoken-audio playback session and publishes reader transport metadata so Control Center can show the sentence track instead of the bed song."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-reader-now-playing-reassert",
                    title: "Reader stays in Control Center",
                    detail: "When Apple Music is playing as the reading bed, book playback now re-publishes sentence metadata after MusicKit playback and track changes so Control Center keeps targeting the reader."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-last-selection-restore",
                    title: "Apple Music bed reloads",
                    detail: "The last selected Apple Music song, album, artist, playlist, or station is remembered by MusicKit item identity and reloaded before narration resumes after relaunch."
                ),
                AppChangelogEntry(
                    id: "apple-music-low-mix-ducking",
                    title: "Apple Music mix has a quieter low end",
                    detail: "Low Apple Music reading-bed mix values now ask the audio session to duck system Music playback, while higher mixes keep the bed-forward behavior by lowering sentence narration around Music."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-reader-now-playing",
                    title: "Reader controls stay in Now Playing",
                    detail: "When Apple Music is used as the reading bed, sentence playback keeps the lock-screen and Control Center play, pause, seek, and bookmark controls instead of yielding them to the Music track."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-survives-active-reader-handoff",
                    title: "Apple Music keeps bedding active narration",
                    detail: "Apple Music remains an optional background bed under sentence narration during active reader navigation handoffs, while still stopping when narration playback intent is gone or Background Music is disabled."
                ),
                AppChangelogEntry(
                    id: "source-discovery-safe-root-stat",
                    title: "NAS source roots are steadier",
                    detail: "Backend source discovery now validates picker roots with the same tolerant stat path used for entries, and the shared backend pipeline runs the source-discovery regression suite before Apple or Web Create source pickers depend on it."
                ),
                AppChangelogEntry(
                    id: "apple-release-contract-in-apple-gate",
                    title: "Release checks join Apple gates",
                    detail: "The Apple contract lane now runs the release-version validator first, so latest-release builds catch plist, Xcode, Markdown changelog, in-app changelog, and visible version badge drift before simulator or device testing."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-neutral-mix",
                    title: "Apple Music stays under narration",
                    detail: "Apple Music is treated as an optional reading bed during sentence playback: queued tracks can resume as soon as narration is requested, while the reader keeps spoken-audio playback ownership so Music sits underneath."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-mix-autoplay-ranged-jobs",
                    title: "Apple Music follows bed playback",
                    detail: "Interactive Reader now starts ranged book jobs from the first loaded sentence instead of sentence one, and Apple Music reading-bed playback pauses, resumes, and mixes with narration through the same requested-playback logic as the built-in bed."
                ),
                AppChangelogEntry(
                    id: "dutch-only-gate-aware-skip-resolution",
                    title: "Dutch-only skips use visible gates",
                    detail: "Translation-only book playback now resolves the active sentence for skip controls through the same gate-aware sentence timing path used by rendering, keeping late-chapter Dutch navigation aligned with the displayed sentence."
                ),
                AppChangelogEntry(
                    id: "apple-create-provider-default-recovery",
                    title: "Create discovery defaults recover",
                    detail: "Apple Create now reapplies backend discovery defaults when the provider inventory changes before the user chooses a source, keeping book and video discovery pickers aligned with current backend readiness."
                ),
                AppChangelogEntry(
                    id: "ipad-keyboard-single-dispatch-autoplay",
                    title: "iPad keys dispatch once",
                    detail: "Interactive Reader now preserves keyboard duplicate guards while reclaiming focus, removes the lookup bubble's competing first-responder bridge, and honors late autoplay intents when an iPad playback pane is already mounted."
                ),
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
                    title: "Lookup bubble uses shared keyboard control",
                    detail: "Paused iPad lookup bubbles now rely on the shared player keyboard broker for Space, Enter, Left, and Right, so lookup focus follows the same route as the reader instead of owning a separate first responder."
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
                    id: "direct-youtube-url-discovery",
                    title: "YouTube URL review is explicit",
                    detail: "Web Video Dubbing and Apple YouTube Dub now show YouTube URL as its own discovery source, so pasted video links or ids go through the same reviewed metadata handoff as YouTube search without requiring the search API key."
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
                    detail: "iPad lookup Read Aloud now reactivates the shared keyboard broker when pronunciation starts or finishes while preserving duplicate guards during focus reclaim, so the first Left or Right press can keep moving lookup words without double-dispatching."
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
}
