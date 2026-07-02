extension AppChangelogData {
    static let july1Entries: [AppChangelogEntry] = [
                AppChangelogEntry(
                    id: "apple-changelog-july1-shard",
                    title: "July changelog history is slimmer",
                    detail: "Apple in-app changelog entries for July 1 now live in a dated shard, keeping the root changelog day index smaller while preserving the same device-visible release history."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-active-url-fallback",
                    title: "Single-track EOF handoffs hold",
                    detail: "Apple reader single-track EOF handoffs now preserve Original-only or Translation-only mode from the sole active audio URL when the system end callback loses its URL, while refusing to guess from multi-file combined queues."
                ),
                AppChangelogEntry(
                    id: "apple-video-discovery-presentation-helper",
                    title: "Video discovery is leaner",
                    detail: "Apple Create video discovery availability, provider options, YouTube metadata labels, candidate filtering, and template discovery-state shaping now live in a focused Swift helper, keeping YouTube Dub easier to compare with Web Video Dubbing."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-passive-mode-observation",
                    title: "Single-track handoffs hold",
                    detail: "Apple reader single-track mode now treats passive SwiftUI audio-mode observation as non-authoritative, so an end-of-batch or default refresh cannot clear the remembered Original-only or Translation-only lane and reset rendering out of sync."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-presentation-helper",
                    title: "Download handoff matching is leaner",
                    detail: "Apple Create Download Station completed-file extraction, metadata fallback hints, handoff detection, and refreshed discovery candidate matching now live in a focused Swift helper, keeping YouTube Dub downloader handoff behavior easier to compare with Web Video Dubbing."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-durable-lane-priority",
                    title: "Single-track batches keep their lane",
                    detail: "Apple reader original-only and translation-only playback now lets the durable selected lane beat stale SwiftUI audio-manager state at sentence-batch boundaries, so a transient reset to the wrong single track cannot desync rendering from narration."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-combined-phase-guard",
                    title: "Single-track batch rendering holds",
                    detail: "Apple reader single-track rendering now bypasses combined-phase timing whenever the durable original-only or translation-only lane is active, so hydrated batch boundaries cannot reset rendering away from the selected audio track."
                ),
                AppChangelogEntry(
                    id: "web-shared-voice-option-utils",
                    title: "Web voice options are shared",
                    detail: "Web Narrate Ebook and Video Dubbing now share focused tested voice-inventory option construction, keeping macOS, Piper, gTTS, and bundled voice filtering aligned for Apple Create parity."
                ),
                AppChangelogEntry(
                    id: "web-video-download-station-utils",
                    title: "Download handoff helpers are leaner",
                    detail: "Web Video Dubbing Download Station handoff detection, completed-file extraction, and refreshed NAS-video matching now live in a focused tested helper, keeping downloader handoff behavior easier to mirror in Apple YouTube Dub."
                ),
                AppChangelogEntry(
                    id: "web-video-source-panel-utils",
                    title: "Video discovery panel is leaner",
                    detail: "Web Video Dubbing source-panel discovery placeholders, hints, filename fallbacks, and candidate summary labels now live in a focused tested helper, keeping video discovery behavior easier to mirror in Apple Create."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-hydrated-chunk-reprepare",
                    title: "Single-track hydration stays in sync",
                    detail: "Apple reader single-track metadata hydration now prepares the refreshed chunk even when the selected Original or Translation audio option was already correct, so end-of-batch playback cannot keep a stale pre-hydration lane and drift rendering."
                ),
                AppChangelogEntry(
                    id: "web-narrate-image-settings-module",
                    title: "Narrate Ebook image settings are leaner",
                    detail: "Web Narrate Ebook image style options, prompt-pipeline options, quality slider mapping, and image-throughput estimates now live in a focused tested module, making image settings easier to mirror in Apple Create."
                ),
                AppChangelogEntry(
                    id: "web-narrate-image-node-hook",
                    title: "Narrate Ebook image controls are leaner",
                    detail: "Web Narrate Ebook Draw Things node availability checks now live in a focused hook with fallback-node and ordering coverage, keeping image generation controls lighter for cross-surface Create parity work."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-view-model-bridge",
                    title: "Single-track batches stay selected",
                    detail: "Apple reader single-track batch handoffs now restore the SwiftUI audio manager from the durable original-only or translation-only lane before default track setup runs, so hydrated sentence batches do not expand back to All and desync rendering."
                ),
                AppChangelogEntry(
                    id: "web-narrate-dialog-wrapper",
                    title: "Narrate Ebook dialogs are leaner",
                    detail: "Web Narrate Ebook file and discovery dialog wiring now lives in a focused rendered wrapper, keeping modal routing out of the main form coordinator while preserving source selection and search behavior."
                ),
                AppChangelogEntry(
                    id: "web-narrate-discovery-candidates-hook",
                    title: "Narrate Ebook discovery is leaner",
                    detail: "Web Narrate Ebook discovery candidate filtering now lives in the discovery hook with focused coverage, keeping backend-default source filtering out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-loaded-url-lane",
                    title: "Single-track batch ends stay selected",
                    detail: "Apple reader single-track playback now treats the loaded single audio URL as the durable lane during batch-end handoffs and rejects wrong-lane EOF callbacks before mutating selection state, preventing Original or Translation picker resets from drifting rendering."
                ),
                AppChangelogEntry(
                    id: "web-narrate-section-state-hook",
                    title: "Narrate Ebook sections are leaner",
                    detail: "Web Narrate Ebook section tabs and metadata overrides now resolve through the focused section-state hook, trimming the form coordinator while keeping Create step presentation covered."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-prefetch-lane",
                    title: "Single-track prefetch holds",
                    detail: "Apple reader adjacent-batch prefetch now treats the durable original-only or translation-only lane as authoritative and warms the selected stream inside combined-only batches, reducing batch-end races where rendering could reset away from the chosen audio track."
                ),
                AppChangelogEntry(
                    id: "web-narrate-workflow-refs-hook",
                    title: "Narrate Ebook workflow refs are leaner",
                    detail: "Web Narrate Ebook mutable workflow refs and user-edited-field preservation now live in a focused tested hook, keeping prefill, template, and default sentinels out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "web-narrate-normalized-state-hook",
                    title: "Narrate Ebook derived state is leaner",
                    detail: "Web Narrate Ebook normalized input metadata-cache keys and merged target-language state now live in a focused tested hook, trimming the main form coordinator while keeping template payloads aligned."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-header-role-lane",
                    title: "Single-track header roles hold",
                    detail: "Apple reader header audio-role pills now use the durable requested original-only or translation-only lane before transient SwiftUI manager state, so batch-boundary sequence blips do not show both tracks as active."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-playback-time-lane",
                    title: "Single-track batches stay in sync",
                    detail: "Apple reader original-only and translation-only playback time now follows the durable requested lane even if the SwiftUI audio manager briefly reports sequence mode at a sentence-batch boundary, preventing hidden-track offsets from drifting rendering."
                ),
                AppChangelogEntry(
                    id: "web-narrate-submit-flow-hook",
                    title: "Narrate Ebook submit flow is leaner",
                    detail: "Web Narrate Ebook submit orchestration now lives in a focused tested hook, keeping pipeline submit, intake refresh, and submit-button presentation together outside the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "web-narrate-image-defaults-hook",
                    title: "Narrate Ebook image defaults are leaner",
                    detail: "Web Narrate Ebook backend image-default application now lives in a focused tested hook, preserving edited image fields and rerun add-images choices while trimming the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-audio-picker-stamps-mode",
                    title: "Audio picker survives batches",
                    detail: "Apple reader audio-track picker selections now stamp the shared original-only or translation-only mode immediately, so stale sequence state cannot reset rendering at the next sentence batch."
                ),
                AppChangelogEntry(
                    id: "web-narrate-history-hook",
                    title: "Narrate Ebook history is leaner",
                    detail: "Web Narrate Ebook recent-job history callbacks now live in a focused tested hook, moving path normalization, previous-start lookup, and latest job defaults out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-durable-stamp",
                    title: "Single-track EOF keeps its lane",
                    detail: "Apple reader EOF handling now stamps the resolved original-only or translation-only lane before stale URL guards or next-batch selection run, tightening batch-boundary sync when the selected audio option briefly resets."
                ),
                AppChangelogEntry(
                    id: "web-narrate-discovery-selection-hook",
                    title: "Narrate Ebook discovery is leaner",
                    detail: "Web Narrate Ebook discovery candidate selection now lives in a focused tested hook, moving local/acquire/archive bridge, metadata-only handoff, and discovery-template provenance state out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-regression-gate",
                    title: "Single-track EOF fixes are guarded",
                    detail: "Apple playback regression gates now pin the reader EOF handoff and same-URL batch reuse contracts, so future changes preserve playback intent through sentence-batch transitions."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-intent-preserve",
                    title: "Single-track EOF handoffs hold intent",
                    detail: "Apple reader end-of-batch audio handoffs now keep playback intent alive until the next sentence batch is loaded or end-of-book pauses, preventing original-only or translation-only selection from briefly resetting."
                ),
                AppChangelogEntry(
                    id: "web-narrate-source-defaults-hook",
                    title: "Narrate Ebook source defaults are leaner",
                    detail: "Web Narrate Ebook generated-source sentence resets and forced output-name enforcement now run through a focused tested hook, moving source and output defaulting out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "web-narrate-prefill-hook",
                    title: "Narrate Ebook prefill is leaner",
                    detail: "Web Narrate Ebook prefilled input-file and rerun-parameter application now run through a focused tested hook, moving cached metadata hydration, history-derived starts, and edited-field preservation out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-same-url-lane-reassert",
                    title: "Single-track batches stay locked",
                    detail: "Apple reader single-track audio preparation now reasserts the active original-only or translation-only lane and timing URL even when the next batch reuses an already loaded URL, preventing rendering from drifting away from narration."
                ),
                AppChangelogEntry(
                    id: "web-narrate-form-editing-hook",
                    title: "Narrate Ebook edits are leaner",
                    detail: "Web Narrate Ebook form editing now runs through a focused tested hook, moving field-change side effects, shared language preference sync, image-default edit markers, and voice override edits out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-lane-inference",
                    title: "Single-track batch endings hold",
                    detail: "Apple reader batch-end handoffs now infer the completed original-only or translation-only lane from the just-ended audio URL when transient manager or selected-track state has reset to combined, keeping the next batch on the selected track."
                ),
                AppChangelogEntry(
                    id: "web-narrate-template-apply-hook",
                    title: "Narrate Ebook template apply is leaner",
                    detail: "Web Narrate Ebook saved-template application now runs through a focused tested hook, moving compatibility status, discovery panel selection, edited-field markers, and shared language preference sync out of the main form coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-row-anchor-hydration",
                    title: "Single-track batches keep their row",
                    detail: "Apple reader original-only and translation-only batch advances now keep a chunk-local target row until sentence metadata hydrates, then upgrade it to the real displayed sentence number so rendering does not reset at batch boundaries."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-metadata-reprepare",
                    title: "Batch hydration keeps audio aligned",
                    detail: "Apple reader metadata refreshes that repair a stale selected audio option in single-track mode now prepare audio again for the same recent sentence anchor, keeping narration and rendered tracks aligned after batch hydration."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-render-anchor-selected-lane",
                    title: "Single-track render locks are stricter",
                    detail: "Apple reader original-only and translation-only render anchors now release only when the active audio URL belongs to the selected lane, preventing hidden-track or stale batch audio from resetting rendering at sentence-batch boundaries."
                ),
                AppChangelogEntry(
                    id: "web-narrate-template-save-hook",
                    title: "Narrate Ebook templates are tidier",
                    detail: "Web Narrate Ebook saved-template save status, errors, and busy state now live in a focused tested hook while preserving the shared template payload rules."
                ),
                AppChangelogEntry(
                    id: "web-library-flat-table-component",
                    title: "Web Library table is leaner",
                    detail: "Web Library flat-table headers, media rows, language labels, status/resume badges, and action wiring now live in focused rendered components, keeping cross-surface Library behavior easier to verify."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-anchorless-reprepare",
                    title: "Single-track batches stay locked",
                    detail: "Apple reader original-only and translation-only context rebuilds now reprepare the selected lane even before the next batch's sentence anchor hydrates, preventing stale combined audio from desyncing rendering at batch boundaries."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-durable-batch-lane",
                    title: "Single-track batch handoffs hold",
                    detail: "Apple reader original-only and translation-only playback now records the active single-track lane as durable view-model state whenever the audio manager is single-track, preventing batch-ending races from resetting playback to combined audio before rendering catches up."
                ),
                AppChangelogEntry(
                    id: "web-player-panel-navigation-state-helper",
                    title: "Web navigation controls are leaner",
                    detail: "Web PlayerPanel navigation controls now derive shell class names, search placement, export labels, advanced toggle state, and compact control visibility through a tested helper while preserving panel and fullscreen behavior."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-durable-lifecycle-restore",
                    title: "Single-track batches keep their lane",
                    detail: "Apple reader batch lifecycle restores now use the loaded/preferred/durable original-only or translation-only lane before default track setup, preventing end-of-batch refreshes from resetting rendering to All while narration stays on the selected track."
                ),
                AppChangelogEntry(
                    id: "web-player-panel-navigation-debug-opt-in",
                    title: "Web player navigation is quieter",
                    detail: "Web PlayerPanel media-navigation debug logs are now opt-in during development, keeping sentence skip and media-session navigation quiet by default under local dogfood and automated playback tests."
                ),
                AppChangelogEntry(
                    id: "apple-visible-single-track-batch-restore",
                    title: "Single-track batch handoffs stay selected",
                    detail: "Apple reader single-track batch handoffs now restore original-only or translation-only audio mode from the visible track selection before default chunk setup can expand back to All, keeping rendering and narration on the selected lane."
                ),
                AppChangelogEntry(
                    id: "web-player-panel-navigation-chrome-hook",
                    title: "Web player chrome is leaner",
                    detail: "Web PlayerPanel navigation chrome now lives in a dedicated tested hook, moving generated sentence-jump IDs, advanced-controls state, and panel/fullscreen control assembly out of the main player coordinator."
                ),
                AppChangelogEntry(
                    id: "apple-batch-boundary-lifecycle-lane-repair",
                    title: "Batch-boundary track selection holds",
                    detail: "Apple reader lifecycle repair now binds the view model to the active audio mode before restoring chunk defaults and makes sequence playback prefer the current batch's combined option, preventing end-of-batch selection resets from desyncing rendering."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-remembered-lane-authority",
                    title: "Translation-only wins batch handoffs",
                    detail: "Apple reader single-track playback now lets the remembered original-only or translation-only lane override transient sequence state in timing, duration, role, and sequence helpers, preventing batch endings from resetting rendering to combined audio."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-policy-gate",
                    title: "Batch-ending checks are guarded",
                    detail: "Apple reader stale EOF lane checks now live in the shared playback URL policy covered by the executable mode-switch harness, so combined-only stream handling stays pinned in simulator gates."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-combined-eof-lane-guard",
                    title: "Combined batches keep the selected lane",
                    detail: "Apple reader combined-only audio batches now apply the stale EOF guard per selected lane, so translation-only playback rejects hidden original-stream endings instead of skipping ahead."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-stale-eof-url-guard",
                    title: "Translation-only batch endings stay put",
                    detail: "Apple reader single-track playback now ignores stale audio-ended callbacks from URLs outside the active selected lane, preventing late EOF events from skipping a batch and drifting rendering away from narration."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-adjacent-batch-helper",
                    title: "Translation-only batch jumps stay aligned",
                    detail: "Apple reader next/previous and end-of-batch advances now share one audio-lane-preserving chunk handoff, so stale combined selections cannot reset translation-only or original-only rendering when sentence batches change."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-remembers-lane",
                    title: "Translation-only lane survives batches",
                    detail: "Apple reader original-only and translation-only playback now remembers the selected single-track lane independently of transient chunk audio IDs, so batch boundaries and metadata refreshes cannot reset rendering to the hidden track."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-disabled-plan-lane",
                    title: "Translation-only batch rendering stays aligned",
                    detail: "Apple reader original-only and translation-only playback now keeps disabled sequence-plan state on the selected lane after loading a new sentence batch, preventing rendering from snapping back to hidden original audio."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-prepublish-batch-selection",
                    title: "Translation-only batch handoff is tighter",
                    detail: "Apple reader chunk switches now repair the incoming batch's selected audio option before publishing the new chunk, preventing a stale combined selection from briefly resetting single-track rendering at sentence-batch boundaries."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-context-rebuild-lock",
                    title: "Translation-only survives metadata refresh",
                    detail: "Apple reader original-only and translation-only playback now re-resolves the selected audio option after live media or chunk metadata rebuilds, so new sentence batches cannot keep stale track IDs and drift rendering from narration."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-prepare-option-lock",
                    title: "Translation-only survives prepare",
                    detail: "Apple reader original-only and translation-only playback now reasserts the active single-track audio option every time audio prepares, so stale combined or original selections cannot reset rendering after a sentence-batch handoff."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-handoff-restores-manager",
                    title: "Translation-only survives batch reset",
                    detail: "Apple reader original-only and translation-only playback now restores the active single-track lane from view-model handoff state before new-batch default track setup can expand back to All, keeping rendering and narration aligned after sentence-batch boundaries."
                ),
                AppChangelogEntry(
                    id: "shared-epub-picker-bounded-newest-helper",
                    title: "EPUB pickers stay lighter",
                    detail: "Web and Apple EPUB discovery now share one cached-stat bounded newest-file helper, keeping large NAS-backed source pickers consistently ordered without building discarded route objects."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-bridge-fallback",
                    title: "Translation-only survives EOF handoff",
                    detail: "Apple reader original-only and translation-only playback now preserves the active single-track lane across end-of-file batch callbacks even if the SwiftUI audio-mode bridge is briefly unavailable, preventing the next batch from falling back to combined audio."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-retry-anchor-sync",
                    title: "Translation-only retry stays in sync",
                    detail: "Apple reader single-track batch retries now reassert the active original-only or translation-only audio option and reuse the latest sentence anchor before preparing playback, preventing retry or same-batch target paths from drifting out of sync."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-boundary-option-lock",
                    title: "Translation-only survives batch boundaries",
                    detail: "Apple reader single-track batch advances now reapply the active original-only or translation-only audio option before selecting the next chunk and explicitly target the first next-batch sentence, keeping rendering and narration on the same lane."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-policy-notes",
                    title: "Discovery warnings stay visible",
                    detail: "Apple Create book and video discovery now shows response-level policy notes from partial Default sources searches, so local candidates stay selectable while YouTube or indexer warnings remain visible."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-stale-selection-guard",
                    title: "Translation-only stays selected",
                    detail: "Apple reader single-track playback now lets the active original-only or translation-only mode override stale batch audio selections, so header progress, prefetch, rendering, and narration stay on the selected lane after sentence-batch handoffs."
                ),
                AppChangelogEntry(
                    id: "acquisition-default-fanout-partial-remote-failure",
                    title: "Default sources stay usable",
                    detail: "Web and Apple Default sources discovery now keeps local NAS/manual candidates when an optional remote video provider such as YouTube search or Newznab/Torznab fails, adding a token-safe policy note instead of emptying the whole picker."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-natural-batch-anchor",
                    title: "Translation-only survives batch end",
                    detail: "Apple reader original-only and translation-only playback now anchors the next sentence batch before autoplay starts, including chunks whose text metadata is still loading, so the selected audio lane does not reset or drift at batch boundaries."
                ),
                AppChangelogEntry(
                    id: "acquisition-handoff-upstream-provider-provenance",
                    title: "Discovery provenance survives import",
                    detail: "Web and Apple prepared acquisition handoffs now preserve token-safe upstream source and acquisition provider values from signed artifact tokens, so templates keep reviewed indexer or Download Station provenance after manual-download imports."
                ),
                AppChangelogEntry(
                    id: "backend-epub-picker-streaming-limit",
                    title: "Latest EPUB picker is lighter",
                    detail: "Web and Apple Narrate EPUB bounded source pickers now stream backend-visible EPUB discovery directly from the shared NAS-safe iterator instead of materializing the full books tree before trimming, keeping latest-book defaults lighter on large NAS roots."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-unhydrated-batch-preserve",
                    title: "Translation-only survives unloaded batches",
                    detail: "Apple reader translation-only and original-only playback now preserve the active audio mode from playable chunk audio options even when the next batch's visible text tracks have not hydrated yet, preventing batch-end resets and render/audio drift."
                ),
                AppChangelogEntry(
                    id: "apple-create-source-list-stale-refresh-guard",
                    title: "Source lists stay current",
                    detail: "Apple Create now ignores stale acquisition-provider, server EPUB, subtitle-source, and NAS video library refreshes when a newer source-list request or delete/upload is in flight, keeping pickers aligned with the latest backend state."
                ),
                AppChangelogEntry(
                    id: "apple-create-metadata-stale-refresh-guard",
                    title: "Metadata lookups follow selection",
                    detail: "Apple Create now ignores stale subtitle TV, YouTube TV, and YouTube metadata lookup responses after the lookup source changes or metadata is reset, so slow preview requests cannot overwrite the current reviewed metadata draft."
                ),
                AppChangelogEntry(
                    id: "apple-create-source-detail-stale-refresh-guard",
                    title: "Source details follow selection",
                    detail: "Apple Create now ignores stale chapter-index and embedded-subtitle inspection responses after the selected EPUB or NAS video changes, preventing old Load Chapters or subtitle-stream results from replacing the current source details."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-stale-refresh-guard",
                    title: "Discovery results stay fresh",
                    detail: "Apple Create now ignores stale book and video discovery responses when a newer provider/query search is in flight, keeping Web-style Default sources, NAS, manual-download, YouTube, and indexer candidates from replacing each other after slow backend scans."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-stale-refresh-guard",
                    title: "Saved templates stay mode-safe",
                    detail: "Apple Create now ignores stale saved-template refreshes when a newer mode/API request is in flight, so Generated Book, Narrate EPUB, Subtitle, and YouTube Dub template lists cannot overwrite each other after slow backend responses."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-selected-option-batch-sync",
                    title: "Translation-only keeps its audio file",
                    detail: "Apple reader chunk handoffs now synchronize the selected audio option from the active original-only or translation-only mode before any next-batch playback load, preventing end-of-batch resets to combined audio that made rendering drift from narration."
                ),
                AppChangelogEntry(
                    id: "web-create-intake-stale-refresh-guard",
                    title: "Create queue status stays fresh",
                    detail: "Web creation surfaces and Apple Create now ignore stale job-intake refreshes when a newer queue snapshot is in flight, keeping Narrate Ebook, Subtitle Tool, Video Dubbing, and native Create aligned with the latest backend capacity state."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-batch-transition",
                    title: "Translation-only survives batch changes",
                    detail: "Apple reader chunk setup now preserves an active original-only or translation-only mode before applying default All-track selection, keeping rendering and narration aligned when playback advances into the next sentence batch."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-resume-anchor-consumed",
                    title: "Translation-only resume advances cleanly",
                    detail: "Apple reader single-track resume anchors are now cleared as soon as live playback reaches the resumed sentence, so the next translated sentence cannot briefly render against the stale resume target."
                ),
                AppChangelogEntry(
                    id: "apple-resume-restores-single-track-before-seek",
                    title: "Resume keeps single-track mode",
                    detail: "Apple reader resume now applies a saved original-only or translation-only mode before the sentence seek starts and before visible tracks default back to All, so rendering and audio do not briefly reset to dual-track playback."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-ignores-stale-sequence-render",
                    title: "Translation-only render ignores stale sequence state",
                    detail: "Apple single-track playback now gates transition, dwell, expected-position, and sequence time-observer shortcuts behind the active audio mode, preventing Cinema/tvOS translation-only rendering from drifting when an old sequence plan is still settling."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-time-seek-render-anchor",
                    title: "Translation-only jumps keep rendered sentence",
                    detail: "Apple single-track time seeks now preserve an explicit sentence-number anchor when one is available, keeping Cinema/tvOS translation-only audio, rendering, and follow-up skips aligned after slider, bookmark, search, or legacy scrubber jumps."
                ),
                AppChangelogEntry(
                    id: "apple-reader-track-aware-resume-progress",
                    title: "Translation-only resume stays anchored",
                    detail: "Apple reader resume sync now preserves the active original/translation playback track, and Apple TV sentence-progress focus now steps and seeks sentences with left/right so translation-only playback stays anchored to the rendered sentence after resume or progress jumps."
                ),
                AppChangelogEntry(
                    id: "apple-reader-transport-resume-offset",
                    title: "Reader play resumes inside sentence",
                    detail: "Apple reader Play/Pause recovery now carries the current in-sentence playback offset when it has to rebuild narration, so Apple TV and iPad resume nearer the last-read word instead of restarting the saved sentence."
                ),
                AppChangelogEntry(
                    id: "client-default-sentinel-discovery-omission",
                    title: "Discovery clients omit default sentinel",
                    detail: "The Web and Apple acquisition API clients now omit backend_defaults before book/video discovery requests, keeping raw helper calls aligned with the visible Default sources fan-out while the backend remains tolerant of older clients."
                ),
                AppChangelogEntry(
                    id: "backend-default-sentinel-discovery-fanout",
                    title: "Discovery defaults are backend-tolerant",
                    detail: "The backend acquisition discovery service and route now treat a leaked backend_defaults provider id as the same no-provider Default sources fan-out used by Web and Apple Create, so older clients do not break book/video discovery."
                ),
                AppChangelogEntry(
                    id: "apple-create-default-source-request-normalization",
                    title: "Apple Create defaults match Web discovery",
                    detail: "Apple Create now keeps Default sources as the visible/template selection while omitting the provider parameter from book and video discovery requests, matching Web's backend fan-out and normalizing media kind values before the handoff."
                ),
                AppChangelogEntry(
                    id: "resume-offset-device-log-check",
                    title: "Resume offset logs are verifiable",
                    detail: "Apple DEBUG builds now write token-safe resume-offset breadcrumbs to the shared playback transport log, with a resume-offset verifier for pulled device logs so Cinema/iPad retests can distinguish exact in-sentence resume from sentence-start fallback."
                ),
                AppChangelogEntry(
                    id: "interactive-sequence-resume-offset",
                    title: "Reader resume seeks inside sequence playback",
                    detail: "Apple interactive reader resume now routes saved in-sentence offsets through the sequence playback controller, so combined original/translation playback can resume near the last-read word instead of only at the beginning of the saved sentence."
                ),
                AppChangelogEntry(
                    id: "resume-storage-safe-iterdir",
                    title: "Resume sync scans are safer",
                    detail: "Backend resume-position listing now uses the shared tolerant directory iterator instead of globbing storage files directly, reducing transient sync failures when Web and Apple browse rows refresh resume evidence."
                ),
                AppChangelogEntry(
                    id: "resume-offset-browse-labels",
                    title: "Resume labels show saved offset",
                    detail: "Apple browse rows and Web Library badges now show sentence resume entries with their saved playback time when available, making cross-device resume precision visible before opening a book."
                ),
                AppChangelogEntry(
                    id: "interactive-resume-word-offset",
                    title: "Reader resume keeps word position",
                    detail: "Interactive book resume now records the current playback time alongside the sentence number and validates that offset before applying it, so Apple TV, iPad, and iPhone resume closer to the last-read word instead of always restarting the sentence."
                ),
                AppChangelogEntry(
                    id: "library-cover-copy-safe-stat",
                    title: "Library cover sync tolerates NAS races",
                    detail: "Backend Library sync now compares existing cover assets through NAS-tolerant stat probes before copying, reducing transient media metadata failures shared by Web and Apple Library refreshes."
                ),
                AppChangelogEntry(
                    id: "webapi-startup-safe-path-probes",
                    title: "API startup tolerates NAS races",
                    detail: "Backend startup cleanup and bundled Web static-asset detection now use NAS-tolerant stat and directory scans, reducing transient boot-time cleanup or SPA serving failures shared by Web and Apple clients."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-active-reader-wins-resume",
                    title: "TV pause keeps reader in charge",
                    detail: "Apple TV Music-bed Play/Pause now refuses to turn a Music-paused state into a resume while sentence narration still reports active playback, targeting Cinema cases where the first press paused Music and the next press resumed instead of stopping the track."
                ),
                AppChangelogEntry(
                    id: "youtube-video-download-safe-exists",
                    title: "YouTube downloads tolerate NAS races",
                    detail: "YouTube video download recovery now checks completed partials and prepared yt-dlp fallback files through NAS-tolerant stat probes, reducing transient source import failures shared by Web and Apple video Create flows."
                ),
                AppChangelogEntry(
                    id: "public-epub-acquire-safe-verify",
                    title: "Public EPUB imports verify safely",
                    detail: "Reviewed Gutenberg and Internet Archive EPUB acquisition now verifies downloaded files through the same NAS-tolerant stat helper used by source discovery, returning a controlled error if final metadata cannot be read."
                ),
                AppChangelogEntry(
                    id: "video-discovery-bounded-newest",
                    title: "Video source pickers stay lighter",
                    detail: "Backend NAS and manual-download video discovery now keeps only the newest requested candidates while scanning, so Web and Apple Create source pickers avoid building giant intermediate lists from large download folders."
                ),
                AppChangelogEntry(
                    id: "tvos-ignored-music-pause-active-reader",
                    title: "TV first pause reaches narration",
                    detail: "Apple TV Music-bed playback now converts an otherwise ignored Music non-playing signal into a reader-owned pause while sentence narration is active, so a Siri Remote pause routed to Music should not leave the track playing until a second press."
                ),
                AppChangelogEntry(
                    id: "youtube-dub-generation-safe-stats",
                    title: "YouTube dubbing probes are NAS-tolerant",
                    detail: "Backend YouTube dubbing submission, generation, artifact handling, and video helper output paths now validate selected media, recovered partial downloads, and temporary mux artifacts through tolerant stat helpers, reducing flaky NAS path failures shared by Web and Apple Create flows."
                ),
                AppChangelogEntry(
                    id: "tvos-active-music-pause-confirms-reader",
                    title: "TV Music pauses confirm reader pause",
                    detail: "Apple TV now confirms a Music-bed non-playing signal during active narration before treating it as a reader-owned pause, so a Siri Remote pause routed to Apple Music should stop the sentence track without waiting for a second press."
                ),
                AppChangelogEntry(
                    id: "tvos-watchdog-stray-music-play-latch",
                    title: "TV pause latch watches Music",
                    detail: "Apple TV reader playback now lets the Music-bed watchdog reassert a reader-owned pause when Apple Music starts playing again without an explicit reader resume, targeting Cinema logs with repeated broker pauses and no intervening play."
                ),
                AppChangelogEntry(
                    id: "tvos-interactive-start-music-bed-gate",
                    title: "TV interactive starts gate Music",
                    detail: "Apple TV interactive playback now routes jump/resume-style starts through the same deferred Apple Music bed resume used by reader Play/Pause, and the tvOS Music-bed simulator journey proves that path before remote pause testing."
                ),
                AppChangelogEntry(
                    id: "tvos-command-center-idempotent-bed-controls",
                    title: "TV bed controls ignore stale echoes",
                    detail: "Apple TV reader Now Playing play/pause callbacks now stay idempotent while the physical Play/Pause path remains a toggle, reducing Music-bed echo races where a stale command could pause only one playback layer."
                )
    ]
}
