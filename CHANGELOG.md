# ebook-tools Changelog

Daily user-visible changes for the Apple app and shared home pipeline dogfood.

## 2026-07-02

### 2026.07.02.012

- Web Video Dubbing presentation helpers for source badges, subtitle labels, stream labels, byte/date/count formatting, output paths, and job labels now live in a focused module while preserving existing imports, keeping source display behavior easier to compare with Apple YouTube Dub.
- Web YouTube video search/download helper logic now lives in a focused tested module covering subtitle defaults, quality labels, source badges, provider lookup, and discovery metadata summaries, trimming the page shell for Apple YouTube Dub parity work.
- Apple reader track pills now treat one-file combined audio as a mixed fallback rather than an independently selectable Translation lane, while two-stream combined audio and dedicated Original/Translation tracks still support single-track and both-track playback.
- Backend generated-book option/default construction now lives in a focused router support module, keeping `/api/books/options` easier to compare across Web Narrate Ebook and Apple Create while preserving the same response contract.
- Apple in-app changelog entries for June 30 now live in a dated shard too, keeping the root changelog source focused on the day index as device-visible history grows.
- `make test-changed` now treats dated Apple in-app changelog shards as release metadata, so shard-only edits still run release-version and Apple contract gates without unnecessary simulator builds.
- Apple reader language/audio pills now keep inactive lanes visually inactive during transient loading states while still allowing Original + Translation, Original-only, and Translation-only playback modes.
- Apple in-app changelog entries for July 1 now also live in a dated shard, continuing the cleanup that keeps the root changelog as a small day index for simulator and device builds.
- Apple in-app changelog entries for July 2 now live in a dated shard, keeping the root changelog day index smaller as Web, backend, and Apple dogfood checkpoints accumulate.
- Apple reader header language/audio pills now route taps through the shared guarded audio-mode toggle, preserving Original-only or Translation-only states while allowing the inactive companion pill to restore both-track playback without disabling the wrong lane.
- Backend Library route telemetry now lives in a focused router support module while preserving the same token-safe duration metrics and logs used by Web and Apple Library actions.
- Web Video Dubbing tab state, status notices, template handoff extras, and initial NAS refresh now live in a focused page-state hook with coverage, keeping the page coordinator closer to Apple YouTube Dub parity checks.
- Apple reader header language pill taps now recompute the live active audio roles before changing lanes, preserving Original-only, Translation-only, and Original + Translation modes even after resume or chunk hydration updates.
- Apple reader language pills now behave as guarded multi-select toggles: tapping an inactive Original or Translation pill adds that lane, tapping an active pill removes only that lane when the other remains active, and the last active lane stays selected.
- Apple reader header pill taps now apply the exact role set shown in the header, so both-track playback can be restored by enabling the inactive companion pill while Original-only and Translation-only remain stable single-track modes.
- Apple reader header language pills now clamp stale track state to the lanes available in the current chunk before toggling, so single-track chunks keep their playable pill active while Original + Translation chunks can still use both lanes.
- Apple reader Audio controls now expose Original + Translation, Original-only, and Translation-only as first-class choices across Apple surfaces, with the header pill label driven by the live audio mode instead of stale single-track resume memory.
- Apple reader audio shortcuts now use the same guarded track-toggle path as the header pills, and sequence mode now prefers the combined lane before stale single-track evidence when calculating timeline duration and header progress.
- Web playback viewer renderability, fullscreen preference, document/chrome state, and wake-lock activation now live in a focused PlayerPanel hook with coverage in the playback gate.
- Web live-media snapshot normalization, storage URL resolution, chunk assembly, and progress-generated file parsing now live in a focused helper shared by online playback, Library media, and offline export playback.
- Web Narrate Ebook form chrome now lives in a focused shell component covering header, step tabs, submit status, template save, and submit routing while the form coordinator stays centered on Create state orchestration.
- Web Narrate Ebook base form state now lives in a focused hook covering shared language defaults, generated-source mode, image defaults, and prefilled image flags before Apple Create parity comparisons.
- Web Library inventory loading, selected-entry reconciliation, error resets, and batched resume evidence now live in a focused hook shared by the Library page and its focused regression gate.
- Web Library external focus and debounced search state now live in a focused hook with coverage for cross-surface jump-to-library requests, trimming more state wiring from the page shell.
- Web playback shortcut registration, MyLinguist font-scale wiring, and the shortcut-help overlay now live in a focused PlayerPanel hook with coverage for help toggling and feature-disabled MyLinguist shortcuts.
- Web playback lifecycle effects for autoplay handoff, shell playback/fullscreen callbacks, and per-job pending-reader cleanup now live in a focused PlayerPanel hook with direct coverage.
- Web playback now renders PlayerPanel boundary, shell, prelude, content, and document slots through a focused frame component with direct coverage in the playback gate.
- Backend YouTube NAS video deletion now scans adjacent subtitle sidecars through the shared tolerant directory iterator, so transient NAS directory failures do not break Web or Apple cleanup flows.
- Web Library tab counts, active media-kind switching, and embedded LibraryList wiring now live in a focused entries panel with direct coverage in the Library Web gate.
- Web Library pagination now lives in a focused controls component with rendered boundary coverage, keeping the Library page shell slimmer for the cross-surface redesign work.
- Web Library selected-entry details now render through a focused details panel with overview, metadata, permissions, and empty-state coverage, further trimming the page shell before redesign.
- Web Library selected-entry presentation now lives in a focused hook with direct coverage for book cover previews and TV/YouTube artwork metadata, trimming the page shell while preserving Library detail behavior.
- Web Library permission resolution now lives in a focused hook with coverage for admin, owner, public, private, and grant-backed access, keeping row actions and details aligned while slimming the page shell.
- Advanced visible Apple app versioning to `v2026.07.02.012`.

### 2026.07.02.011

- Backend source discovery now keeps bounded newest EPUB/video/source candidates with ordered insertion and early stale-tail discard, reducing per-file work during large NAS scans while preserving Web/Apple picker ordering.
- Web playback now routes PlayerPanel sentence-jump datalist and shortcut-help prelude chrome through a focused component with rendered coverage in the playback gate.
- Apple reader header language pills now use the shared audio-mode toggle, so Original-only or Translation-only can expand back to both tracks by tapping the inactive companion pill instead of swapping to the other single lane.
- Apple Settings now shows a dedicated Job Intake Contract row for `/api/pipelines/intake/status`, so the device pipeline can verify queue-pressure parity before opening native Create.
- Bounded pipeline source-picker calls now trim output entries as well as EPUB entries, keeping Web and Apple Create source refreshes lighter on large shared output roots.
- Apple reader sequence resume retries now keep the same resolved track as the initial in-sentence seek, preventing job open from starting in Translation and then retrying the first sentence on Original before the next Translation plays.
- Apple playback transport log verification now rejects sequence resume retries that change tracks for the same saved sentence/time, so physical Apple TV logs catch this regression directly.
- Apple reader header language pills now use true toggle semantics: when Original and Translation are both active, tapping Original disables only Original and keeps Translation active, with the symmetric behavior for Translation.
- Apple reader lifecycle refreshes now let a visible Translation-only user selection beat stale Original resume memory, so Apple TV no longer deactivates the Translation pill after chunk availability or lazy metadata refreshes.
- Library media responses now preserve chunk `audioTracks` and `timingTracks` for Apple playback, so Apple TV/iPad/iPhone Library launches keep the Translation pill selectable instead of greying it out when sentence text is loaded lazily.
- Apple reader text-track availability now stays audio-backed while lazy chunk metadata loads, so Apple TV can keep the Translation pill and text track selectable for completed jobs whose `/media` response initially has audio lanes but no inline sentences.
- Shared job-list pagination now sorts visible jobs newest-first before slicing and keeps the route from reshuffling service-provided pages, so Web and Apple Jobs views keep stable ordering across page boundaries.
- Apple timing decode now accepts target, translated, and dubbed timing-track aliases and tolerates translation-only timing responses without a mix track, keeping Translation selectable for live, archived, and offline media.
- Backend media manifests now canonicalize chunk timing-track aliases through the same Original, Translation, and Mix role mapping as audio tracks, so Web and Apple diagnostics agree on translation availability.
- Apple reader header language pills and audio shortcuts keep the active lane stable across single-track switching and restore all available tracks by enabling the inactive companion lane.
- Apple Job and Library resume recording now stores the same selected-track player clock used by resume, preventing Now Playing refreshes from overwriting the last spoken word offset with a rendered sentence-start highlight time.
- Advanced visible Apple app versioning to `v2026.07.02.011`.

### 2026.07.02.003

- Apple reader header roles now expose Translation whenever combined audio contains that stream, even if the chunk also has a dedicated Original option, and single-track resume now uses the exact player clock before falling back to rendered highlight time so playback can continue from the last spoken position.
- Apple reader lifecycle refreshes now honor explicit Original + Translation visible-track selections before restoring stale single-track state, so turning Translation back on on iPad remains active across metadata and sentence-batch updates.
- Apple reader sentence-batch lifecycle restores now read the loaded/preferred/durable Original-only or Translation-only lane before defaulting visible/audio tracks, so end-of-batch chunk refreshes cannot reset selection to All and drift rendering from narration.
- Web Library flat-table rendering now lives in a focused `LibraryFlatTable` component with shared language-label rendering and focused coverage for layout headers, resume/status/action composition, and row permission gating.
- Apple reader Original-only and Translation-only context rebuilds now reprepare the selected lane even when the recent batch-start anchor is not hydrated yet, preventing end-of-batch resets to stale combined audio and out-of-sync rendering.
- Web Subtitle Tool submit errors, template handoff/save messages, intake status, loading-template notices, and submitted-job summaries now render through a focused `SubtitleToolStatusNotices` component with rendered coverage and focused-suite routing.
- Web Video Dubbing downloaded-video rows, detached discovered-source display, subtitle picker, embedded stream chooser, and delete/extract actions now live in a focused `VideoDownloadedListPanel` component with rendered coverage and changed-test routing.
- Apple reader live-media and chunk-metadata context rebuilds now reprepare Original-only or Translation-only audio at the recent sentence anchor, so a sentence-batch refresh cannot keep stale timing/audio URLs while rendering moves to the next batch.
- Apple reader Original-only and Translation-only playback now keeps the user-selected lane as durable view-model state across sentence-batch EOF handoffs and metadata refreshes, so track selection survives batch boundaries and rendering stays synced to the playing audio.
- Web Video Dubbing source discovery provider buttons, query/search status, remote candidate rendering, and Download Station handoff chrome now live in a focused `VideoDiscoveryPanel` component with rendered coverage and changed-test routing.
- Web Video Dubbing TVMaze metadata preview, artwork, editable job/show/episode fields, and raw payload rendering now live in a focused `VideoTvMetadataPreview` component with rendered coverage and changed-test routing, trimming the metadata panel while preserving Apple Create parity behavior.
- Apple reader combined/sequence batch endings no longer infer Original-only or Translation-only mode from the final segment URL after the sequence plan has ended, preventing all-track playback from resetting the next batch to the last spoken track and drifting rendering out of sync.
- Backend acquisition provider discoverability now lives in a focused `provider_catalog` module shared by discovery routing and the provider registry, reducing the chance that Web and Apple Create expose a provider the backend handler map cannot actually route.
- Backend acquisition file discovery, artifact preparation, and Download Station handoff now import source-root resolution from `provider_roots` directly, keeping provider payload assembly out of reusable Web/Apple Create source handling paths.
- Backend acquisition provider root resolution now lives in a focused `provider_roots` helper module, keeping books, NAS video, manual-download, environment, and safe-stat readability logic reusable for Web and Apple Create without bloating the provider registry payload builder.
- Apple reader original-only/translation-only batch handoffs now let the stored selected timing lane override a stale enabled sequence controller, preventing end-of-batch resets where narration continues on the selected track but rendering falls back to combined.
- Web Video Dubbing page feedback, template status, template errors, and intake callout rendering now live in a focused `VideoDubbingFeedbackPanel` with rendered coverage and changed-test routing, trimming the page coordinator without changing the cross-surface Create workflow.
- Apple reader original-only/translation-only rendering now treats the selected timing lane as durable single-track evidence before transient audio-manager or picker state, so no-URL EOF recovery and batch refreshes cannot reset rendering back to combined while narration stays on the selected lane.
- Backend acquisition provider readiness now resolves manual download roots through one helper that keeps NAS video roots discoverable while excluding them from explicit manual-download default fallback policy, preserving Web and Apple Create default-source semantics.
- Apple reader original-only/translation-only playback now treats the selected timing URL stamped by single-track loading as durable lane evidence at sentence-batch EOF, preventing AVPlayer queue cleanup from resetting rendering back to combined while narration advances.
- Apple TV Music-bed watchdogs now recover reader starts that still have a pending interactive autoplay sentence but no reader player, and restore narration volume if reader audio is playing/requested but remains muted outside a sentence transition.
- Apple reader original-only/translation-only end-of-batch anchors now survive slower NAS/device metadata hydration for up to 60 seconds, so the selected audio lane does not reset before the next batch becomes renderable.
- Apple reader Job and Library autoplay now validate tracked resume/start sentences against the loaded job, allow start-only placeholder chunks to resolve their first sentence for metadata hydration, and share a longer bounded retry schedule, reducing stale-start autoplay stalls while tvOS Music-bed E2E remains under active hardening.
- Apple E2E Xcode runs now go through a narrow retry wrapper that cleans stale result/DerivedData paths and retries once only for the known `mobile.notification_proxy` secure-connection simulator service failure, keeping tvOS Music-bed automation from stopping before app assertions.
- Apple reader original-only/translation-only playback now lets the single audio lane that was actually loaded beat stale preferred state at sentence-batch EOF, so end-of-batch handoffs cannot reset rendering away from the selected track.
- Backend acquisition Default sources readiness now lives in a focused provider-defaults helper with direct coverage, keeping Web and Apple Create default book/video source fanout policy reusable outside the provider registry payload builder.
- Backend acquisition discovery now dispatches providers through a registry-aligned routing table with direct coverage, so Web and Apple Create provider metadata cannot drift from the backend discovery handlers.
- Backend Internet Archive acquisition discovery now lives with the focused Archive helper module, keeping Archive search, source-id bridge lookups, EPUB candidate construction, and token-safe handoff metadata out of the shared provider fanout while preserving Web and Apple Create contracts.
- Apple reader original-only/translation-only playback now stamps the current SwiftUI audio mode into the view model before sentence-batch default setup runs, so the selected track cannot reset and drift rendering after a batch ends.
- Backend Open Library acquisition discovery now lives with the focused Open Library helper module, keeping metadata-only candidate construction and media-metadata lookup payload shaping out of the shared provider fanout while preserving Web and Apple Create contracts.
- Backend Project Gutenberg acquisition discovery now lives with the focused Gutenberg helper module, keeping Gutendex API calls and public-domain candidate construction out of the shared provider fanout while preserving Web and Apple Create contracts.
- Backend Newznab/Torznab acquisition discovery now lives with the focused indexer helper module, keeping review-only metadata candidate construction, source-reference storage, and token-safe indexer error handling out of the shared provider fanout.
- Backend YouTube URL/search acquisition discovery now lives with the focused YouTube helper module, keeping metadata candidate construction and token-safe API error handling out of the shared provider fanout while preserving Web and Apple Create contracts.
- Apple reader resume and visible-track restore paths now reapply the full original-only/translation-only audio selection instead of only assigning a matching option id, keeping the durable loaded lane intact when sentence batches end or resume opens in single-track mode.
- Backend local EPUB, manual download, and NAS video discovery now share a focused file-backed provider helper module, keeping filesystem scanning and candidate shaping out of the large acquisition fanout while preserving Web and Apple Create source picker behavior.
- Backend acquisition discovery result models now live in a focused shared module and are re-exported through the existing package APIs, making provider helpers easier to split without changing Web or Apple Create contracts.
- Backend acquisition discovery request normalization now lives in focused tested helpers for media kind, provider, query, limit, language, and Internet Archive source-id handling, keeping Web and Apple Create discovery fanout easier to maintain.
- Apple reader original-only/translation-only playback now remembers the single audio lane that was actually loaded and uses that lane for EOF and render-active checks across sentence-batch handoffs, so transient picker refreshes to Original or Combined cannot desync rendering from narration.
- Apple reader original-only/translation-only render anchors now release only when the active audio URL belongs to the selected lane inside the current selected option, preventing hidden-track or stale batch audio from clearing the next-batch render lock.
- Apple reader translation-only/original-only batch endings now validate EOF callbacks against the currently active single audio URL before selecting the next sentence batch, so stale hidden-track endings cannot reset the audio selection and drift rendering out of sync.
- Apple reader passive hydrated-batch setup now refuses to expand a remembered original-only/translation-only lane back to combined audio just because both text tracks are available, keeping rendered tracks and narration aligned after sentence-batch boundaries.
- Backend Default sources discovery planning now lives in a focused tested helper, keeping local/manual/NAS freshness ordering and remote-provider fetch limits aligned for Web and Apple Create source pickers.
- Backend YouTube acquisition discovery now shares focused tested helpers for URL parsing, metadata normalization, duration parsing, API-key lookup, and token-safe error reason extraction across Web and Apple Create video discovery.
- Backend Newznab/Torznab acquisition discovery now shares focused tested helpers for endpoint/key/category lookup, API URL sanitization, XML feed parsing, and published-date normalization for Web and Apple video source pickers.
- Backend Open Library acquisition discovery now shares focused tested helpers for work/book key normalization, metadata URLs, and cover URLs, keeping Web and Apple Create book metadata handoff easier to maintain.
- Backend Internet Archive acquisition discovery now shares focused tested helpers for search queries, EPUB eligibility, download URLs, metadata fetches, and rights classification used by Web and Apple Create book discovery.
- Backend Project Gutenberg acquisition discovery now shares focused tested helpers for Gutendex search parameters, EPUB/HTML URL selection, and contributor normalization used by Web and Apple Create book discovery.
- Backend local/manual/NAS acquisition discovery now shares focused tested helpers for source-relative paths, display titles, zero-byte EPUB filtering, and bounded newest-first manual source ordering used by Web and Apple Create pickers.
- Backend acquisition discovery now shares focused tested value-normalization helpers for safe identifiers, string/sequence coercion, and integer parsing across public-catalog and video providers.
- Advanced visible Apple app versioning to `v2026.07.02.003`.

## 2026-07-01

### 2026.07.01.001

- Apple reader single-track EOF handoffs now preserve Original-only/Translation-only mode from the sole active audio URL when the system end callback loses its URL, while refusing to guess from multi-file combined queues.
- Apple Create video discovery availability, provider options, YouTube metadata labels, candidate filtering, and template discovery-state shaping now live in a focused Swift helper, keeping Apple YouTube Dub easier to compare with Web Video Dubbing.
- Apple reader single-track mode now treats passive SwiftUI audio-mode observation as non-authoritative, so an end-of-batch/default refresh cannot clear the remembered Original-only or Translation-only lane and reset rendering out of sync.
- Apple Create Download Station completed-file extraction, metadata fallback hints, handoff detection, and refreshed discovery candidate matching now live in a focused Swift helper, keeping Apple YouTube Dub downloader handoff behavior easier to compare with Web Video Dubbing.
- Apple reader original-only/translation-only playback now lets the durable selected lane beat stale SwiftUI audio-manager state at sentence-batch boundaries, so a transient reset to the wrong single track cannot desync rendering from narration.
- Apple reader single-track rendering now bypasses combined-phase timing whenever the durable original-only/translation-only lane is active, so hydrated batch boundaries cannot reset rendering away from the selected audio track.
- Web Narrate Ebook and Video Dubbing now share focused tested voice-inventory option construction, keeping macOS, Piper, gTTS, and bundled voice filtering aligned for Apple Create parity.
- Web Video Dubbing Download Station handoff detection, completed-file extraction, and refreshed NAS-video matching now live in a focused tested helper, keeping downloader handoff behavior easier to mirror in Apple YouTube Dub.
- Web Video Dubbing source-panel discovery placeholders, hints, filename fallbacks, and candidate summary labels now live in a focused tested helper, keeping video discovery behavior easier to mirror in Apple Create.
- Apple reader single-track metadata hydration now prepares the refreshed chunk even when the selected Original/Translation audio option was already correct, so end-of-batch playback cannot keep a stale pre-hydration lane and drift rendering.
- Web Narrate Ebook image style options, prompt-pipeline options, quality slider mapping, and image-throughput estimates now live in a focused tested module, making image settings easier to mirror in Apple Create.
- Web Narrate Ebook Draw Things node availability checks now live in a focused hook with fallback-node and ordering coverage, keeping image generation controls lighter for cross-surface Create parity work.
- Apple reader single-track batch handoffs now restore the SwiftUI audio manager from the view model's durable original-only/translation-only lane before default track setup runs, so hydrated sentence batches do not expand back to All and desync rendering.
- Web Narrate Ebook file and discovery dialog wiring now lives in a focused rendered wrapper, keeping modal routing out of the main form coordinator while preserving source selection and search behavior.
- Web Narrate Ebook discovery candidate filtering now lives in the discovery hook with focused coverage, keeping backend-default source filtering out of the main form coordinator.
- Apple reader single-track playback now treats the loaded single audio URL as the durable lane during batch-end handoffs and rejects wrong-lane EOF callbacks before mutating selection state, preventing Original/Translation picker resets from drifting rendering.
- Web Narrate Ebook section tabs and section metadata overrides now resolve through the focused section-state hook, trimming the form coordinator while keeping Create step presentation covered.
- Apple reader adjacent-batch prefetch now treats the durable original-only/translation-only lane as authoritative and warms the selected stream inside combined-only batches, reducing batch-end races where rendering could reset away from the chosen audio track.
- Web Narrate Ebook mutable workflow refs and user-edited-field preservation now live in a focused tested hook, keeping prefill/template/default sentinels out of the main form coordinator.
- Web Narrate Ebook normalized input metadata-cache keys and merged target-language state now live in a focused tested hook, trimming the main form coordinator while keeping Web and Apple template payloads aligned.
- Apple reader header audio-role pills now use the durable requested original-only/translation-only lane before transient SwiftUI manager state, so batch-boundary sequence blips do not show both tracks as active.
- Apple reader translation-only/original-only playback time now follows the durable requested single-track lane even if the SwiftUI audio manager briefly reports sequence mode at a sentence-batch boundary, preventing hidden-track offsets from drifting rendering out of sync.
- Web Narrate Ebook submit orchestration now lives in a focused tested hook, keeping pipeline submit, intake refresh, and submit-button presentation together outside the main form coordinator.
- Web Narrate Ebook backend image-default application now lives in a focused tested hook, preserving edited image fields and rerun `add_images` choices while trimming the main form coordinator.
- Apple reader audio-track picker selections now stamp the shared original-only/translation-only mode immediately, so iPad and iPhone cannot carry a stale sequence mode into the next sentence batch and reset rendering out of sync.
- Web Narrate Ebook recent-job history callbacks now live in a focused tested hook, moving path normalization, previous-start lookup, and latest job defaults out of the main form coordinator.
- Apple reader EOF handling now stamps the resolved original-only/translation-only lane as durable view-model state before stale URL guards or next-batch selection run, tightening batch-boundary sync when the selected audio option briefly resets.
- Web Narrate Ebook discovery candidate selection now lives in a focused tested hook, moving local/acquire/archive bridge, metadata-only handoff, and discovery-template provenance state out of the main form coordinator.
- Apple playback regression gates now pin the reader EOF handoff and same-URL batch reuse contracts, so future single-track fixes must preserve playback intent through sentence-batch transitions.
- Apple reader end-of-batch audio handoffs now keep playback intent alive until the view model loads the next sentence batch or pauses at end-of-book, preventing single-track selection from briefly resetting during EOF transitions.
- Web Narrate Ebook generated-source sentence resets and forced output-name enforcement now run through a focused tested hook, moving source/output defaulting out of the main form coordinator.
- Web Narrate Ebook prefilled input-file and rerun-parameter application now run through a focused tested hook, moving cached metadata hydration, history-derived starts, and edited-field preservation out of the main form coordinator.
- Apple reader single-track audio preparation now reasserts the active original-only/translation-only lane and timing URL even when the next batch reuses an already loaded URL, preventing end-of-batch selection resets from drifting rendered text away from narration.
- Web Narrate Ebook form editing now runs through a focused tested hook, moving field-change side effects, shared language preference sync, image-default edit markers, and voice override edits out of the main form coordinator.
- Apple reader batch-end handoffs now infer the completed original-only/translation-only lane from the just-ended audio URL when transient manager or selected-track state has reset to combined, so the next sentence batch keeps rendering and narration on the selected track.
- Web Narrate Ebook saved-template application now runs through a focused tested hook, moving compatibility status, discovery panel selection, edited-field markers, and shared language preference sync out of the main form coordinator.
- Apple reader single-track batch anchors can now survive as chunk-local target rows until sentence metadata hydrates, then upgrade to the real displayed sentence number so translation-only/original-only rendering does not reset at sentence-batch boundaries.
- Apple reader metadata refreshes that repair a stale selected audio option in single-track mode now prepare audio again for the same recent sentence anchor, keeping narration and rendered tracks aligned after batch hydration.
- Web Narrate Ebook saved-template save status, errors, and busy state now live in a focused tested hook, trimming lifecycle state from the main form while preserving the shared template payload rules.
- Apple reader single-track batch handoffs now record the active original-only/translation-only lane as durable view-model state whenever the audio-mode manager is single-track, so a batch-ending race cannot reset selection to combined audio before rendering catches up.
- Web PlayerPanel navigation controls now derive shell class names, search placement, export labels, advanced toggle state, and compact control visibility through a tested helper, shrinking the render component while preserving panel/fullscreen behavior.
- Web PlayerPanel media-navigation debug logs are now opt-in during development, keeping sentence skip and media-session navigation quiet by default under local dogfood and automated playback tests.
- Apple reader single-track batch handoffs now restore original-only/translation-only audio mode from the user's visible track selection before any default chunk setup can expand back to All, so end-of-batch playback keeps rendering and narration on the selected lane.
- Web PlayerPanel navigation chrome now lives in a dedicated tested hook, moving generated sentence-jump IDs, advanced-controls state, and panel/fullscreen control assembly out of the main player coordinator.
- Apple reader batch-boundary lifecycle repair now binds the view model to the current audio mode before restoring defaults and makes sequence-mode resolution prefer the current batch's combined option, so track selection cannot reset and desync rendering at the end of a sentence batch.
- Web PlayerPanel pending chunk-selection handoff now lives in a focused tested hook, trimming another playback effect out of the main coordinator while preserving chunk activation and stale-index cleanup.
- Apple reader single-track playback now lets the remembered original-only/translation-only lane override transient sequence manager state in timing, duration, role, and sequence-activity helpers, preventing sentence-batch endings from resetting rendering back to combined audio.
- Apple reader stale EOF lane checks now live in the shared playback URL policy covered by the executable mode-switch harness, so combined-only original/translation stream handling is verified in the simulator pipeline instead of only by source-shape assertions.
- Apple reader combined-only audio batches now apply the stale EOF guard per selected lane, so translation-only playback rejects hidden original-stream end callbacks instead of treating them as valid batch endings.
- Apple reader single-track batch endings now ignore stale AVPlayer end callbacks from URLs outside the active selected lane, preventing late EOF notifications from advancing another sentence batch and drifting translation-only rendering from narration.
- Web Narrate Ebook static audio, voice, and written-mode option lists now flow directly from shared constants instead of being re-memoized in the large form coordinator.
- Web Narrate Ebook selected and manual target-language merging now resolves through the tested Create intake utility, keeping submit payloads, voice overrides, and shared language preferences on the same deduped list outside the large form coordinator.
- Web Narrate Ebook saved-template application now resolves clear/skip/incompatible/apply decisions through the tested template helper, keeping apply-key and compatibility messages outside the large form coordinator.
- Web Narrate Ebook saved-template saves now run through the tested template helper, keeping sanitized payload construction and save success/error mapping outside the large form coordinator.
- Apple reader original-only/translation-only playback now remembers the selected single-track lane independently of transient chunk audio IDs, so sentence-batch boundaries and metadata refreshes cannot reset rendering back to the hidden track.
- Web Narrate Ebook saved-template edit markers now resolve through the tested Create intake utility, keeping edited field, source, sentence, and image-default guards outside the large form component.
- Advanced visible Apple app versioning to `v2026.07.01.001`.
- Web Narrate Ebook discovery template provenance now clears through a tested template helper when the selected EPUB changes, while sparse provider/query discovery state remains available for cross-surface handoff.
- Web Narrate Ebook saved-template extras now resolve through a tested template helper, preserving selected discovery provenance or sparse provider/query drafts before candidate selection outside the form coordinator.
- Web Narrate Ebook prefilled input-file updates now resolve through the tested Create intake utility, preserving derived output names, forced output overrides, cached metadata, and history start-sentence defaults outside the large form component.
- Web Narrate Ebook voice override edits now resolve through the tested Create intake utility, preserving trimmed add/update/delete/no-op behavior outside the large form component.
- Web Narrate Ebook shared language preference updates now resolve through the tested Create intake utility, keeping input language, target-language split, and lookup-cache preference sync pinned outside the large form component.
- Apple interactive reader single-track audio choices now immediately pin the visible transcript lane from header/menu controls and expand back on combined mode, preventing batch-boundary track resets from drifting rendering away from narration.
- Apple reader chunk switches now repair the incoming batch's selected audio option before publishing the new chunk, so translation-only/original-only playback cannot briefly expose a stale combined selection at sentence-batch boundaries.
- Web Narrate Ebook generated-source sentence resets and forced output-name application now resolve through tested Create intake utilities, trimming more side-effect state wiring out of the large form component.
- Web Narrate Ebook generic field updates now flow through tested Create intake utilities, preserving forced-output guards and unchanged-state identity while shrinking the form coordinator.
- Web Narrate Ebook field-change side effects now resolve through tested Create intake utilities, keeping edited-field refs, image-default guards, and shared language updates consistent outside the form coordinator.
- Web Narrate Ebook saved-template form-state normalization and forced-output merging now resolve through tested Create intake utilities, keeping template apply behavior aligned while trimming the form coordinator.
- Apple reader original-only/translation-only playback now keeps disabled sequence-plan state on the selected lane after a new sentence batch loads, preventing end-of-batch rendering from snapping back to the hidden original track.
- Web Narrate Ebook initial form defaults now resolve through the tested Create intake utility, keeping shared language, target-language split, forced output name, and lookup-cache defaults pinned outside the large form component.
- Web PlayerPanel navigation prop shaping now carries the shared sleep-timer slot through the tested playback props helper, trimming the playback component while keeping panel/fullscreen controls aligned under the focused Web gate.
- Apple reader original-only/translation-only playback now re-resolves the active audio option after live media and chunk metadata rebuilds, so a fresh sentence batch cannot keep stale track IDs and drift rendering away from narration.
- Web live media parsing now shares tested relative-path and display-name derivation helpers, keeping live/completed playback files labeled consistently while shrinking the media hook.
- Web live media parsing now shares tested scalar, category, and media-signature helpers from the live-media state module, shrinking the playback hook while keeping live/completed media snapshots normalized the same way.
- Web Library page refresh, edit, remove, access-update, and resume-fetch flows now share tested item reconciliation and mutating-state helpers, trimming more inline state logic before the cross-surface library refresh.
- Apple reader original-only/translation-only playback now reasserts the active single-track audio option at prepare time too, so stale combined/original selections cannot reset rendering after a sentence-batch handoff.
- Web Library list layout detection and timestamp formatting now live in tested shared helpers, shrinking the main list surface before the cross-surface visual refresh while preserving the existing book/subtitle/video table behavior.
- Web and Apple subtitle source discovery now reuses cached NAS-safe stat metadata from the shared source walker when building picker rows, avoiding a second stat pass over every discovered subtitle.
- Apple reader original-only/translation-only playback now restores the active single-track lane from view-model handoff state before new-batch default track setup can expand back to All, keeping rendering and narration aligned after sentence-batch boundaries.
- Web and Apple NAS video discovery now reuses each walked folder stat while ranking videos by effective recency, reducing repeated NAS probes in folders with many downloaded episodes.
- Manual-download EPUB discovery now reuses the shared cached-stat newest-file ordering helper, so Web and Apple Default sources apply the same newest/title tie-break across local and manual roots.
- Web and Apple EPUB discovery now share a bounded newest-file helper that trims source candidates using cached NAS-safe stat payloads before route/acquisition objects are built, keeping large source pickers lighter and consistently ordered.
- Apple reader translation-only/original-only playback now preserves the active single-track lane across end-of-file batch callbacks even if the SwiftUI audio-mode bridge is temporarily unavailable, preventing next-batch playback from falling back to combined audio and rendering out of sync.
- Web Job Detail media diagnostics now count chunks with no files as gaps, matching Apple playback's warning-only diagnostics when backend manifests say playback may skip sections.
- Apple reader single-track batch retries now reassert the active original-only/translation-only audio option and reuse the latest sentence anchor before preparing audio, preventing retry or same-batch target paths from resetting rendering out of sync.
- Apple reader single-track batch advances now reapply the active original-only/translation-only audio option before selecting the next chunk and explicitly target the first next-batch sentence, preventing end-of-batch resets that made rendering drift from narration.
- Apple Create book/video discovery now shows response-level policy notes from partial Default sources searches, matching Web Video Dubbing when local results remain available but YouTube or indexer providers warn.
- Web Video Dubbing discovery now shows backend policy notes from partial Default sources searches, so NAS/manual candidates remain selectable while YouTube or indexer warnings stay visible.
- Apple reader single-track playback now treats the active original-only/translation-only mode as authoritative when a new sentence batch still carries a stale selected audio-track id, keeping header progress, prefetch, rendering, and narration on the selected lane instead of drifting back to combined/original.
- Web and Apple Default sources discovery now keeps local NAS/manual candidates when an optional remote video provider such as YouTube search or Newznab/Torznab fails, surfacing a token-safe policy note instead of collapsing the whole picker.
- Apple reader original-only/translation-only playback now creates a next-batch sentence anchor during natural end-of-batch advances, including placeholder chunks whose text metadata is still hydrating, so the selected audio lane survives batch boundaries without render/audio drift.
- Web and Apple prepared acquisition handoffs now preserve token-safe upstream `source_provider` and `acquisition_provider` values from signed artifact tokens, so templates keep indexer/download-station provenance after manual-download imports.
- Apple reader translation-only/original-only playback now survives unhydrated next-batch setup by preserving the active audio mode from playable chunk audio options even when visible text tracks temporarily fall back to Original, preventing batch-end resets and render/audio drift.
- Web and Apple Narrate EPUB bounded source pickers now stream backend-visible EPUB discovery directly from the shared NAS-safe iterator instead of materializing the full tree before trimming, keeping latest-book defaults lighter on large books roots.
- Apple Create now ignores stale acquisition-provider, server EPUB, subtitle-source, and NAS video library refreshes when a newer source-list request or delete/upload is in flight, keeping pickers aligned with the latest backend state.
- Apple Create now ignores stale subtitle TV, YouTube TV, and YouTube metadata lookup responses after the lookup source changes or metadata is reset, so slow preview requests cannot overwrite the current reviewed metadata draft.
- Apple Create now ignores stale chapter-index and embedded-subtitle inspection responses after the selected EPUB or NAS video changes, preventing old Load Chapters or subtitle-stream results from replacing the current source details.
- Apple Create now ignores stale book and video discovery responses when a newer provider/query search is in flight, keeping Web-style Default sources, NAS, manual-download, YouTube, and indexer candidates from replacing each other after slow backend scans.
- Apple Create now ignores stale saved-template refreshes when a newer mode/API request is in flight, so Generated Book, Narrate EPUB, Subtitle, and YouTube Dub template lists cannot overwrite each other after slow backend responses.
- Apple reader chunk handoffs now synchronize the selected audio option from the active original-only or translation-only mode before any next-batch playback load, preventing end-of-batch resets to combined audio that made rendering drift from narration.
- Apple reader resume sync now preserves the active original/translation playback track, and Apple TV sentence-progress focus now steps and seeks sentences with left/right so translation-only playback stays anchored to the rendered sentence after resume or progress jumps.
- Apple reader Play/Pause recovery now carries the current in-sentence playback offset when it has to rebuild narration, so Apple TV and iPad resume nearer the last-read word instead of restarting the saved sentence.
- The Web and Apple acquisition API clients now omit `backend_defaults` before book/video discovery requests, keeping raw helper calls aligned with the visible Default sources fan-out while the backend remains tolerant of older clients.
- The backend acquisition discovery service and route now treat a leaked `backend_defaults` provider id as the same no-provider Default sources fan-out used by Web and Apple Create, so older clients do not break book/video discovery.
- Apple Create now keeps Default sources as the visible/template selection while omitting the provider parameter from book and video discovery requests, matching Web's backend fan-out and normalizing media kind values before the handoff.
- Apple TV reader playback now lets the Music-bed watchdog reassert a reader-owned pause when Apple Music starts playing again without an explicit reader resume, targeting Cinema logs with repeated broker pauses and no intervening play.
- Apple TV interactive playback now routes jump/resume-style starts through the same deferred Apple Music bed resume used by reader Play/Pause, and the tvOS Music-bed simulator journey asserts that deferred path before remote pause testing.
- Apple TV reader Now Playing play/pause callbacks now stay idempotent while the physical Play/Pause path remains a toggle, reducing Music-bed echo races where a stale command could pause only one playback layer.
- Web and Apple public-catalog EPUB acquisition now reserves collision-safe destination filenames through the NAS-tolerant stat helper, avoiding direct existence checks when backend books roots are flaky.
- Web and Apple YouTube NAS subtitle deletion now validates the selected video through the tolerant stat helper, and changed-test selection runs the focused YouTube dubbing backend gate for these route edits.
- Web and Apple pipeline defaults now validate configured default EPUB inputs with the same tolerant stat helper, so transient NAS existence checks do not leak as defaults-route failures.
- Web and Apple playback media manifests now check lazy chunk metadata availability through the tolerant stat helper, avoiding direct metadata existence checks on flaky NAS-backed job roots.
- Web and Apple reading-bed catalogs now load their manifest through the tolerant stat helper, keeping background-music catalog sync resilient when NAS-backed storage races with remounts.
- Web and Apple media search now resolves generated text, media, subtitle, job-root, and metadata-manifest paths through tolerant stat checks, so reader search pills skip vanished NAS files without breaking the whole search.
- Web and Apple resume/bookmark playback-state files now load and clear through tolerant stat checks, keeping Continue and bookmark sync steadier when shared storage races with remounts.
- Web and Apple job status image-generation summaries now probe image prompt-plan metadata through tolerant stat checks, avoiding direct metadata existence races on NAS-backed job roots.
- Web and Apple lookup-cache builds now probe job roots and chunk metadata through tolerant stat checks, keeping precomputed word lookups steadier around NAS-backed job-root races.
- Web and Apple metadata enrichment caches now load and delete cached lookup files through tolerant stat checks, avoiding direct cache-file existence races during Create metadata review.
- Web and Apple Library sync now loads job metadata manifests through tolerant stat checks, keeping library item refreshes steadier when NAS-backed metadata paths race with cleanup or remounts.
- Web and Apple Library sync now resolves and stages source EPUB/PDF material through tolerant stat checks, reducing source-copy races when NAS-backed job data folders remount or files vanish mid-refresh.
- Web and Apple Library sync now resolves and normalizes cover assets through tolerant stat checks, keeping Library row artwork refreshes steadier around NAS-backed metadata folders.
- Web and Apple Library media manifests now compact chunk payloads, load chunk metadata, and compute media file stats through tolerant stat checks, reducing playback-manifest races around NAS-backed job roots.
- Web and Apple Library playability, media cleanup, and cover-presence checks now use tolerant stat probes, keeping paused-item resume badges and artwork detection steadier during NAS remounts.
- Web and Apple Library import/export flows now validate source folders, metadata manifests, target conflicts, and export sources through tolerant stat checks, reducing filesystem races around shared library actions.
- Web and Apple Library metadata refresh now checks source EPUB availability through tolerant stat probes before local extraction, reducing refresh/enrichment races when NAS-backed source files vanish.
- Web and Apple Library cover mirroring now validates source artwork through tolerant stat probes before copying into item media, reducing artwork refresh races when NAS-backed files vanish.
- Web and Apple Library YouTube-dub bundling now discovers source videos, subtitle companions, staging roots, and copied metadata through tolerant stat probes, reducing NAS races when moving video jobs into the Library.
- Web and Apple Library moves now validate queue roots, target conflicts, YouTube stitched-media detection, and post-move cleanup waits through tolerant stat probes, reducing NAS races during book/video promotion.
- Web and Apple Library media-removal and entry-delete actions now validate item roots and prune ancestors through tolerant stat probes, reducing shared-storage races during cleanup.
- Web and Apple Library metadata edits, access edits, and refresh relocations now validate item roots and rename targets through tolerant stat probes, reducing NAS races during item maintenance.
- Web and Apple Library enrichment, source reupload, and ISBN metadata actions now validate item roots, uploaded source files, and obsolete source cleanup through tolerant stat probes.
- Web and Apple Library item recovery, media-file serving, cover lookup, and filesystem recovery scans now use tolerant stat probes for metadata manifests and file candidates.
- Web and Apple Library repository startup now discovers SQLite migration files through tolerant stat and directory probes, avoiding raw migration-path existence checks during app/preflight startup.
- Web and Apple runtime directory resolution now cleans and reuses configured roots through tolerant stat probes, reducing Create/source-root startup races around transient filesystems.
- Web and Apple default SMB books/output root validation now uses tolerant stat probes for existing roots, creatable children, and missing-parent rejection.
- Web and Apple YouTube dubbing batch stitching now resolves stitched-output collisions, batch inputs, and adjacent subtitle files through tolerant stat probes.

## 2026-06-30

### 2026.06.30.001

- Advanced visible Apple app versioning to `v2026.06.30.001`.
- The unattended Apple TV deploy helper now has contract coverage for sleeping-tvOS launch recovery: it detects foreground-launch denial, requests a userspace reboot, waits for CoreDevice availability, and retries the console launch once.
- Apple TV reader resume from lookup now waits for narration to become active before restarting the Apple Music bed, ignores stale MusicKit pause mirrors after an accepted reader resume, and tvOS sequence dwell pins the muted playhead at sentence boundaries to reduce next-sentence audio bleed.
- Apple TV Play/Pause now treats opposite actions inside the duplicate window as real remote presses while still filtering same-action echoes, reducing cases where only the Apple Music bed pauses before narration.
- The tvOS Music-bed simulator journey now requires the first remote Play/Pause press to report both reader narration and Apple Music paused before any resume attempt, tightening coverage for the two-click pause regression.
- Discovery and downloader handoffs now strip URL user-info credentials from public acquisition metadata and reject credential-bearing signed handoff URLs before Web or Apple Create can reuse them.
- Acquisition metadata now strips sensitive key/value URL fragments, and signed discovery handoff tokens reject fragment credentials before downloader reuse.
- Acquisition token signing and public route serialization now share one URL-safety helper so Web/Apple discovery handoffs use the same credential-scrubbing rules.
- Saved Create templates now reuse the shared URL-safety helper so discovery-state URLs cannot persist user-info credentials, private tracker query keys, or token fragments before Web/Apple reuse.
- Web and Apple Create now scrub discovery-state URL credentials before saving templates, keeping client-side book/video template drafts aligned with the backend guard.
- Apple Create now scrubs subtitle and YouTube metadata drafts with the same recursive template-safety rules before applying or saving templates.
- Offline export manifests now recursively remove sensitive metadata keys and scrub credential-bearing URLs before Apple/Web offline players receive them.
- The backend offline-export checkpoint now runs the manifest metadata scrubber test alongside export route tests, so reusable Apple pipeline validation covers both route and archive payload safety.
- Apple contract tests now compare backend, Web, and Apple URL-safety markers plus public URL schemes directly, preventing template/offline-export scrubbing rules from drifting across surfaces.
- Notification device-removal routing now uses the same `{device_id}` path template advertised by `/api/system/runtime`, and backend tests compare the public descriptor against FastAPI's route table.
- Runtime descriptor tests now compare every advertised `/api/...Path` and `/api/...PathTemplate` against FastAPI routes, aligning library media file streaming on the shared `{file_path}` template.
- The focused `test-backend-runtime-descriptor` pipeline gate now runs that full runtime route-table parity check, so shared Apple preflight catches descriptor drift without the full Web API suite.
- Changed-test selection now routes runtime descriptor source and contract edits through `test-backend-runtime-descriptor`, so local checkpoints exercise the focused Apple preflight gate automatically.
- Changed-test selection now also routes Apple deploy/readiness hook edits through both runtime descriptor and Apple contract gates, preventing unattended-device preflight changes from falling back to generic tests only.
- The shared Apple pipeline manifest validator now requires the full repo-owned backend and Web checkpoint target lists, so reusable pipeline manifests cannot silently drop focused safety slices.
- Shared Apple pipeline manifest validation now rejects well-formed `make` commands that point at targets absent from this repo's Makefile, catching manifest typos before orchestration dry-runs.
- Shared Apple pipeline manifest validation now requires UI-test and macOS iPad-style app-owned journeys and verifies each journey's Makefile target exists before orchestration dry-runs.
- Shared Apple pipeline manifest validation now checks `APPLE_PIPELINE_JOURNEY_PROFILES` against the manifest app-owned journeys, keeping aggregate dry-runs aligned with registered local lanes.
- Apple Create saved-template pickers now show compact read-only details for the selected template, including job type, last update, saved-field count, and token-safe discovery provider/source kind for TV-safe browsing.
- Apple-origin Open Web Create handoffs now persist a token-safe `handoff_source` marker when Web saves generated-book, Narrate EPUB, subtitle, or YouTube dubbing templates, without changing the existing `source: web` template contract.
- Apple Create readiness now probes the authenticated single-template route with a synthetic missing id, treating a clean 404 as route-ready so template detail/handoff/delete drift is caught before simulator or device runs.
- Creation-template detail lookups now scan raw stored ids and normalize only the matching template payload, avoiding unnecessary sanitization work for unrelated saved drafts during Web/Apple handoffs.
- Missing creation-template deletes now scan raw stored ids before normalizing payloads, so stale Web/Apple cleanup requests avoid unnecessary work on unrelated saved drafts.
- Apple Create now treats a missing saved-template delete as stale local state, pruning the row and resolving selection instead of leaving a dead template with a generic error.
- Filtered creation-template lists now scan raw stored modes before normalizing payloads, so mode-specific Web/Apple template pickers avoid touching unrelated saved drafts.
- Apple Create now requests saved templates with the current canonical job mode and refreshes on mode changes, dogfooding the lighter backend template filter from iPhone, iPad, and TV.
- Apple Create readiness now probes all canonical mode-filtered saved-template lists, catching regressions in every lighter template picker route before simulator or device deployment.
- Apple contract tests now compare backend creation-template modes, Apple Create mode mapping, and readiness mode probes so future template modes cannot drift silently between surfaces.
- Changed-test selection now routes creation-template backend schema/service/route edits through backend template tests plus Apple contracts, so the cross-surface template-mode guard runs on the changes that can break it.
- Apple contract tests now include Web's creation-template DTO mode union, and changed-test selection routes shared Web DTO edits through the focused template and Apple contract gates.
- Runtime descriptor contracts now also verify Web's creation-template client path against the canonical backend Create template route, and Web template-client edits run Apple contracts.
- Runtime descriptor contracts now compare Web's generated-book options/jobs client paths with the canonical backend Create routes, and Web generated-book API edits run focused Create plus Apple contract gates.
- Runtime descriptor contracts now compare Web's acquisition discovery/download handoff client paths with the canonical backend Create routes, and Web jobs API edits run Apple contracts.
- Runtime descriptor contracts now compare Web's subtitle and YouTube Create client paths with the canonical backend/Apple routes, and Web subtitle API edits run both focused subtitle/video gates plus Apple contracts.
- Runtime descriptor contracts now compare Web media and resume client paths with the canonical Apple playback/export routes, and Web media/resume API edits run focused Web gates plus Apple contracts.
- Runtime descriptor contracts now compare Web Library action/media client paths with the canonical Apple Library routes, and Web Library API edits run focused Library plus Apple contracts.
- Runtime descriptor contracts now compare Web auth login/OAuth/session client paths with the canonical Apple auth routes, and Web auth API edits run focused auth plus Apple contracts.
- Changed-test selector tests now derive Web clients from the runtime descriptor contract and require Apple contracts for each, keeping future Web/Apple parity additions wired into the pipeline.
- The standalone Apple runtime payload checker now has data-driven coverage for every public descriptor section, including exact array values, so simulator/device preflights catch non-Create contract drift.
- Apple runtime descriptor model tests now derive every Swift contract field and optionality expectation from the backend descriptor constants, catching partial decode-model updates before simulator or device preflights.
- Apple runtime contract constants now expose auth token transport, pipeline cache-buster, and offline export player-type arrays through Swift constants, with tests comparing every advertised backend descriptor value against the Apple clients.
- Web auth and resume clients now use a shared runtime-contract route module mirrored from `/api/system/runtime`, and changed-test selection treats that module as both Web and Apple contract-sensitive.
- Web media, live-media, bookmark, bookmark-delete, and offline-export create calls now use the shared runtime-contract route module, extending backend/Web/Apple path parity into playback-focused Web tests.
- Web Library item, move/remove, upload-source, ISBN, enrichment, and Library-media calls now use the shared runtime-contract route module, keeping Web Library routes aligned with backend and Apple clients.
- Web generated-book options/jobs and creation-template list/detail calls now use the shared runtime-contract route module, bringing another Create handoff slice under backend/Web/Apple path parity.
- Web acquisition provider, discovery, acquire, prepare, and downloader job calls now share the same runtime-contract routes as Apple Create, with focused Web jobs tests covering encoded artifact/task ids.
- Web subtitle source, YouTube dubbing, subtitle job, and assistant lookup calls now use shared runtime-contract route constants, with a direct API-client test covering encoded source/video queries.
- Web pipeline file/default/intake/content-index/upload/LLM/image-node helpers and voice inventory now use the shared Create runtime contract, with focused Web API tests covering encoded source paths.
- Web voice preview synthesis and media search now use shared Linguist/Create runtime-contract routes, with focused media API tests covering encoded search queries.
- Web pipeline submit/list/status/restart/delete/event, timing, and lookup-cache helpers now use the shared Create/PipelineJobs/PipelineMedia/Linguist runtime contracts, with focused Web tests covering encoded job and lookup terms.
- Web subtitle model, metadata fetch, and TV/YouTube metadata cache-clear helpers now use shared Create/PipelineMedia runtime-contract routes, with focused Web tests covering encoded subtitle job ids.

## 2026-06-29

### 2026.06.29.031

- Advanced visible Apple app versioning to `v2026.06.29.031`.
- Apple TV Play/Pause broker resume now bypasses the short MusicKit pause-hold only for an accepted physical remote press, so a reader-owned paused bed can resume on the next click without loosening Now Playing echo protection.
- Reader-owned Apple Music bed resume now defers transient non-playing evidence while auto-resume is active, preventing a stale MusicKit pause observation from immediately pausing narration again.
- The tvOS music-bed simulator journey now treats player containers as presence anchors and walks the debug control strip by remote focus order, so unattended tests reach the Play/Pause assertions instead of failing on a non-focusable view.

### 2026.06.29.029

- Advanced visible Apple app versioning to `v2026.06.29.029`.
- Apple TV Play/Pause broker handling now treats a fully paused reader-owned Apple Music bed as resumable after the short local hold, instead of swallowing the next remote press as a pause echo.
- iPad and iPhone book autoplay now attaches the audio-mode manager and synchronizes visible track selection before the first sentence prepare, preventing original-only startup until a tap refreshes playback.
- Unattended tvOS deploys now detect the CoreDevice foreground-launch sleep refusal, request one userspace reboot, wait for the device to return, and retry launch once.

### 2026.06.29.027

- Advanced visible Apple app versioning to `v2026.06.29.027`.
- Apple TV resume after a reader-owned Apple Music pause now accepts the first post-guard play command instead of treating the normal paused-bed state as an unsolicited echo.
- Changed-test automation now runs non-Xcode contract gates before Apple simulator builds, so an unhealthy macOS account/cache state cannot hide useful Apple pipeline failures.

### 2026.06.29.026

- Advanced visible Apple app versioning to `v2026.06.29.026`.
- Apple device host readiness now writes a token-safe JSON report for passed or failed local Xcode/CoreDevice account-cache checks, so blocked Cinema/iPad/iPhone deploy attempts leave durable evidence under `test-results`.
- Physical-device helper preflight/install/verify/launch commands now resolve friendly CoreDevice names such as Cinema through `devicectl list` before issuing device commands, while still falling back to the original selector if list metadata is unavailable.
- Apple TV resume after a reader-owned Apple Music pause now accepts the first post-guard play command instead of treating the normal paused-bed state as an unsolicited echo.

### 2026.06.29.025

- Advanced visible Apple app versioning to `v2026.06.29.025`.
- Apple TV, iPad, and Now Playing reader pause paths now stop sentence narration before adopting the Apple Music bed pause, so MusicKit follow-up events cannot leave only the bed paused on the first command.

### 2026.06.29.024

- Advanced visible Apple app versioning to `v2026.06.29.024`.
- Apple TV and Apple reader playback now immediately adopts a MusicKit bed pause as reader transport before pausing narration, so the first remote/menu pause should stop both the bed and sentence track together.
- Apple device deploys now fail fast when the local macOS user/cache lookup is unhealthy, reporting the `uid ... has no passwd entry` remediation before CoreDevice or Xcode can abort.
- Added `make apple-device-host-readiness` as a no-device local deploy-host gate for Cinema TV, iPad, and iPhone testing, while keeping `make apple-devices` available for diagnostics.

### 2026.06.29.023

- Advanced visible Apple app versioning to `v2026.06.29.023`.
- iPad and Apple reader Space/play resume now treats stale requested-but-paused narration as resume intent and reasserts playback once, reducing the case where the first key press only clears transport state.
- Web Narrate Ebook templates now also preserve sparse discovery provider/query state before a candidate is selected, matching Apple Create for Default sources and manual-download searches without storing candidate tokens.

### 2026.06.29.022

- Advanced visible Apple app versioning to `v2026.06.29.022`.
- Apple Narrate EPUB templates now preserve discovery provider and query state even before a candidate is selected, keeping Apple-saved drafts aligned with Web Default sources/manual-download discovery while still excluding candidate tokens.

### 2026.06.29.021

- Advanced visible Apple app versioning to `v2026.06.29.021`.
- Apple TV now mirrors a reader-owned Music pause into sentence narration even when AVPlayer requested/playing flags are transiently stale, closing the case where the first Siri Remote click pauses only the Apple Music bed and the second click pauses the track.

### 2026.06.29.020

- Advanced visible Apple app versioning to `v2026.06.29.020`.
- Apple sequence playback now preserves a validated reader play intent across lookup pronunciation and audio-session handoffs, so autoplay and bubble resume do not stop after the first word when the coordinator request flag flickers during a sentence seek.
- Apple TV now adopts active-reader Apple Music non-playing observations before transient bed recovery, so a Siri Remote pause that reaches Music first should pause sentence narration on the first click instead of requiring a second click.
- Reader pause/resume toggles now prefer an active reader-pause state over stale audio coordinator flags, fixing the lookup-bubble Space resume path that could accidentally issue another pause.

### 2026.06.29.019

- Advanced visible Apple app versioning to `v2026.06.29.019`.
- Book autoplay now keeps retrying until the rendered sentence matches the requested resume sentence, preventing transient or wrong-lane playback from ending the retry after one word.
- Reader-owned resume now reasserts the narration audio session before restarting after lookup pronunciation, covering TV remote and parent transport paths that bypass the child bubble handler.

### 2026.06.29.018

- Advanced visible Apple app versioning to `v2026.06.29.018`.
- Apple TV now treats unprompted Apple Music non-playing events during active narration as recoverable bed dips instead of reader pause commands, preventing autoplay from stopping after a word while keeping explicit reader pauses guarded.
- The Apple TV reader pause path keeps the 1.5-second reader-owned hold, ignores noisy broker echoes for 2.5 seconds, and treats paused-bed `pauseCommand` callbacks as resume intent once the hold expires so lookup-bubble and remote resume do not get swallowed.

### 2026.06.29.017

- Advanced visible Apple app versioning to `v2026.06.29.017`.
- Apple TV adopted observed Apple Music stops immediately during active reader narration, removing the 600 ms confirmation delay that let sentence audio keep playing briefly after Music paused.

### 2026.06.29.016

- Advanced visible Apple app versioning to `v2026.06.29.016`.
- Apple TV Music-bed pause now treats a tvOS-observed Apple Music stop during active reader narration as reader pause intent even if the prior bed-evidence flag was cleared, closing the regression where one Play/Pause press paused only Music while sentence audio continued.
- The tvOS Music-bed debug probe now simulates that weaker physical-device signal so the unattended journey covers Music-only pause adoption instead of relying only on a reader-owned remote command.
- Apple TV Music-bed launch-log validation now accepts that observed Music-only pause adoption breadcrumb as a reader-owned pause route, so physical-device captures can verify the fixed path directly.

### 2026.06.29.015

- Advanced visible Apple app versioning to `v2026.06.29.015`.
- Manual-download discovery guidance now chooses folder vs folders from configured roots while keeping `source_path` limited to readable roots, so a single missing import folder is described accurately on Web and Apple Create.
- Apple Create readiness now documents and validates acquisition provider source labels so the reusable device pipeline catches provider-registry drift before simulator or device runs.

### 2026.06.29.014

- Advanced visible Apple app versioning to `v2026.06.29.014`.
- Apple TV reading-bed pause now accepts tvOS-observed Apple Music pause events as reader transport pauses, so one remote Play/Pause press can stop both Apple Music and sentence narration instead of pausing only the bed.
- Backend acquisition providers now advertise source labels such as Books root, NAS video root, and Manual download folders, and Web plus Apple Create use those labels in unavailable-source guidance instead of generic backend-root wording.

### 2026.06.29.013

- Advanced visible Apple app versioning to `v2026.06.29.013`.
- Apple translation-only word highlighting now keeps backend sentence gates in translation-audio time after slider jumps, so measured player duration drift cannot rescale the active translated sentence away from narration.

### 2026.06.29.012

- Advanced visible Apple app versioning to `v2026.06.29.012`.
- Apple translation-only word highlighting now renders through the canonical timeline runtime after slider jumps, so if AVPlayer's actual file duration differs from gate metadata the next translated sentence does not reveal too early or drift away from narration.
- Apple translation-only playback now keeps render timing on the active translation file even when the selected option is the combined original/translation pair, so slider jumps and next/previous skips no longer add the hidden original-track offset.
- Apple translation-only slider seeks now keep the recent single-track target pinned in transcript rendering and selected-sentence state until live audio reaches it, so stale chunk-edge timing cannot make the next skip jump a 10-sentence batch.
- Apple translation-only slider jumps now suppress single-track autoplay until the target sentence seek finishes and mute narration during the seek settle, preventing a chunk-start burst from desynchronizing translated word highlights or making the next move look like a 10-sentence skip.

### 2026.06.29.008

- Advanced visible Apple app versioning to `v2026.06.29.008`.
- Translation-only slider jumps now keep rendering locked to the resolved target chunk until that chunk's audio reaches the requested sentence window, preventing stale old-batch audio from causing 10-sentence skips or dead word highlighting.

### 2026.06.29.007

- Advanced visible Apple app versioning to `v2026.06.29.007`.
- Apple translation-only slider and skip seeks now share a stale-completion guard and resolve explicit anchors through chunk-local rows, so dragging the slider cannot leave audio on one sentence while rendering or next/previous jumps by a 10-sentence batch.

### 2026.06.29.006

- Advanced visible Apple app versioning to `v2026.06.29.006`.
- Apple translation-only rendering now treats start-only sentence gates as absolute audio positions, so slider jumps keep translated word highlighting and audio on the same sentence even when the job metadata omits end gates.

### 2026.06.29.005

- Advanced visible Apple app versioning to `v2026.06.29.005`.
- Apple translation-only slider jumps now keep their cross-chunk sentence anchor while target metadata loads, so a following next/previous command advances by one sentence instead of falling through to the next 10-sentence chunk.

### 2026.06.29.004

- Advanced visible Apple app versioning to `v2026.06.29.004`.
- Translation-only slider commits now refresh the shared single-track sentence anchor before async seek work begins, so next and previous sentence commands start from the slider target instead of stale playback time.

### 2026.06.29.003

- Advanced visible Apple app versioning to `v2026.06.29.003`.
- iPad translation-only slider jumps now release the temporary rendered-sentence lock as soon as the live audio sentence catches up, restoring word highlighting after scrubbing.

### 2026.06.29.002

- Advanced visible Apple app versioning to `v2026.06.29.002`.
- Apple TV reader transport now cancels delayed narration recovery retries when a pause is accepted and treats tvOS-delivered Apple Music pause events as reader pauses while the bed is active, so one Play/Pause press should stop both bed music and sentence audio.
- Apple sentence slider jumps now temporarily lock the rendered transcript/header to the requested sentence until the audio playhead catches up, preventing translation-only jumps from showing a stale sentence while narration has moved.
- Apple interactive reader Audio menu selections now route Original, Translation, and Combined choices through the same audio-mode manager as text/header toggles, so iPad and Apple TV translation-only playback keeps sentence rendering, slider progress, skips, and narration on the selected track.

## 2026-06-28

### 2026.06.28.074

- Advanced visible Apple app versioning to `v2026.06.28.074`.
- Apple single-track reader modes now bypass combined-queue offsets even when a chunk exposes multi-file combined audio, so translation-only or original-only playback keeps rendered sentences, skip targets, and slider jumps aligned to the selected track instead of adding the hidden other-track duration.

### 2026.06.28.073

- Advanced visible Apple app versioning to `v2026.06.28.073`.
- Apple TV Music-bed playback now treats passive MusicKit non-playing observations during active narration as transient bed interruptions to recover, not immediate reader-transport pauses, reducing cases where normal sentence playback pauses both bed music and track audio without a remote pause.
- Apple Settings and deploy/Create readiness now require the backend Media contract to advertise `chunkOrdering=sentenceRange`, so older runtimes that can still return parallel-completion chunk order fail preflight before Apple device testing.

### 2026.06.28.072

- Advanced visible Apple app versioning to `v2026.06.28.072`.
- Apple playback now sorts backend chunk manifests by sentence range before building next/previous navigation, so Apple TV translation-only book playback advances from the 2210-2219 batch to 2220-2229 even when the backend reports chunks in parallel completion order.
- Backend Job and Library media APIs now also sort chunk manifests by sentence range before returning them to Web or Apple clients, preventing older clients and library playback from rendering parallel-completion chunk order while audio advances by sentence order.
- The Apple interactive context builder regression check now includes an out-of-order `2210 -> 2220 -> 2230` manifest fixture, guarding translation-only drift observed around sentence 2219.

### 2026.06.28.065

- Advanced visible Apple app versioning to `v2026.06.28.065`.
- iPad Music-bed E2E now presses Enter while a lookup pronunciation bubble is open and verifies the reader receives a bubble lookup command before Space resume.
- The Apple journey runner now supports Return/Enter through the hidden text-input fallback path, while raw Left/Right remain true XCTest `typeKey` events; the simulator gate documents that raw XCTest Enter does not reach the app reliably.
- iPad Music-bed E2E now drives raw XCTest Left/Right arrow keys while a lookup pronunciation bubble is open, so simulator coverage exercises the same shortcut stack as a hardware keyboard instead of only tapping debug notification buttons.
- The shared Apple journey validator now accepts raw Left/Right keyboard steps alongside Space, and the runner maps them through `XCUIElement.typeKey` for iPad UI tests.
- iPad lookup bubbles now have automated Left/Right word-navigation coverage while pronunciation is active, so the simulator catches the class of failures where arrows stop moving highlighted words before device retests.
- The Music-bed E2E status strip now exposes DEBUG-only bubble word-navigation counters, and the journey validator only permits Left/Right keyboard probes when they are backed by explicit E2E controls instead of raw XCTest text injection.
- iPad lookup-bubble resume now has a simulator journey that starts from a pronunciation pause and resumes with Space through the shared reader transport, proving sentence audio and Apple Music bed return together before device retest.
- The DEBUG lookup-bubble resume probe now runs through the existing hidden E2E controls instead of adding a tappable overlay inside the reader surface, avoiding layout and focus side effects during normal playback.
- iPad reader Play/Space now preserves the current sentence track and playhead on resume by trying the existing AVPlayer before any sentence-boundary recovery reload.
- Reader transport recovery still falls back to sentence reload when the player is genuinely missing, but delayed recovery no longer rewinds a paused original/translation track that can continue in place.
- The iPad Music-bed simulator journey passed again after the in-place reader transport recovery fix before device deployment.
- iPad reader Play/Space with Apple Music bed now clears the reader-owned Music pause state before narration restarts, preventing MusicKit queue restore latency from immediately pausing the sentence track again.
- Job and Library playback now share the same immediate Music-bed resume handoff, while MusicKit still owns the async queue restore and stale-resume barrier internally.
- The iPad Music-bed simulator journey passed again after the immediate Music-bed resume handoff before device deployment.
- iPad reader sentence resume now carries the autoplay intent through same-sentence sequence jumps, so Space/play retries on the already-rendered sentence restart narration instead of clearing the jump silently.
- Sequence sentence jumps now use the per-jump autoplay flag for within-track seeks, track switches, and non-sequence fallback seeks, avoiding stale global playback-request state after a reader-owned pause.
- The iPad Music-bed simulator journey passed again after the same-sentence autoplay fix before device deployment.
- iPad reader transport recovery now treats actual playback as the success signal, so a Space resume that leaves narration requested but silent keeps reloading the current sentence until audio is playing again.
- Device keyboard breadcrumbs now report Job/Library reader transport recovery attempts with requested/playing state and sentence number for the next hardware repro capture.

### 2026.06.28.055

- Advanced visible Apple app versioning to `v2026.06.28.055`.
- iPad and iPhone reader Play/Pause now allow an explicit Space-bar resume immediately after a reader-owned pause, while Apple TV keeps the longer Music-bed pause-hold guard for duplicate remote events.

### 2026.06.28.054

- Advanced visible Apple app versioning to `v2026.06.28.054`.
- Apple Music reading beds now use a neutral playback audio session while mixing with sentence narration, keeping exclusive spoken-audio mode only when Apple Music is not the bed so iPad can play both layers together.
- The iPad Music-bed simulator journey passed again with the neutral mixing session before device validation.

### 2026.06.28.053

- Advanced visible Apple app versioning to `v2026.06.28.053`.
- iPad and iPhone Apple Music reading beds now keep transient sentence-boundary non-playing observations out of the reader-pause adoption path, while still recovering the bed if MusicKit remains stopped.
- iPad and iPhone Apple Music beds now treat sequence sentence handoffs as settle-only transitions when narration remains requested, avoiding a fresh MusicKit resume task at every sentence boundary.
- iPad Apple Music reading beds now defer transient MusicKit non-playing observations while narration is active, reducing sentence-boundary bed dips without changing Apple TV's explicit pause handling.
- The iPad Music-bed simulator journey now probes the already-playing auto-resume path and fails unless the DEBUG skip counter advances, so the gate covers the no-restart behavior directly.
- The same iPad Music-bed journey now forces a requested sentence-transition pause and fails unless Apple Music remains playing while reader audio is briefly between tracks.
- Job and Library playback now switch the reader narration audio session into Apple Music mixing mode as soon as Apple Music becomes the bed, preventing sentence-boundary narration updates from holding an exclusive session under the music bed.
- Apple Music bed playback now exposes DEBUG-only audio-session stability evidence in the shared Music-bed E2E overlay, and the tvOS music-bed journey asserts the reader remains on the stable mixing session instead of repeatedly reactivating audio at playback boundaries.

### 2026.06.28.050

- Advanced visible Apple app versioning to `v2026.06.28.050`.
- Apple TV Play/Pause now hard-pauses whenever the reader still owns the Apple Music bed, even if tvOS has already flickered the instantaneous Music playing flags, so a stale status sample cannot turn the remote press into a resume.
- The Apple TV Music-bed device log gate now verifies the hard-pause breadcrumb and rejects system-driven MusicKit resumes before an explicit reader play command.
- Web Video Dubbing and Apple YouTube Dub now filter `Default sources` result lists through the backend provider default-eligibility contract too, keeping direct YouTube URL candidates out of blind default results while preserving explicit URL review.

### 2026.06.28.048

- Advanced visible Apple app versioning to `v2026.06.28.048`.
- Backend acquisition providers now advertise which media kinds may participate in default discovery fan-out, and Web/Apple Create use that shared contract so direct YouTube URL review remains an explicit source while NAS, manual, YouTube search, and indexer defaults stay consistent across surfaces.

### 2026.06.28.047

- Advanced visible Apple app versioning to `v2026.06.28.047`.
- Apple TV reader-owned Music-bed transport now keeps explicit pause callbacks as pause during the reader pause hold, while Play and toggle still resolve through reader state, so duplicate remote deliveries cannot turn a fresh pause into resume.
- Apple TV Play/Pause now enters the same reader-owned pause path used by lookup/read-aloud whenever the app still owns an Apple Music bed, even if the system playback status has already flickered while the pause is settling.
- Apple TV Play/Pause now uses the lookup-bubble hard-pause semantics when narration or the system Apple Music bed is actually playing, bypassing stale toggle inference before pausing both layers.
- Web and Apple Create now merge prepared artifact provenance into saved book/video discovery state, so templates keep normalized source provider, acquisition provider, candidate id, and source kind after local handoffs.
- Apple TV Music-bed pause now suppresses stray MusicKit play or track-change observations before publishing a playing state to the reader, matching the lookup-bubble hard-pause path more closely.
- Apple Music reading beds now treat reader-owned pause like lookup-bubble pause: auto-resume and disappear handoff paths stay blocked while the reader transport pause is latched, so only an explicit reader play command can restart the bed.
- Shared acquisition prepare responses now include token-free source provider and candidate provenance metadata, keeping Web and Apple discovery templates/drafts traceable after local, public-catalog, or manual-download artifacts are prepared.
- Apple-saved subtitle creation templates now use Web's canonical existing-source mode, and Web accepts older Apple `server` subtitle templates as existing-file templates so saved Create settings round-trip across surfaces.

### 2026.06.28.041

- Advanced visible Apple app versioning to `v2026.06.28.041`.
- Apple Interactive Reader sentence jumps now ignore stale same-chunk metadata completions after a newer slider/search/bookmark/chapter jump supersedes them, preventing older pending jumps from clearing the newer target and leaving audio ahead of a loading transcript.
- Same-URL and non-sequence pending sentence jumps now seek through the audio-ready path, keeping target rendering, audio seek, and optional autoplay ordered together.

### 2026.06.28.040

- Advanced visible Apple app versioning to `v2026.06.28.040`.
- Apple TV reader-owned Music-bed playback now resolves direct tvOS Now Playing play/pause callbacks through reader state while Apple Music is only the bed, so a hardware Play/Pause delivery that arrives as an explicit play command still enters the same pause path that stops sentence audio and the Music bed together.
- The Apple TV Music-bed simulator journey passed again with the updated transport resolver before device validation.

### 2026.06.28.039

- Advanced visible Apple app versioning to `v2026.06.28.039`.
- Apple TV reader-owned Music-bed pauses now route remote Play/Pause through both the foreground command and app broker paths, then hold reader resumes locally during the pause window so duplicate tvOS or Now Playing deliveries cannot restart sentence audio while Apple Music is still settling under the reader surface.
- The Apple TV Music-bed simulator journey now drives the Siri Remote path without debug-button shortcuts and reads status without moving TV focus, proving guarded pause, post-hold resume, rapid double-press pause, and return-to-menu behavior in one credentialed run.

### 2026.06.28.038

- Advanced visible Apple app versioning to `v2026.06.28.038`.
- Web and Apple Create discovery now skip zero-byte EPUB placeholders in backend books roots and manual download folders, keeping unfinished browser/NAS handoffs out of Narrate Ebook source pickers until a real file is present.
- Apple TV reader-owned Music-bed pauses now latch Apple Music before publishing sentence pause state, and book lookup/read-aloud pauses use the same reader-transport latch so bubble activation does not depend on MusicKit observation timing.
- Apple TV reader-owned Music-bed pauses now ignore stale non-foreground Now Playing callbacks that resolve to play, including delayed toggle callbacks, while the foreground remote Play/Pause path stays covered by the reader pause duplicate window.
- The Apple TV Music-bed simulator journey now includes an E2E-only guarded-toggle control, proving stale command-center toggles do not increment reader transport or resume audio while the pause guard is active.
- Apple/Web Create intake readiness now snapshots backend queue pressure through the API threadpool hook, keeping readiness checks responsive while backend worker state is busy.

### 2026.06.28.034

- Advanced visible Apple app versioning to `v2026.06.28.034`.
- Apple TV interactive playback now lets the outer reader transport own Play/Pause when a book shell supplies the unified override, avoiding a second embedded toggle that could restart narration or the Apple Music bed after a pause.

### 2026.06.28.033

- Advanced visible Apple app versioning to `v2026.06.28.033`.
- The Apple TV Music-bed simulator journey now drives the observed Apple Music pause path directly, proving the reader pause guard arms without a reader transport command before the remote-button sequence continues.

### 2026.06.28.032

- Advanced visible Apple app versioning to `v2026.06.28.032`.
- Apple TV now treats an observed Apple Music pause during active reader narration as a reader pause immediately, closing a bounce window where Music could resume before the pause guard was armed.

### 2026.06.28.031

- Advanced visible Apple app versioning to `v2026.06.28.031`.
- Apple TV reader-owned Music-bed pauses now ignore stray Now Playing play callbacks while the pause guard is active, keeping Music-surface events from restarting sentence playback after a remote pause.
- Apple TV Music-bed launch-log checks now require the app-level remote Play/Pause broker breadcrumb and the unified reader-owned pause adoption breadcrumb, making physical remote failures easier to diagnose.

### 2026.06.28.029

- Advanced visible Apple app versioning to `v2026.06.28.029`.
- Apple TV Music-bed pauses observed from the system Music surface now adopt the same reader-owned pause guard as explicit reader pauses, so fullscreen Music suppression, stale resume cancellation, and pause confirmation stay active together.
- Apple TV remote Play/Pause now also routes through the app-level player shortcut broker, matching the iPad Space/keyboard path when SwiftUI focus or MusicKit surfaces do not deliver the view-scoped Play/Pause command.

### 2026.06.28.028

- Advanced visible Apple app versioning to `v2026.06.28.028`.
- Apple TV reader-owned Music-bed pause now cancels pending sentence sequence handoffs before pausing audio, preventing stale track-switch callbacks from restarting narration immediately after Play/Pause.
- Same-action duplicate reader transport callbacks now re-apply pause or play while opposite-action bounce callbacks are still rejected.

### 2026.06.28.027

- Advanced visible Apple app versioning to `v2026.06.28.027`.
- Apple TV Music-bed pause now treats a system-level Apple Music pause during active narration as a reader pause, keeps the reader Now Playing surface alive while paused, and holds fullscreen Music fanart suppression until the reader resumes.

### 2026.06.28.026

- Advanced visible Apple app versioning to `v2026.06.28.026`.
- Apple simulator E2E config can now bootstrap with `E2E_AUTH_TOKEN` or `EBOOKTOOLS_SESSION_TOKEN`, validating the token through the normal session endpoint before falling back to username/password login.

### 2026.06.28.025

- Advanced visible Apple app versioning to `v2026.06.28.025`.
- Apple TV Music-bed Play/Pause now keeps reader pause quiet by stopping reader Now Playing reassertion loops while paused, while preserving fullscreen Music fanart suppression during bed resume so Music stays underneath narration.

### 2026.06.28.024

- Advanced visible Apple app versioning to `v2026.06.28.024`.
- Apple TV reader-owned Music-bed controls now keep direct Now Playing play and pause commands idempotent while reserving current-state resolution for foreground Play/Pause and true toggle callbacks, reducing pause-then-resume loops and fullscreen Music fanart takeovers.

### 2026.06.28.023

- Advanced visible Apple app versioning to `v2026.06.28.023`.
- Apple TV reader-owned Music-bed pause now keeps the tvOS fullscreen-art suppression pulses alive beyond the pause guard, and the stale system-surface release path has been renamed to queue-preserving suppression so future changes do not accidentally hand Now Playing back to Music.

### 2026.06.28.022

- Advanced visible Apple app versioning to `v2026.06.28.022`.
- Apple TV now treats Play and Pause command-center callbacks as state-resolved reader toggles while Apple Music is only the background bed, matching physical remote behavior and keeping fullscreen Music fanart suppression active.
- Job and Library playback now share the same reader transport command resolver, so Apple TV Music-bed Play/Pause policy and duplicate-window timing stay consistent across Browse surfaces.
- The Apple reader navigation contract now guards the shared transport resolver, both Job/Library call sites, and iOS/tvOS project membership so the reusable pipeline catches future drift.

### 2026.06.28.020

- Advanced visible Apple app versioning to `v2026.06.28.020`.
- Apple TV reader Now Playing now keeps direct play and pause commands explicit, while MusicKit play or track-change callbacks during reader-owned pause are re-paused before Music can resume narration or promote fullscreen fanart.
- The Apple TV Music-bed XCUITest target can now run with a warm restored simulator session when credentials are absent, while ordinary Apple E2E targets still fail fast if login credentials are missing.
- Apple Library, Jobs, and search rows now mirror Web’s smart row cues by showing `Newly completed` for fresh playable entries and `Needs attention` for missing media when no resume evidence is present.
- Apple interactive reader headers now show a compact Timing provenance pill when job-level, chunk-level, or gate-only timing data is available, matching the Web reader's timing-source visibility without adding a new control.

### 2026.06.28.019

- Advanced visible Apple app versioning to `v2026.06.28.019`.
- Apple TV keeps fullscreen Music artwork suppression on a live watchdog while Apple Music is only the reading bed, force-reapplying the tvOS idle/fanart block if the system resets it after MusicKit playback or track changes.
- The Apple TV Music-bed launch-log verifier now requires the fullscreen-artwork watchdog breadcrumb in pause-release mode, so hardware repro logs prove the live tvOS guard was armed.

### 2026.06.28.018

- Advanced visible Apple app versioning to `v2026.06.28.018`.
- Apple YouTube Dub templates now restore the saved discovery source and search query in the native source picker when applied, making Apple/Web video discovery handoffs visible as well as preserved in the payload.

### 2026.06.28.017

- Advanced visible Apple app versioning to `v2026.06.28.017`.
- Apple YouTube Dub templates now preserve the selected discovery source and search query with reviewed video candidates, keeping Apple-saved templates aligned with Web Video Dubbing discovery handoffs.

### 2026.06.28.016

- Advanced visible Apple app versioning to `v2026.06.28.016`.
- Apple TV reader-owned Music-bed pause now keeps the Apple Music queue intact while repeatedly re-pausing stray Music playback and holding reader Now Playing suppression, reducing fullscreen Music fanart takeovers without breaking resume.
- The Apple Music-bed launch-log verifier now checks for queue-preserving tvOS playback-surface suppression instead of the older delayed Music surface release.

### 2026.06.28.015

- Advanced visible Apple app versioning to `v2026.06.28.015`.
- Apple Narrate EPUB discovery templates now preserve reviewed book title, rights, language, year, and capability hints across Apple/Web save and apply cycles, including sparse discovery-only template payloads.

### 2026.06.28.014

- Advanced visible Apple app versioning to `v2026.06.28.014`.
- Apple TV Music-bed Play/Pause now cancels and barrier-checks in-flight MusicKit resume tasks after reader pause, then re-pauses/releases the tvOS Music surface if an old async resume wakes up late.
- Apple TV delays the paused Music surface release briefly so quick Play/Pause cycles can resume the remembered bed without immediately tearing down the player queue, while the fullscreen artwork suppression guard remains active.

### 2026.06.28.013

- Advanced visible Apple app versioning to `v2026.06.28.013`.
- Apple TV Music-bed Play/Pause now treats an observed Apple Music pause during bed auto-resume intent as a reader pause even if MusicKit missed the prior playing transition, and releases the tvOS Music playback surface after a shorter hold to reduce fullscreen fanart takeovers.
- Apple reader Now Playing now removes stale remote-command handlers when the active sentence player is reattached or cleared, reducing nondeterministic TV Play/Pause delivery after track or view handoffs.
- The Apple device pipeline now has a token-safe Music-bed launch-log verifier for Apple TV startup and pause/release captures, so real launch-console evidence can be checked with a Makefile target after physical validation.
- Apple Narrate EPUB saved templates now preserve the Discovery panel query and selected provider, including Default sources, so Web-style discovery drafts reopen on Apple with the same source-search context instead of only restoring the EPUB path.
- Apple Narrate EPUB Discovery now auto-loads available default source results when the Discovery panel opens or the provider changes, matching the Web dialog’s default-source behavior while still keeping manual search available.
- Apple TV Music-bed Play/Pause now keeps fullscreen Music artwork suppression behind a shared reader idle-timer owner and delays Music surface release until a reader pause has actually held, improving pause/resume consistency while still pushing the Music fanart surface away.
- Backend video acquisition discovery is now read-only for NAS/manual folders: discovery skips `.part` files instead of recovering/renaming them during source scans, while downloader/acquire flows can still recover completed partials explicitly.
- Web Video Dubbing and Apple YouTube Dub now hide explicit-only `youtube_url` candidates from `Default sources` results even if a malformed backend fanout includes them; pasted YouTube URLs remain available from the explicit YouTube URL source.
- Apple TV Music-bed Play/Pause now blocks delayed duplicate resume callbacks for a short post-pause window and lets the watchdog re-pause narration before returning for the Music pause guard, targeting the pause-then-immediate-resume symptom.
- Apple TV Music-bed E2E status now reports actual fullscreen artwork suppression on tvOS instead of only the requested reader-surface flag.
- The Apple TV Music-bed journey now has a credential-free dry-run target and semantic journey validation for command counts, pause/play actions, double-press debouncing, reader surface ownership, and fullscreen artwork suppression evidence.
- Apple TV Music-bed Play/Pause now rejects stale async MusicKit resume tasks after a reader pause, preventing a delayed queue restore from restarting Music or narration and reducing full-screen Music artwork takeovers.
- Apple TV reader Now Playing reassertions now refresh the actual tvOS idle/fullscreen suppression state, so the reader keeps reapplying the guard if the system flips it while Apple Music is only a background bed.
- Apple TV reader-owned Apple Music pauses now release the tvOS Music playback surface after the pause has held instead of immediately tearing down the queue, while preserving the remembered bed selection so reader Play/Pause can resume the bed from the app.
- The Apple TV Music-bed simulator journey now taps debug-only reader play/pause command buttons, proving direct Now Playing callbacks resolve through reader state instead of only testing physical remote toggles.
- Apple TV reader playback now treats direct remote play/pause callbacks as state-resolved toggles, so a stray Music/Now Playing `play` command cannot consume the duplicate window and block the real reader-owned pause.
- Apple TV reader playback now resolves Play/Pause intent before mutating state and suppresses duplicate foreground/Now Playing callbacks from the same remote press, so the Apple Music bed cannot immediately resume a reader-owned pause.
- The Apple TV Music-bed simulator journey now asserts the accepted reader Play/Pause action (`lastAction=pause/play`) in addition to reader/music state, making duplicate remote callbacks easier to spot from unattended evidence.

### 2026.06.28.004

- Advanced visible Apple app versioning to `v2026.06.28.004`.
- Apple TV now keeps the reader Now Playing surface active while Apple Music is only a background bed, including paused reader transport, and disables tvOS idle promotion into full-screen Music artwork during that reader-owned state.
- The Apple TV Music-bed simulator journey now exposes and asserts the reader pause guard directly, so unattended runs verify that remote pause enters the fullscreen-fanart suppression state and remote play clears it.
- Extended the Apple TV Music-bed pause guard so reader-owned pauses treat the hold window as hard suppression, re-pausing stray MusicKit play observations before they can restart narration or promote fullscreen Music artwork.
- Hardened Apple TV Music-bed Play/Pause so reader-owned pauses keep suppressing stray Apple Music resumes until reader transport explicitly resumes, and active narration keeps tvOS from drifting into full-screen Music artwork.
- Web interactive playback now shows a compact timing provenance pill when word sync is active, distinguishing job-level estimated timing from chunk metadata timing so QA can spot inferred-token playback without opening devtools.

## 2026-06-27

### 2026.06.27.001

- Advanced visible Apple app versioning to `v2026.06.27.001`.
- Hardened Apple TV Music-bed Play/Pause so Job and Library reader transports debounce play, pause, and toggle commands through one gate, and MusicKit suppresses stray Apple Music resumes immediately after a reader-owned pause to reduce fullscreen Music artwork takeovers.
- Routed Mac Studio runtime helper script edits through `make test-changed` to the Apple contract gate, keeping golden-pipeline SSH and fast-forward changes covered by the same non-physical Apple checks.
- Added `make apple-runtime-fast-forward`, a guarded BatchMode SSH helper that fast-forwards the Mac Studio runtime clone with `git pull --ff-only`, prunes stale untracked export-player JS orphans, and refuses other dirtiness before golden pipeline source-sync checks.
- Anchored Apple Now Playing next/previous sentence commands to the last rendered reader sentence, reducing translation-only track skips that jumped multiple sentences when the audio clock lagged the UI.
- Tightened the Apple TV Music-bed simulator journey to assert that each physical Play/Pause press reaches Job/Library reader transport command handling before checking reader and Music-bed pause/resume state, and verified the shared `tvos-music-bed-sync` remote-env journey passes with that route covered.
- Added top-level tvOS Play/Pause handlers to Job and Library playback so the physical Apple TV remote routes directly to reader transport, with duplicate-toggle guarding when Now Playing and foreground delivery both fire.
- Cancelled stale delayed Apple Music-bed reader reassertions on pause/stop/deactivate, and now require live playback or auto-resume intent before delayed reassertions refresh the MusicKit surface.
- Re-ran the shared Apple pipeline contract runner and orchestration dry-runs after the TV Music-bed/preflight hardening, confirming the reusable pipeline expands all ebook-tools simulator and app-owned journey profiles without physical deployment.
- Routed E2E config preflight script edits through `make test-changed` to the Apple contract gate, keeping simulator credential validation changes out of the generic fast suite.
- Guarded the shared Apple pipeline helper against dropping E2E config preflight coverage, and refreshed the TV Music-bed notes to call out the remote Play/Pause assertion.
- Added the Apple E2E config preflight parser tests to the regular Apple contract gate, so the reusable pipeline keeps checking credential/env-file validation instead of only the temporary config writer.
- Extended the unattended Apple TV Music-bed sync journey to press the tvOS remote Play/Pause button after Music-bed playback is active, proving one remote press pauses and resumes both sentence narration and Apple Music in the simulator gate.
- Added a fast Apple E2E config preflight so iPhone, iPad, and Apple TV XCUITest journeys fail before Xcode starts when `E2E_USERNAME`, `E2E_PASSWORD`, or the API URL are missing or malformed.
- Added an unattended Apple TV Music-bed sync journey (`make test-e2e-tvos-music-bed-sync`) that opens a Library book, simulates MusicKit pause/play observations, and proves reader sentence transport mirrors the Apple Music bed.
- Reasserted reader Now Playing ownership when Job or Library playback scene phase changes while Apple Music is only the reading bed, reducing the chance that tvOS fullscreen Music artwork steals focus from the app.
- Added `make test-changed`, a path-aware local gate that maps current Git changes to focused backend, Web, or Apple Make targets before falling back to the fast suite.
- Hardened Makefile pytest target Python selection so Apple/backend gates prefer `.venv` and then a Python 3.10+ runtime instead of accidentally using macOS system Python 3.9.
- Made low Apple Music reading-bed mix values request system ducking while higher mixes keep the bed-forward sentence-narration reduction, giving the slider a quieter low end despite MusicKit volume being system-owned.
- Kept sentence playback as the Now Playing / Control Center owner when Apple Music is used as the reading bed, so play/pause/seek/bookmark controls continue targeting the book instead of the Music track.
- Reasserted reader Now Playing metadata after MusicKit playback and track changes, so iPad Control Center is less likely to fall back to advertising the Apple Music bed instead of the active sentence.
- Persisted the last selected Apple Music song, album, artist, playlist, or station by MusicKit item identity so the reader can reload the previous bed before narration resumes after relaunch.
- Added backend service and route regression coverage proving `youtube_url` remains an explicit discovery provider and never joins backend default video discovery.
- Initialized Apple Music reading-bed mix to a louder bed-forward default on first use, while keeping Apple Music at system volume and reducing sentence narration around it instead of treating Music as narration audio.
- Hardened Apple Create readiness so unattended/golden pipeline gates require `youtube_url` to declare video discovery explicitly and reject it from backend default video discovery, preserving the reviewed direct-URL handoff semantics.
- Web Video Dubbing and Apple YouTube Dub now expose the backend `YouTube URL` discovery provider explicitly, routing pasted YouTube URLs/video IDs into the same reviewed metadata handoff as YouTube search without requiring the search API key.
- Made `youtube_url` an explicit metadata-only acquisition discovery provider, letting Web and Apple Create normalize pasted YouTube URLs/video IDs into reviewed candidates without API-key search or automatic download.
- Moved uploaded reading-bed fetch, upload-size validation, and cleanup checks onto the shared tolerant stat helper, keeping Web and Apple background-music controls steadier around storage races.
- Moved prepared acquisition artifact file validation onto the shared NAS-tolerant stat helper, so reviewed Web/Apple Create handoffs fail cleanly when local/manual EPUB or video files vanish after discovery.
- Documented and contract-guarded Apple Music as an optional system-volume background bed during sentence narration, with the app mix slider reducing narration around Music instead of lowering Apple Music or relying on ducking.
- Moved subtitle source picker roots and selected server subtitle validation onto the shared NAS-tolerant stat path, so Web and Apple subtitle job creation behaves like the EPUB/video pickers during remount or cleanup races.
- Moved `/api/pipelines/files` output-root readiness checks onto the shared tolerant stat path, so Web and Apple file pickers keep showing completed output folders when direct root existence checks race with NAS remounts.
- Reused the shared NAS-tolerant stat helper inside YouTube/NAS video discovery and skipped videos that vanish during path resolution, so Web Video Dubbing and Apple Create video pickers keep listing visible videos/subtitles even if NAS checks race with a remount.
- Reused the NAS-tolerant source stat helper for acquisition provider readiness, so Web and Apple Create default discovery sources do not flap when source roots disappear during remount or cleanup races.
- Kept Apple Music as an optional background reading bed under active sentence narration during reader navigation handoffs, while still stopping it when narration intent is gone or Background Music is disabled.
- Routed Apple interactive reader skip gestures, buttons, and iPad keyboard shortcuts through one explicit sentence-row jump path, and made single-track original/translation seeks prefer per-sentence gates before token timelines so translation-only playback does not drift or skip batches after jumps.
- Moved Apple single-track sentence-gate selection into the shared sentence-position helper and covered original, translation, mixed, invalid, and out-of-range gates in the executable Apple sentence-position contract.
- Added configured Newznab/Torznab indexers to backend-owned default video discovery so Web and Apple Create can include review-only indexer metadata alongside NAS/manual/YouTube candidates without exposing raw URLs or starting downloads.
- Added a Web and Apple video discovery “Default sources” picker option that sends no explicit provider, letting backend-owned NAS/manual/YouTube/indexer defaults return mixed reviewed candidates in one search.
- Added token-safe section span-coverage metrics to backend content indexes, helping Web and Apple playback investigations detect skipped EPUB text without logging source text.
- Added a non-mutating Mac Studio runtime checkout check to the Apple golden pipeline, verifying the remembered `fifo@192.168.1.9` SSH target and `/Users/fifo/Projects/home/ebook-tools` path against the local Git head before source-sync.
- Added an executable Apple playback regression check for Dan Brown-style late-chapter chunks where global sentence numbers use chunk-local word-timing indices, preventing translation-only rendering from losing the active sentence after jumps.
- Reclaimed the iPad player keyboard broker more aggressively after lookup pronunciation starts or finishes, so paused lookup-bubble Left/Right can keep moving the highlighted word after Read Aloud.
- Added visible video progress sliders to Apple playback: iPhone/iPad now show a bottom scrubber and Apple TV exposes a focusable scrubber row above transport controls.
- Tightened translation-only book playback by clearing stale sequence plans before loading a single translation track and seeking sentence jumps against the enabled track instead of defaulting back to original timing.
- Fixed sequence skip targeting so Left/Right sentence skips advance to the next distinct sentence on the preferred track instead of stepping through same-sentence track segments or stale sequence batches.
- Fixed single-track sentence skipping to navigate by the currently rendered sentence index rather than by the next raw timestamp, preventing translation-only playback from jumping whole batches when timing gates drift.
- Cleared stale sequence plans even when switching to an already-loaded single translation track, preventing translation-only playback from reusing old sequence timing during same-URL reloads.
- Routed iPad lookup-bubble Left/Right keys through the global keyboard broker too, so word navigation keeps working after lookup Read Aloud steals first-responder focus.
- Hardened iPad lookup arrow navigation after Read Aloud by clearing the shared keyboard broker and player debounce state whenever playback focus is reactivated, so the first Left/Right press after pronunciation can move the highlighted lookup word.
- Matched video lookup Read Aloud to the same debounce reset path and cleared stale video keyboard dispatch state before subtitle pronunciation starts.
- Normalized acquisition discovery provider IDs before backend search, matching async job handling so Web and Apple Create tolerate trimmed or mixed-case provider selections.
- Normalized acquisition registry provider and media-kind helper IDs too, so reusable pipeline readiness code sees the same provider catalog as the route and service layers.
- Normalized provider/media-kind IDs inside signed acquisition tokens when acquiring or preparing artifacts, keeping saved Web and Apple Create source handoffs compatible after provider-catalog cleanup.
- Normalized discovery/source metadata at the pipeline service boundary, so direct Apple/Web job construction, submit-time metadata inference, and persisted responses keep provider labels consistent for job cards and reader pills.
- Hardened the shared Create job-intake status route so queue-inspection failures return a generic unavailable response with token-safe telemetry instead of exposing backend exception details.
- Hardened the shared pipeline defaults route the same way, so Create defaults-loading failures return a generic unavailable response without leaking local config paths.
- Hardened the Create image-node availability route so Draw Things URL normalization or probe failures return a generic unavailable response without leaking configured node URLs.
- Hardened shared audio voice inventory and match routes so Create voice-picker failures return generic unavailable responses without leaking local voice paths, language parameters, or model names.
- Hardened the shared audio preview synthesis setup path with token-safe telemetry and a generic unavailable response, so Apple/Web Create voice previews do not leak local config paths, sample text, language parameters, or voice identifiers when setup fails.
- Hardened the shared acquisition provider registry route so Create discovery setup failures return a generic unavailable response with token-safe telemetry instead of leaking local config paths or provider secrets.
- Hardened shared assistant lookup failures so Web and Apple lookup bubbles receive a generic backend error with token-safe telemetry instead of raw LLM/provider exception text.
- Hardened Library ISBN metadata preview failures so Web and Apple Library sheets receive a generic lookup error with token-safe telemetry instead of raw Open Library/provider messages.
- Hardened YouTube discovery, download, cleanup, and dubbing failure logs so Web and Apple video Create paths no longer attach raw traceback payloads containing URLs, NAS paths, titles, languages, voices, or tokens.
- Hardened shared OAuth and registration failures so Apple and Web sign-in surfaces receive stable generic errors without exposing provider setup details, identity-token text, email addresses, or local user-store paths.
- Hardened offline export create/download failures so Web and Apple offline sync receive generic errors without exposing source IDs, export IDs, storage paths, or export template locations.
- Added token-safe resume-position route telemetry and generic storage-failure responses so Apple and Web playback resume sync can be diagnosed without exposing user IDs, job IDs, or resume storage paths.
- Hardened bookmark sync storage failures so Apple and Web playback bookmark add/list/delete calls return a generic unavailable response while preserving token-safe route metrics.
- Hardened reading-bed catalog, stream, and admin storage failures so Web and Apple background-music controls receive generic unavailable responses without exposing bed IDs, upload labels, filenames, or storage paths.
- Added token-safe notification route telemetry and generic failure responses so Apple push registration, test notification, and preference sync failures do not expose device tokens, user IDs, payload titles, cover URLs, or storage paths.
- Added token-safe subtitle model inventory telemetry so Apple and Web subtitle Create pickers can diagnose model-list failures without logging user IDs, model tags, provider paths, or backend exception text.
- Hardened acquisition async-job provider validation so unsupported-provider errors no longer echo submitted provider strings, URLs, or token-like query parameters from Web and Apple downloader handoffs.
- Hardened Library source replacement failures so Apple and Web source-upload reviews receive generic errors with token-safe timing instead of backend paths, job IDs, or uploaded filenames.
- Hardened Library metadata edit failures so Apple and Web edit sheets receive stable generic errors with token-safe timing instead of edited titles, authors, job IDs, or library paths.
- Hardened Library ISBN apply failures so Apple and Web metadata sheets receive stable generic errors with token-safe timing instead of ISBNs, job IDs, cache paths, or provider details.
- Hardened Library metadata enrichment failures so Apple and Web enrichment actions receive stable generic errors with token-safe timing instead of provider messages, job IDs, cache paths, or tokens.
- Hardened Library metadata refresh failures so Web refresh and enrich-from-source actions receive stable generic errors with token-safe timing instead of source paths, provider messages, job IDs, or tokens.
- Hardened Library item deletion failures so Apple and Web delete actions receive stable generic errors with token-safe timing instead of job IDs, library paths, or backend storage details.
- Hardened Library move-to-library failures so Apple and Web move actions receive stable generic errors with token-safe timing instead of permission text, job IDs, library paths, or queue storage details.
- Hardened Library media-removal failures so Web cleanup actions receive stable generic errors with token-safe timing instead of job IDs, library paths, media folders, or serialization details.
- Hardened Library item-list failures so Apple and Web Library screens receive a stable generic error with token-safe timing instead of search terms, user IDs, index paths, or serialization details.
- Hardened Library media-manifest failures so Apple and Web playback receive stable generic errors with token-safe timing instead of job IDs, media filenames, library paths, or manifest serialization details.
- Hardened Library media-file resolver failures so Apple and Web playback streams receive stable generic errors with token-safe timing instead of job IDs, encoded file paths, filenames, or library storage paths.
- Hardened Library access-policy load and update failures so Web sharing controls receive stable generic errors with token-safe timing instead of user IDs, grant subjects, job IDs, library paths, or policy serialization details.
- Hardened Library reindex failures so admin maintenance receives stable generic errors with token-safe timing instead of index database paths or library storage details.
- Hardened Library metadata edit access-check and serialization failures so edit sheets keep returning stable generic errors instead of job IDs, edited titles, authors, genres, or library storage paths.
- Hardened Library ISBN apply access-check and serialization failures so metadata sheets keep returning stable generic errors instead of ISBNs, job IDs, cache paths, or library storage details.
- Hardened Library metadata refresh access-check and serialization failures so source-refresh actions keep returning stable generic errors instead of job IDs, source paths, cache paths, or library storage details.
- Hardened Library metadata enrichment access-check and serialization failures so provider-enrichment actions keep returning stable generic errors instead of job IDs, provider cache paths, tokens, or library storage details.
- Hardened Library delete access-check failures so removal actions keep returning stable generic errors instead of job IDs, policy lookup paths, or library storage details.
- Hardened Library source-upload access-check and serialization failures so source replacement keeps returning stable generic errors instead of filenames, job IDs, temporary upload paths, or library storage details.
- Hardened Library move-to-library payload validation failures so queue-to-Library handoffs keep returning stable generic errors instead of job IDs, queue paths, or library storage details.
- Hardened Library media-manifest final payload validation so Apple and Web playback keep returning stable generic errors instead of logging success before malformed manifest responses are rejected.
- Hardened Library reindex response validation so admin maintenance keeps returning stable generic errors instead of logging success before malformed index counts are rejected.
- Hardened Library list response validation so Apple and Web Library screens keep returning stable generic errors instead of logging success before malformed result envelopes are rejected.
- Hardened bookmark response validation so Apple and Web playback bookmark sync keeps returning stable generic errors instead of logging success before malformed bookmark payloads are rejected.
- Hardened resume-position response validation so Apple and Web playback resume sync keeps returning stable generic errors instead of logging success before malformed resume payloads are rejected.
- Hardened creation-template storage and response validation so Apple and Web Create template sync returns stable generic errors instead of leaking template IDs, user IDs, local paths, or malformed payload values.
- Hardened audio voice inventory and match response validation so Apple and Web Create voice pickers keep returning generic errors instead of logging success before malformed voice payloads are rejected.
- Hardened subtitle source and model picker failures so Apple and Web Create return generic errors instead of leaking NAS paths, source filenames, user IDs, or malformed model payloads.
- Hardened assistant lookup bad-request and response-validation failures so Apple and Web lookup bubbles return generic errors instead of leaking selected words, prompts, models, or malformed token-usage payloads.
- Hardened offline export response validation and unexpected download failures so Apple and Web offline sync keep returning generic errors instead of leaking export IDs, filenames, or storage paths.
- Hardened acquisition provider and discovery response validation so Apple and Web Create discovery pickers keep returning generic errors instead of leaking provider IDs, source paths, candidate tokens, or malformed rights payloads.
- Hardened acquisition acquire, artifact-prepare, and downloader job responses so Web and Apple Create handoffs validate before success telemetry and keep malformed artifact/task payloads behind generic errors.
- Normalized reading-bed fetch, update, and delete route IDs so Apple and Web background-music controls tolerate padded IDs and reject blank IDs before touching storage.
- Normalized Apple push-notification device tokens on register/unregister, added typed unregister/preferences-update responses, and guarded malformed preference-device payloads behind generic sync errors.
- Added token-safe telemetry for EPUB chapter loading so Apple and Web Create can diagnose content-index success, validation, missing-file, and parser-error outcomes without logging source filenames or paths.
- Normalized shared pipeline job action route IDs so Apple and Web pause/resume/cancel/delete/restart controls tolerate padded IDs and reject blank IDs before touching job storage.
- Normalized shared playback timing route IDs and returned generic authorization failures so Apple and Web timing resolvers tolerate padded IDs without exposing backend paths or user details.
- Normalized shared storage media-stream job IDs and returned generic authorization failures so Apple and Web audio/video/text file playback tolerates padded IDs without leaking backend paths.
- Normalized shared job media manifest route IDs and returned generic authorization failures so Apple and Web playback setup tolerates padded IDs without leaking backend paths.
- Normalized the shared media-root resolver used by sentence-image and lookup-cache routes, so padded job IDs and forbidden media access behave consistently without leaking backend paths.

## 2026-06-26

### 2026.06.26.183

- Advanced visible Apple app versioning to `v2026.06.26.183`.
- Fixed iPad lookup arrow navigation after Read Aloud starts by reclaiming the shared player keyboard path when pronunciation playback begins and removing duplicate bubble-local arrow shortcuts.
- Matched iPad video lookup keyboard handling to the book reader by removing duplicate hidden subtitle-bubble arrow shortcuts and refreshing the shared keyboard broker after video lookup Read Aloud starts.
- When an iPad lookup bubble is open, plain Left and Right now navigate lookup words before playback transport checks run, avoiding stale playing-state from stealing paused word navigation.
- Routed paused iPad lookup-bubble Left/Right arrow handling through the bubble word-navigation path across UIKit, SwiftUI, app-command, and hardware-keyboard fallback sources, so the highlighted word and lookup definition advance together.
- Added local iPad Left/Right shortcuts inside the lookup bubble itself, so paused word navigation keeps working when the bubble owns hardware-keyboard focus.
- Fixed iPad Interactive Reader lookup navigation by mounting the SwiftUI hardware-keyboard fallback layer, so plain Left/Right moves the highlighted lookup word while paused even after bubble focus changes.
- Added DEBUG-only iPad keyboard breadcrumbs around Interactive Reader shortcut dispatch and word selection, making future hardware-key regressions diagnosable from device logs instead of guesswork.
- Added an iPad video keyboard fallback layer so paused video lookup bubbles can receive the same hardware-key previous/next word path as book playback.
- Hid the custom iPhone and iPad video timeline pill when native AVPlayer controls are available, so video playback no longer shows a duplicate progress control beside the system scrubber.
- Web video dubbing now refreshes manual NAS downloads after a completed Download Station task and auto-selects the matching video/subtitle when the completed file can be matched safely.

### 2026.06.26.164

- Advanced visible Apple app versioning to `v2026.06.26.164`.
- Fixed Interactive Reader sentence jumps so iPad and iPhone wait for renderable target-sentence metadata before preparing audio, preventing the loading wheel from staying visible while the jumped sentence is already playing.
- Fixed Apple TV Interactive Reader footer-slider remote movement so left/right scrubs sentences instead of falling through to previous/next word highlighting.

### 2026.06.26.163

- Advanced visible Apple app versioning to `v2026.06.26.163`.
- Made Apple Create EPUB imports behave like Web uploads: choosing a local EPUB now immediately uploads it to the backend server EPUB folder, refreshes the server picker, and selects the uploaded path before Narrate EPUB submission.
- Improved dense-text word taps in Interactive Reader so near-token taps seek and lookup instead of falling through as background playback toggles.
- Made Apple TV Interactive Reader sentence-progress focus explicit while preserving Video playback's native focused overlay scrubber as the single TV video timeline control.
- Made the iPhone Interactive Reader sentence slider hideable behind a compact progress pill, with bottom transcript clearance while the full slider is visible and renderable tracks kept on-screen during slider jumps.
- Removed the extra shared bottom progress footer from Apple TV video playback so the TV surface shows only its native focused scrubber.
- Added a thin cross-surface progress footer for Interactive Reader and video playback so sentence/time seeking stays available on iPhone, iPad, Apple TV, and Mac Designed for iPad without crowding the header.
- Tightened the Interactive Reader identity header by moving title, author, category/type, and model metadata onto one compact line where space allows.
- Hardened acquisition/discovery API responses so provider metadata cannot leak obvious secret fields or sensitive URL query parameters into Web or Apple Create handoffs.
- Improved shared media manifest diagnostics so URL-backed or persisted media entries use manifest-provided sizes instead of showing false missing-size warnings in Web or Apple playback.
- Made Return to Now Playing reopen the active item in a resume-only continue mode, so it resumes the current rendered position when available instead of falling back to the beginning.
- Fixed Apple Music reading-bed auto-resume during sentence playback by allowing the bed to resume as soon as narration playback is requested, while still respecting manually paused music.
- Changed Apple TV's browse-shell Now Playing return into a focused bottom overlay after backing out of playback, giving the remote a direct way back to the active entry.
- Tightened interactive sequence track switching so a pause during a sentence transition is respected instead of restarting playback when the new track becomes ready.

### 2026.06.26.157

- Advanced visible Apple app versioning to `v2026.06.26.157`.
- Improved backend sentence splitting so `a.m.`/`p.m.` time abbreviations can end a sentence before a clear uppercase follow-up while staying attached to lowercase continuations; refined sentence caches now invalidate with splitter version `regex-v8`.
- Added stricter splitter losslessness tests that map each output sentence back through the source text in order, covering harder dialogue, CJK punctuation, ellipses, and time-abbreviation cases.

### 2026.06.26.156

- Advanced visible Apple app versioning to `v2026.06.26.156`.
- Extended Apple Create readiness runtime preflight beyond Create routes to validate Library action, offline export, playback-state, and notification contracts before native journeys start.
- Kept Apple TV's Return to Now Playing affordance in the browse list after backing out of playback, and tightened Apple Music reading-bed auto-resume so sentence switches respect paused music.

### 2026.06.26.155

- Advanced visible Apple app versioning to `v2026.06.26.155`.
- Added an Apple offline-export download route helper that substitutes the advertised runtime template, keeping future native download handling aligned with Settings and Create-readiness preflight.

### 2026.06.26.154

- Advanced visible Apple app versioning to `v2026.06.26.154`.
- Aligned Apple Create template and acquisition job helpers with their advertised runtime templates, keeping saved-template and discovery job polling routes on the same contract Settings validates.

### 2026.06.26.153

- Advanced visible Apple app versioning to `v2026.06.26.153`.
- Aligned Apple Library metadata helpers with their advertised runtime templates so item edits, source uploads, ISBN apply, and metadata enrichment share the same route contract checked in Settings.

### 2026.06.26.152

- Advanced visible Apple app versioning to `v2026.06.26.152`.
- Moved Apple library media file URL construction and offline path parsing behind shared media route helpers so playback and offline sync resolve encoded Library assets through one contract.

### 2026.06.26.151

- Advanced visible Apple app versioning to `v2026.06.26.151`.
- Kept Apple Music reading-bed toggles on the same play-intent guard as sentence switches, so enabling Background Music does not restart a manually paused Apple Music track unless narration is actively playing.

### 2026.06.26.150

- Advanced visible Apple app versioning to `v2026.06.26.150`.
- Added notification device, test, rich-test, and preference routes to the public Apple runtime contract and moved Apple notification API calls behind shared helpers so Settings and create-readiness checks catch push-route drift.

### 2026.06.26.149

- Advanced visible Apple app versioning to `v2026.06.26.149`.
- Added OAuth login and reading-bed catalog paths to the public Apple runtime contract, and moved Apple auth/session/runtime plus playback-state route calls behind shared helpers for stronger preflight drift checks.

### 2026.06.26.148

- Advanced visible Apple app versioning to `v2026.06.26.148`.
- Moved Apple playback media, timing, subtitle metadata, lookup-cache, assistant lookup, and audio synthesis endpoints into shared route helpers so playback surfaces avoid inline API string drift.

### 2026.06.26.147

- Advanced visible Apple app versioning to `v2026.06.26.147`.
- Added Apple Jobs and Library move/remove routes to the public runtime contract and shared Apple client helpers, so settings/readiness checks catch action endpoint drift before simulator or device deployment.

### 2026.06.26.146

- Advanced visible Apple app versioning to `v2026.06.26.146`.
- Improved backend sentence splitting for book jobs so leading bullet markers are preserved instead of dropped, Unicode lowercase starts after terminal punctuation split more naturally, and refined sentence caches invalidate through splitter version `regex-v7`.

### 2026.06.26.145

- Advanced visible Apple app versioning to `v2026.06.26.145`.
- Made Apple chapter menu and range-selector jumps preserve requested playback through sentence transitions, matching Search, Bookmarks, and the header progress slider.

### 2026.06.26.144

- Advanced visible Apple app versioning to `v2026.06.26.144`.
- Kept Apple Music idle when Background Music is off, so selecting Apple Music as the preferred reading-bed source does not claim mixing or Now Playing ownership until music is enabled again.

### 2026.06.26.143

- Advanced visible Apple app versioning to `v2026.06.26.143`.
- Made Apple Music reading-bed playback respect Control Center and lock-screen pauses as manual pause intent, preventing paused music from restarting on sentence switches until the user resumes it.

### 2026.06.26.142

- Advanced visible Apple app versioning to `v2026.06.26.142`.
- Added a compact Apple TV Now Playing mini control in the browse shell after backing out of playback, keeping a direct route back to the active job or library item while preserving the existing return strip.

### 2026.06.26.141

- Advanced visible Apple app versioning to `v2026.06.26.141`.
- Tightened Apple API route encoding for playback, Library, media, lookup, event-stream, and notification path components so job IDs, bookmark IDs, chunk IDs, and tokens containing route separators cannot split backend paths.

### 2026.06.26.140

- Advanced visible Apple app versioning to `v2026.06.26.140`.
- Kept the Now Playing return strip visible in the iPad/Mac-style Search surface after leaving playback, so search does not strand the active job or library item without a direct return action.

### 2026.06.26.139

- Advanced visible Apple app versioning to `v2026.06.26.139`.
- Moved the Apple TV Return to Now Playing affordance into the top of the browse menu after backing out of playback, giving the remote a direct focused path back to the active item.

### 2026.06.26.138

- Advanced visible Apple app versioning to `v2026.06.26.138`.
- Updated Apple Create's Download Station completion message and handoff panel to resolve completed filenames from the same top-level and metadata fallback hints used by Web.

### 2026.06.26.137

- Advanced visible Apple app versioning to `v2026.06.26.137`.
- Updated Web Video Dubbing to read Download Station completed-file hints from acquisition job metadata, matching the shared Apple fallback contract when top-level status fields are absent.

### 2026.06.26.136

- Advanced visible Apple app versioning to `v2026.06.26.136`.
- Mirrored completed Download Station file hints into acquisition job metadata so Web and Apple Create can reconnect finished downloads through the same fallback metadata contract as the top-level status.

### 2026.06.26.135

- Advanced visible Apple app versioning to `v2026.06.26.135`.
- Tightened Apple Music reading-bed auto-resume so sentence switches and paused jumps only restart Apple Music when narration playback is still explicitly requested and active.

### 2026.06.26.134

- Advanced visible Apple app versioning to `v2026.06.26.134`.
- Preserved Download Station job metadata in Apple Create and used safe metadata file hints as a fallback when matching completed downloads back to manual video discovery.
- Added a persistent Apple TV Now Playing return overlay in the browse shell so backing out of playback leaves a direct route back to the active job or library item.
- Extended Apple Create readiness preflight to make bounded book/video discovery calls against the backend-owned default providers, validating response shape before simulator or device journeys.
- Extended Apple Create readiness preflight to validate backend-owned default acquisition provider ids for book and video discovery before simulator or device journeys.
- Clarified the Apple browse Now Playing return control with explicit return wording and an action-oriented icon, making the route back to active playback easier to recognize on TV, iPad, iPhone, and Mac-style surfaces.
- Added backend-owned discovery media-kind metadata to acquisition providers so Web and Apple Create can show only providers that really support book or video discovery while preserving fallback behavior for older backends.
- Exposed backend-owned default discovery provider ids in the acquisition provider response so Web and Apple Create can align default book/video searches with the API instead of hard-coded assumptions.
- Wired Web and Apple Create pickers to adopt backend-owned default book/video discovery providers once per session while preserving the user's manual provider choice.
- Moved Web Narrate Ebook discovery-provider ordering, availability, and default-provider selection into a focused utility with direct pipeline coverage.

### 2026.06.26.133

- Advanced visible Apple app versioning to `v2026.06.26.133`.
- Made Apple sentence-sequence transitions respect the current pause intent, so paused playback and Apple Music reading-bed state stay paused across dwell, track-switch, and direct jump transitions.

### 2026.06.26.132

- Advanced visible Apple app versioning to `v2026.06.26.132`.
- Made the Apple browse Now Playing return element remember the active playback target and refocus on Apple TV after backing out of playback, keeping a direct route back to the playing job or library item.

### 2026.06.26.131

- Advanced visible Apple app versioning to `v2026.06.26.131`.
- Aligned Apple Library, Jobs, and search resume menu labels with the freshest available local or cloud resume point so the visible Resume action matches the row badge.

### 2026.06.26.130

- Advanced visible Apple app versioning to `v2026.06.26.130`.
- Unified Apple Create submission and template-save draft construction so generated book, narration, subtitle, and YouTube Dub jobs use the same current draft builders, preserving YouTube discovery metadata in saved templates.

### 2026.06.26.129

- Advanced visible Apple app versioning to `v2026.06.26.129`.
- Added the Now Playing return strip across Apple browse surfaces so iPhone, iPad, Mac-style, and Apple TV users can get back to the current playback entry after navigating away.

### 2026.06.26.128

- Advanced visible Apple app versioning to `v2026.06.26.128`.
- Refactored Apple Create settings assembly into a dedicated SwiftUI view so the large Create screen keeps mode-gated section ordering outside the main orchestration view.

### 2026.06.26.127

- Advanced visible Apple app versioning to `v2026.06.26.127`.
- Completed the repo-owned cross-surface checkpoint alignment with the shared backend/Web manifest so safe checkpoints run the full backend slice set, focused Web checks, full Vitest, Web builds, and Apple local-surface verification.

### 2026.06.26.126

- Advanced visible Apple app versioning to `v2026.06.26.126`.
- Aligned the repo-owned cross-surface checkpoint with the shared pipeline's Library, playback, Sidebar, Job Progress, and app-view checks so safe checkpoints cover the broader Web/backend surface before Apple simulator verification.

### 2026.06.26.125

- Advanced visible Apple app versioning to `v2026.06.26.125`.
- Broadened `make verify-apple-cross-surface-checkpoint` so safe checkpoints cover backend subtitle and YouTube dubbing slices plus focused Web Video Dubbing and Subtitle Tool tests before Web builds and Apple local-surface verification.

### 2026.06.26.124

- Advanced visible Apple app versioning to `v2026.06.26.124`.
- Fixed Apple Music reading-bed playback so a manual pause stays paused across sentence changes instead of auto-resuming during narration transitions.
- Added a tvOS Now Playing return control above the browse menu so pressing Back from playback still leaves a direct path back to the current job or library item.

### 2026.06.26.123

- Advanced visible Apple app versioning to `v2026.06.26.123`.
- Tightened unattended Apple deploys so stable signed artifacts are verified before CoreDevice preflight/install, and locked-device launch denials after a verified install are reported without failing the deploy.

### 2026.06.26.122

- Advanced visible Apple app versioning to `v2026.06.26.122`.
- Extended `make verify-apple-cross-surface-checkpoint` to run the backend creation-template and acquisition route slices before the Web Create checks, Web build, and Apple local-surface verification.

### 2026.06.26.121

- Advanced visible Apple app versioning to `v2026.06.26.121`.
- Strengthened `make verify-apple-cross-surface-checkpoint` so it runs focused Web Create intake and creation-template tests before the Web production/export build and Apple local-surface verification.

### 2026.06.26.120

- Advanced visible Apple app versioning to `v2026.06.26.120`.
- Fixed Web Narrate Ebook so applying a discovery-backed template opens the Discovery source tab, matching the preserved source provenance in the saved template payload.

### 2026.06.26.119

- Advanced visible Apple app versioning to `v2026.06.26.119`.
- Fixed Web Narrate Ebook template apply/save loops so discovery-backed templates keep sanitized source provenance instead of dropping `discovery_state` after the first re-save.

### 2026.06.26.118

- Advanced visible Apple app versioning to `v2026.06.26.118`.
- Fixed Apple Narrate EPUB templates so discovery-backed saved templates reopen the Apple source controls on the Discovery panel while keeping ordinary server/manual EPUB templates on Server.

### 2026.06.26.117

- Advanced visible Apple app versioning to `v2026.06.26.117`.
- Added `make verify-apple-dogfood-pipeline` as a non-physical gate that runs the local Web/Apple cross-surface checkpoint before the shared Apple pipeline verification, with the golden gate layering source-sync before that dogfood gate.

### 2026.06.26.116

- Advanced visible Apple app versioning to `v2026.06.26.116`.
- Fixed the Apple TV interactive reader header so the modern book banner stretches across the top row and reserves enough vertical clearance before the original sentence renders.

### 2026.06.26.115

- Advanced visible Apple app versioning to `v2026.06.26.115`.
- Added `make verify-apple-cross-surface-checkpoint` as a repo-owned non-physical gate that builds Web production/export assets and then runs the Apple local-surface verification before safe checkpoints or explicit attended device deploys.

### 2026.06.26.114

- Advanced visible Apple app versioning to `v2026.06.26.114`.
- Tightened Web and Apple Create source discovery readiness so missing backend-advertised book/video providers stay disabled with a clear message after provider inventory loads, while pre-load fallback controls remain usable.

### 2026.06.26.113

- Advanced visible Apple app versioning to `v2026.06.26.113`.
- Fixed Apple interactive reader slider, Jump To, search, chapter, and bookmark jumps so the target sentence starts rendering immediately while audio seeks and begins playback.
- Fixed the Apple TV interactive reader header so the book banner can stretch across the screen and the transcript reserves the measured header height instead of rendering under the original-language line.
- Tightened Apple interactive reader word taps so sequence taps resolve the controller's track-aware sentence target before seeking, including track switches when the tapped word is on the other lane.

### 2026.06.26.112

- Advanced visible Apple app versioning to `v2026.06.26.112`.
- Guarded Apple interactive reader word taps against stale sequence audio transitions and drift on same-track seeks, so tapping a word rewinds to that word and can switch tracks without an older load moving playback back afterward.

### 2026.06.26.111

- Advanced visible Apple app versioning to `v2026.06.26.111`.
- Hardened Apple interactive reader word taps so sequence playback computes the seek from the tapped language track directly and combined single-track playback reloads the matching original or translation audio before rewinding.
- Exposed the backend sentence splitter mode across Web Narrate Ebook and Apple Create, including defaults, templates, recent-job restore, and pipeline submission overrides.

### 2026.06.26.110

- Advanced visible Apple app versioning to `v2026.06.26.110`.
- Fixed Apple interactive reader word taps outside sequence mode so tapping a word on the other language track explicitly switches the narration mode before rewinding to that word.

### Sentence splitting dry-run

- Added an opt-in `modern` sentence splitter mode with deterministic regex fallback, splitter-mode cache invalidation, and a dry-run comparison utility for checking sentence-count deltas, normalized text coverage, tiny fragments, and max words before changing pipeline defaults.

## 2026-06-25

### 2026.06.25.109

- Advanced visible Apple app versioning to `v2026.06.25.109`.
- Promoted Narrate EPUB discovery into a first-class source panel on Apple Create so server EPUB selection and discovery are available as explicit source modes.
- Matched Web Narrate Ebook with a Source/Discovery tab inside the source step while preserving the existing discovery dialog and prepared EPUB handoff.
- Fixed Apple interactive reader word taps in sequence playback so tapping a word on the other language track rewinds to that word and switches the active audio track when needed.

### 2026.06.25.108

- Advanced visible Apple app versioning to `v2026.06.25.108`.
- Fixed the interactive reader sentence slider so keyboard sentence skips, search jumps, bookmark jumps, chapter jumps, and word taps clear any stale slider draft and keep the header synced to the live sentence.
- Updated paused word taps in the Apple interactive reader to rewind to the tapped word, stay paused, and open lookup for that word.
- Hardened the interactive reader header top inset by measuring the rendered banner height and using it to prevent overlap with the original-language track.

### 2026.06.25.107

- Advanced visible Apple app versioning to `v2026.06.25.107`.
- Fixed the interactive reader header slider layout so the taller header reserves enough space and no longer overlaps the original-language track.
- Updated the header sentence slider to follow the active playback/sequence sentence instead of sticking to the last manually selected sentence.

### 2026.06.25.106

- Advanced visible Apple app versioning to `v2026.06.25.106`.
- Added an iPad/iPhone interactive reader header sentence slider for fast media-player-style jumps across the book.
- Updated word taps so a single tap seeks to that word and starts playback, while a double tap seeks to that word, pauses, and opens the lookup bubble.
- Changed interactive reader sequence navigation so next/previous follows playback order across original and translation tracks instead of staying on the currently playing language track.

### 2026.06.25.105

- Advanced visible Apple app versioning to `v2026.06.25.105`.
- Fixed the interactive reader Jump To input on iPad and iPhone by sanitizing numeric entry, clamping to sentence bounds, and adding keyboard Done/Go actions.
- Fixed interactive book bookmark jumps by preferring stored chunk/time targets and updating the visible sentence selection before falling back to sentence lookup.

### 2026.06.25.104

- Advanced visible Apple app versioning to `v2026.06.25.104`.
- Restored the integrated interactive reader time pill tap action on iPad so it can hide and show timeline details from inside the header banner.
- Made interactive book bookmark adds update immediately during playback, then reconcile with the backend bookmark id after remote sync completes.

### 2026.06.25.103

- Advanced visible Apple app versioning to `v2026.06.25.103`.
- Integrated the interactive reader progress and time pills into the iPad header banner and let the book identity header fill the available row width.
- Added a cover-tap metadata overlay on iPad and iPhone so book title, author, languages, type, and model are available from the reader header.

### 2026.06.25.102

- Advanced visible Apple app versioning to `v2026.06.25.102`.
- Hardened the interactive reader book-job header on physical iPad by removing fit-based generic SwiftUI alternatives from the overlay and erasing the stored header controls type.

### 2026.06.25.101

- Advanced visible Apple app versioning to `v2026.06.25.101`.
- Fixed a physical-iPad crash when opening book jobs by replacing the interactive reader header's runtime `ViewThatFits` generic composition with explicit wide/compact banner branching.

### 2026.06.25.100

- Advanced visible Apple app versioning to `v2026.06.25.100`.
- Apple-saved generated-book and Narrate EPUB templates now include trimmed `title`, `book_title`, and `job_label` metadata, matching submitted Apple book jobs so Web handoff and template reuse show the same book title label.

### 2026.06.25.99

- Advanced visible Apple app versioning to `v2026.06.25.99`.
- Apple interactive reader headers now use adaptive wide and compact identity-banner layouts, keeping the book cover, title, author, metadata pills, and inline controls composed across iPhone, iPad, Apple TV, and Mac Designed for iPad.

### 2026.06.25.98

- Advanced visible Apple app versioning to `v2026.06.25.98`.
- Apple-saved generated-book and Narrate EPUB templates now preserve remote cover artwork as `cover_url` in Web-compatible `book_metadata`, while keeping local/backend cover files in `book_cover_file` just like submitted Apple book jobs.

### 2026.06.25.97

- Advanced visible Apple app versioning to `v2026.06.25.97`.
- Apple-saved generated-book and Narrate EPUB templates now include normalized `book_genres` arrays in their Web-compatible `book_metadata`, matching submitted Apple book jobs and preserving multi-genre metadata through Web handoff and template reuse.

### 2026.06.25.96

- Advanced visible Apple app versioning to `v2026.06.25.96`.
- Apple-saved generated-book and Narrate EPUB templates now include source-language metadata in their Web-compatible `book_metadata`, keeping Apple-to-Web draft handoff and later Apple template reuse aligned with submitted book jobs.

### 2026.06.25.95

- Advanced visible Apple app versioning to `v2026.06.25.95`.
- Apple Create saved-template metadata loading now treats Web `book_metadata` JSON as a shared metadata source, keeping book-only Narrate Ebook templates useful when applied on iPhone, iPad, Apple TV, and Mac Designed for iPad.

### 2026.06.25.94

- Advanced visible Apple app versioning to `v2026.06.25.94`.
- Apple interactive reader headers now route the banner, book cover, title, metadata pills, and inline controls through a dedicated SwiftUI identity banner component with stable UI-test identifiers across iPhone, iPad, Apple TV, and Mac Designed for iPad.

### 2026.06.25.93

- Advanced visible Apple app versioning to `v2026.06.25.93`.
- Apple Narrate EPUB chapter controls now show a clear "Same as start" end-chapter placeholder, keeping loaded chapter ranges and manual-range fallback states easier to read on iPad, iPhone, Apple TV, and Mac Designed for iPad.

### 2026.06.25.92

- Advanced visible Apple app versioning to `v2026.06.25.92`.
- Apple Jobs and Library now track offline export busy state per source row, keeping duplicate taps disabled for the exporting item without blocking export actions for other completed jobs or library entries.

### 2026.06.25.91

- Advanced visible Apple app versioning to `v2026.06.25.91`.
- Web Video Dubbing and Apple YouTube Dub now restore token-free video discovery provenance when applying saved templates, so apply/save loops keep reviewed NAS/manual/YouTube/indexer context instead of dropping it after the first save.

### 2026.06.25.90

- Advanced visible Apple app versioning to `v2026.06.25.90`.
- Apple interactive playback now treats the full reader header as one composed identity area: the banner owns the channel mark, book cover, title, author, item/model pills, and playback controls, while progress pills adapt beside or below it without a redundant outer glass panel.

### 2026.06.25.89

- Advanced visible Apple app versioning to `v2026.06.25.89`.
- Web Video Dubbing and Apple YouTube Dub templates now preserve token-free video discovery provenance, including provider, candidate id, selected paths, rights, and source kind, so Web/Apple handoff loops keep reviewed NAS/manual/YouTube/indexer context without saving candidate tokens.

### 2026.06.25.88

- Advanced visible Apple app versioning to `v2026.06.25.88`.
- Apple interactive and video playback headers now present the banner, cover art, title, author, and info pills as one modern media identity area with stronger material styling, cover fallbacks, and fit-aware metadata rows across iPhone, iPad, Apple TV, and Mac Designed for iPad.

### 2026.06.25.87

- Advanced visible Apple app versioning to `v2026.06.25.87`.
- Web app shell hooks now subscribe to granular Zustand fields/actions instead of whole stores, reducing avoidable rerenders while preserving auth, job, prefill, and player routing behavior.
- Apple YouTube Dub now matches completed Download Station filenames against refreshed manual-download candidates and applies the matching video/subtitle source, shortening the indexer-to-native-job setup loop.
- Apple interactive playback now treats the banner, book cover, title, author, type, and model pills as one media identity block with a fallback cover tile and fit-aware pills across iPhone, iPad, Apple TV, and Mac Designed for iPad.
- Web and Apple video discovery now recognize Download Station handoff metadata when the backend sends explicit providers, booleans, or legacy string flags, keeping reviewed indexer candidates visible across metadata encoding changes.
- Apple Create readiness now reports whether searchable Newznab/Torznab video candidates can be handed to Download Station, separating provider inventory health from the downloader handoff path used by Web and Apple discovery.
- Apple playback no longer shows the upper file/chunk/audio/timing/image count strip on iPhone, iPad, Apple TV, or Mac Designed for iPad; it now keeps the top chrome quiet unless media gaps could affect playback.
- When media gaps are present, Apple playback shows a compact warning banner instead of the old diagnostics counter grid.

### 2026.06.25.86

- Advanced visible Apple app versioning to `v2026.06.25.86`.
- Apple Library, Jobs, and combined search no longer show the redundant upper browse action row; section, search, and filter controls now start the list chrome on iPhone, iPad, Apple TV, and Mac Designed for iPad.
- Moved manual resume sync and logout into Settings so account/session actions remain available without consuming first-screen browse space.

### 2026.06.25.84

- Advanced visible Apple app versioning to `v2026.06.25.84`.
- Apple Library, Jobs, and combined search headers now drop the extra iCloud/sync status strip; refresh stays in the upper row and manual resume sync remains in the account menu, reducing browse chrome clutter on iPhone, iPad, Apple TV, and Mac Designed for iPad.
- Apple video playback now shares the sleep timer pill on iPhone, iPad, Apple TV, and Mac Designed for iPad; timer expiration pauses video playback and tvOS remote focus can move through Search, Bookmarks, Sleep Timer, and the timeline controls.
- Web interactive text and video playback now expose the same 5, 15, 30, and 45 minute sleep timer pattern; expiration pauses narration plus reading music for books and pauses video playback for media jobs.

### 2026.06.25.82

- Advanced visible Apple app versioning to `v2026.06.25.82`.
- Apple interactive playback now has a sleep timer pill with 5, 15, 30, and 45 minute presets on iPhone, iPad, Apple TV, and Mac Designed for iPad; when the timer expires it pauses narration plus the active reading bed.
- Apple playback now hides the media diagnostics file/chunk/timing count strip during healthy playback and only surfaces it when diagnostics report media gaps, reducing upper-bar clutter on iPhone, iPad, Apple TV, and Mac Designed for iPad.

### 2026.06.25.81

- Advanced visible Apple app versioning to `v2026.06.25.81`.
- Apple Now Playing clears cached elapsed-time and duration state when playback metadata is reset, so lock-screen controls re-publish complete timing for the next book or video even when it starts at the same position as the previous item.

### 2026.06.25.80

- Advanced visible Apple app versioning to `v2026.06.25.80`.
- Apple interactive playback keeps the Jump, Search, and Bookmark pills visible across iPhone, iPad, Apple TV, and Mac Designed for iPad even when a book has no language flag metadata, preserving search-result and bookmark jump controls during playback.

### 2026.06.25.79

- Advanced visible Apple app versioning to `v2026.06.25.79`.
- Apple interactive playback now prefetches nearby sentence images around the active transcript position, so image-heavy book chunks feel smoother when revisited or advanced through quickly.
- Apple interactive playback now reuses a bounded token normalization cache across live refreshes and chunk metadata rebuilds, making repeated chunk visits lighter without retaining stale sentence metadata.
- Apple interactive playback bookmark time jumps now wait for the target chunk audio to be ready before seeking, preserving active playback across iPhone, iPad, Apple TV, and Mac Designed for iPad.
- Apple active-job playback now falls back to the regular media snapshot if the initial live-media request is temporarily unavailable, while still preferring live updates for running jobs.
- Apple narration playback now retries one failed stream at the current file/time position and cleans up stall observers across player rebuilds, improving recovery from short network interruptions.
- Apple interactive playback now sanitizes backend word timing windows before transcript highlighting, dropping invalid timings and clamping overlaps within each sentence/file group for smoother reading.
- Apple interactive playback now shows a Retry action when selected chunk transcript metadata fails to load, then reloads the metadata and prepares audio again across iPhone, iPad, Apple TV, and Mac Designed for iPad.
- Apple playback search and bookmark pills now expose stable native identifiers and Apple TV video playback can move focus between Search, Bookmark, and the header controls from the remote.
- Apple Narrate EPUB source choices now stay filtered to real EPUB entries and preserve newest-first backend ordering, matching the Web defaulting behavior more closely.
- Web Video Dubbing and Apple YouTube Dub can now carry a selected Newznab/Torznab indexer candidate directly into the reviewed Download Station handoff via the server-side candidate token, so API-key URLs stay hidden while the user still confirms the task.
- Apple TV lookup read-aloud now cycles focus across visible bubble controls so the remote can reach Read Aloud, and it retries tvOS pronunciation audio-session setup with simpler playback options when the richer spoken-audio session is rejected.

### Acquisition token hardening checkpoint

- Newznab/Torznab discovery now stores raw indexer download URLs in a backend-side acquisition reference, letting `/api/acquisition/jobs` submit reviewed candidate tokens to Download Station without exposing API-key URLs to Web or Apple clients.
- Discovery candidate and prepared artifact tokens are now HMAC-signed before Web or Apple use them, so reviewed acquire/prepare handoffs reject unsigned or tampered payloads while clients continue treating them as implementation-owned strings.
- Acquisition token signing now rejects secret-like payload keys and URL query credentials, keeping future indexer/download handoffs from smuggling API-key URLs through client-visible tokens.

### Open Library Archive bridge checkpoint

- Web Narrate Ebook and Apple Narrate EPUB can now turn Open Library records with Internet Archive identifiers into focused public Archive EPUB discovery results, then use the existing reviewed acquire/prepare flow.
- `/api/acquisition/discover` now accepts repeated `source_id` values for safe provider-specific focused lookups; the Internet Archive adapter validates identifiers and still filters restricted, private, or encrypted items.

### 2026.06.25.70

- Advanced visible Apple app versioning to `v2026.06.25.70`.
- Apple Narrate EPUB now keeps the output/job name aligned with the newly selected EPUB whenever the output field has not been manually edited, preventing a new job from inheriting another book's name.

### 2026.06.25.69

- Advanced visible Apple app versioning to `v2026.06.25.69`.
- Apple TV lookup read-aloud now rejects decoded-but-empty backend pronunciation audio and falls back to platform speech, keeping the Read Aloud control from going silent when backend TTS returns unusable audio.

### Apple template roundtrip checkpoint

- Apple Create now restores saved ebook `discovery_state` when applying Narrate EPUB or generated-book templates, preserving token-free acquisition provenance for the next save, submit, or Web handoff.

### Discovery template checkpoint

- Web Narrate Ebook and Apple Narrate EPUB templates now persist token-free discovery provenance (`discovery_state`) for reviewed ebook candidates, so saved Create drafts can remember which local/public/metadata source was selected without storing acquisition tokens or credentials.

### Backend timing validation checkpoint

- Chunk export timing validation now derives sentence windows from original and translation tracks and fails the post-export summary when sentence gates overlap, giving Web and Apple playback/read-aloud surfaces a clearer signal before a chunk can skip or double-read text.

### 2026.06.25.68

- Advanced visible Apple app versioning to `v2026.06.25.68`.
- Apple lookup read-aloud now falls back to platform speech when backend pronunciation audio cannot start, so Apple TV, iPhone, iPad, and voice previews do not fail silently on undecodable or refused audio playback.

### 2026.06.25.67

- Advanced visible Apple app versioning to `v2026.06.25.67`.
- Apple TV and iPhone/iPad lookup read-aloud now pauses active playback before speaking, and cached narration playback stops any active pronunciation audio before resuming the book or video track.

### 2026.06.25.66

- Advanced visible Apple app versioning to `v2026.06.25.66`.
- Apple TV lookup read-aloud now always has a platform speech fallback, even when the lookup language is a backend label that cannot be mapped to a specific AVSpeech voice code.

### 2026.06.25.65

- Advanced visible Apple app versioning to `v2026.06.25.65`.
- Apple TV lookup read-aloud now falls back to platform speech after a short backend pronunciation timeout and keeps AVFoundation speech operations on the main actor, so slow backend TTS no longer makes lookup audio feel dead.

### 2026.06.25.64

- Advanced visible Apple app versioning to `v2026.06.25.64`.
- Lookup-cache endpoints now preserve authorization failures instead of treating them as cache misses, while still keeping missing jobs or missing caches as graceful MyLinguist fallback paths for Web and Apple playback.

### 2026.06.25.63

- Advanced visible Apple app versioning to `v2026.06.25.63`.
- Apple Narrate EPUB now resolves the selected server EPUB through one shared helper, so the right-side Job Settings chapter controls show the same selected-book detail as the source picker on wide iPad, iPhone, tvOS, and local Mac iPad-style surfaces.

### 2026.06.25.62

- Advanced visible Apple app versioning to `v2026.06.25.62`.
- Apple Narrate EPUB keeps the server picker usable when only manual path fallback is available, adds folder context to nested NAS EPUB choices, and shows the selected server EPUB detail beside Load Chapters.

### 2026.06.25.61

- Advanced visible Apple app versioning to `v2026.06.25.61`.
- Chunk exports now persist post-export timing validation for original and translation tracks, making overlap and duration drift visible before Web or Apple playback debugging has to guess.

### 2026.06.25.60

- Advanced visible Apple app versioning to `v2026.06.25.60`.
- Apple TV lookup read-aloud controls now use native focusable buttons, restoring reliable remote Select activation for cached narration playback.
- Apple Create readiness now validates the acquisition provider registry for book/video discovery provider IDs, media/capability shape, and attended Z-Library policy before simulator journeys.

### 2026.06.25.59

- Advanced visible Apple app versioning to `v2026.06.25.59`.
- Web Video Dubbing and Apple YouTube Dub discovery now derive video-capable provider choices from the backend registry while preserving NAS, manual downloads, YouTube search, and Indexers ordering.

### 2026.06.25.58

- Advanced visible Apple app versioning to `v2026.06.25.58`.
- Apple Create readiness now opens Narrate EPUB discovery, selects the attended Z-Library provider from the backend-driven source picker, and asserts the disabled-policy message before moving on to language and media-job defaults.

### 2026.06.25.57

- Advanced visible Apple app versioning to `v2026.06.25.57`.
- Web and Apple ebook discovery now derive book-capable provider choices from the backend registry while preserving familiar ordering, labels, and disabled-provider policy messages.
- Apple TV lookup read-aloud now configures the tvOS playback audio session before synthesized pronunciation audio or system speech fallback.

### 2026.06.25.56

- Advanced visible Apple app versioning to `v2026.06.25.56`.
- Web and Apple ebook discovery now show Z-Library as an attended-import-only path with direct automation disabled, guiding authorized EPUBs through Manual downloads or the backend books folder.

### 2026.06.25.55

- Advanced visible Apple app versioning to `v2026.06.25.55`.
- Apple Narrate EPUB now keeps the server EPUB picker visible with a loaded-source summary and skips generated/runtime chapter lookups that cannot resolve through the backend EPUB folder.

### 2026.06.25.54

- Advanced visible Apple app versioning to `v2026.06.25.54`.
- Web Narrate Ebook and Apple Narrate EPUB now clear stale source metadata when the selected EPUB changes, preventing a new job from inheriting the previous book title or catalog details.
- Apple Narrate EPUB chapter loading now keeps source and loaded-range states clearer, and Apple TV video lookup can play from cached narration timing again.

### 2026.06.25.53

- Advanced visible Apple app versioning to `v2026.06.25.53`.
- Web Narrate Ebook and Apple Narrate EPUB now use the shared acquisition artifact prepare endpoint before filling selected discovery source paths.

### 2026.06.25.52

- Advanced visible Apple app versioning to `v2026.06.25.52`.
- Acquisition artifacts now have a shared prepare endpoint that resolves reviewed local or acquired sources into existing Create form fields for Web and Apple clients.

### 2026.06.25.51

- Advanced visible Apple app versioning to `v2026.06.25.51`.
- Sentence splitting now recognizes lowercase sentence starts and ASCII quoted dialogue after terminal punctuation while keeping ellipsis continuations and inline dialogue tags intact; refined sentence caches invalidate through splitter version `regex-v5`.

### 2026.06.25.50

- Advanced visible Apple app versioning to `v2026.06.25.50`.
- Apple generated-book and Narrate EPUB submissions now preserve applied Open Library provenance in job metadata, including work/edition IDs, catalog lookup hints, and cover URLs while keeping visible form edits authoritative.

### 2026.06.25.49

- Advanced visible Apple app versioning to `v2026.06.25.49`.
- Open Library discovery candidates can now apply book metadata into Web Narrate Ebook and Apple Narrate EPUB without choosing or acquiring an EPUB source.

### 2026.06.25.48

- Advanced visible Apple app versioning to `v2026.06.25.48`.
- Open Library is now a shared metadata-only ebook discovery provider for Web Narrate Ebook and Apple Narrate EPUB, showing reviewable catalog matches without attempting EPUB acquisition.

### 2026.06.25.38

- Advanced visible Apple app versioning to `v2026.06.25.38`.
- Apple YouTube Dub discovery can now search configured manual download folders for user-authorized NAS/Download Station video files and reuse discovered subtitle hints.

### 2026.06.25.37

- Advanced visible Apple app versioning to `v2026.06.25.37`.
- Apple Narrate EPUB discovery now uses the shared acquisition provider registry to disable unavailable ebook source searches and explain missing backend source roots before users get an empty result list.
- Web Narrate Ebook discovery now also reads provider readiness, skipping unavailable ebook source searches and showing the same source-root guidance for local/manual discovery providers.

### 2026.06.25.36

- Advanced visible Apple app versioning to `v2026.06.25.36`.
- Apple interactive playback now falls back to chunk-local translation timing tracks when job-level timing is unavailable, matching the existing original-track fallback and preserving word highlights in multi-sentence chunks.

### 2026.06.25.35

- Advanced visible Apple app versioning to `v2026.06.25.35`.
- Web and Apple Narrate Ebook discovery can now search configured manual download folders for user-authorized EPUBs downloaded through Safari, Download Station, or another attended workflow.
- The acquisition provider registry now advertises a token-safe manual downloads provider for backend-visible EPUB/video inboxes without scraping browser sessions or exposing credentials.

### 2026.06.25.34

- Advanced visible Apple app versioning to `v2026.06.25.34`.
- YouTube acquisition discovery now returns token-safe quota, rate-limit, and authorization messages for configured providers instead of collapsing API failures into a generic provider error.

### 2026.06.25.33

- Advanced visible Apple app versioning to `v2026.06.25.33`.
- Web and Apple YouTube search surfaces now read the token-safe acquisition provider registry, disable YouTube search when the backend is not configured, and keep direct URL/NAS paths usable.

### 2026.06.25.32

- Advanced visible Apple app versioning to `v2026.06.25.32`.
- Web YouTube downloads can now search configured YouTube metadata results from the backend, select a result into the existing URL field, and continue through subtitle inspection, subtitle selection, and video download review.

### 2026.06.25.31

- Advanced visible Apple app versioning to `v2026.06.25.31`.
- Apple YouTube Dub discovery can now switch between NAS videos and configured YouTube search metadata, sending reviewed YouTube results into the existing metadata lookup flow before any download or dubbing step.

### 2026.06.25.30

- Advanced visible Apple app versioning to `v2026.06.25.30`.
- Web Video Dubbing discovery can now switch between NAS videos and configured YouTube search metadata, sending reviewed YouTube results into the existing metadata lookup flow before any download or dubbing step.

### 2026.06.25.29

- Advanced visible Apple app versioning to `v2026.06.25.29`.
- Apple Narrate EPUB discovery can now switch between local EPUBs and Gutenberg catalog results, acquiring reviewed Gutenberg EPUBs before filling the standard server EPUB path.

### 2026.06.25.28

- Advanced visible Apple app versioning to `v2026.06.25.28`.
- Web Narrate Ebook discovery can now switch between local EPUBs and Gutenberg catalog results, acquiring reviewed Gutenberg EPUBs before filling the standard input path.

### 2026.06.25.27

- Advanced visible Apple app versioning to `v2026.06.25.27`.
- Added reviewed Gutenberg EPUB acquisition at `/api/acquisition/acquire`, saving public catalog EPUBs into the configured books root and exposing the path through Web and Apple API clients plus runtime readiness metadata.

### 2026.06.25.26

- Advanced visible Apple app versioning to `v2026.06.25.26`.
- Added an explicit Project Gutenberg/Gutendex acquisition discovery provider that returns public catalog ebook candidates with author, language, cover, source URL, and EPUB link metadata for reviewed acquisition.

### 2026.06.25.25

- Advanced visible Apple app versioning to `v2026.06.25.25`.
- Acquisition discovery now clamps internal result limits, short-circuits zero-limit calls before scanning provider roots, and rejects non-discovery providers such as Download Station until a reviewed handoff implementation exists.

### 2026.06.25.24

- Advanced visible Apple app versioning to `v2026.06.25.24`.
- Apple Create now keeps EPUB and YouTube Dub acquisition discovery responses isolated, preventing stale book/video search results or errors from leaking when switching creation modes.

### 2026.06.25.23

- Advanced visible Apple app versioning to `v2026.06.25.23`.
- Apple YouTube Dub now has a Discover Video Sources control backed by `/api/acquisition/discover`, letting iPhone, iPad, and Apple TV fill the existing NAS video/subtitle fields from backend-visible NAS candidates.

### 2026.06.25.22

- Advanced visible Apple app versioning to `v2026.06.25.22`.
- Web Video Dubbing now has a Discover video sources panel backed by `/api/acquisition/discover`, letting backend-visible NAS video candidates fill the existing video/subtitle selection without changing dub job payloads.

### 2026.06.25.21

- Advanced visible Apple app versioning to `v2026.06.25.21`.
- Apple Narrate EPUB now has a Discover Sources control backed by the shared acquisition discovery endpoint, letting iPhone, iPad, and Apple TV fill the existing server EPUB path from backend-visible local candidates.
- The public runtime descriptor now advertises `/api/acquisition/discover` alongside acquisition providers so Apple settings and readiness checks can detect discovery contract drift.

### 2026.06.25.20

- Advanced visible Apple app versioning to `v2026.06.25.20`.
- Web Narrate Ebook now has a Discovery sources dialog that searches the backend acquisition discovery contract for local EPUB candidates and fills the existing input path without changing submission payloads.

### 2026.06.25.19

- Advanced visible Apple app versioning to `v2026.06.25.19`.
- Added `/api/acquisition/discover` for editor/admin source discovery across backend-visible EPUBs, NAS videos with subtitle hints, and configured YouTube Data API metadata search while keeping actual downloads as a separate reviewed step.
- Hardened sentence splitting so closing quotes after sentence punctuation are preserved instead of silently dropped, with content-index regression coverage for approximate/truncated chapter ranges.

### 2026.06.25.18

- Advanced visible Apple app versioning to `v2026.06.25.18`.
- Added the first backend acquisition provider contract at `/api/acquisition/providers`, exposing token-safe lawful discovery provider metadata for local EPUBs, NAS videos, YouTube URL/search, Download Station/indexer handoff, and planned public/open ebook sources.

### 2026.06.25.17

- Advanced visible Apple app versioning to `v2026.06.25.17`.
- Web and Apple sequence playback now fills missing per-sentence gates from that sentence's phase durations, so mixed chunks keep every original/translation sentence in the plan instead of dropping phase-only sentences after the first gated one.

### 2026.06.25.16

- Advanced visible Apple app versioning to `v2026.06.25.16`.
- Documented the lawful discovery acquisition layer for YouTube, NAS/Download Station, public/open ebook catalogs, metadata enrichment, and Web/Apple Create handoff, with Z-Library/shadow-library automation explicitly out of scope.
- Apple interactive playback now reads chunk-local original timing tokens before legacy global fallback so iPad, iPhone, and Apple TV preserve per-word original highlights from chunk metadata.

### 2026.06.25.15

- Advanced visible Apple app versioning to `v2026.06.25.15`.
- Moved the shared pipeline LLM model inventory route onto FastAPI's threadpool so Web and Apple Create model pickers do not block the async server while provider discovery runs.

### 2026.06.25.14

- Advanced visible Apple app versioning to `v2026.06.25.14`.
- Canonicalized saved creation-template delete responses and skipped storage reads for empty normalized template IDs so Web/Apple draft cleanup stays predictable.

### 2026.06.25.13

- Advanced visible Apple app versioning to `v2026.06.25.13`.
- Hardened the release contract so the latest Markdown changelog day, Apple in-app changelog day, visible date label, and shipped release version all have to agree on today's build date.

### 2026.06.25.12

- Advanced visible Apple app versioning to `v2026.06.25.12`.
- Optimized the shared YouTube NAS library picker used by Web Video Dubbing and Apple Create so linked-job tagging prefilters unrelated stored jobs by filename before path normalization and reuses each discovered video token while building the response.

### 2026.06.25.11

- Advanced visible Apple app versioning to `v2026.06.25.11`.
- Apple Create now shares one Narrate EPUB chapter-range control between the source pane and the wide iPad/Mac job-settings pane, keeping Load Chapters, chapter pickers, range summaries, and sentence-window updates consistent.

### 2026.06.25.10

- Advanced visible Apple app versioning to `v2026.06.25.10`.
- Expanded the shared Web Create intake gate so Narrate Ebook content-index chapter loading, generated-source skips, consecutive chapter selection, backend error surfacing, and estimated range/duration labels are directly covered.

### 2026.06.25.9

- Advanced visible Apple app versioning to `v2026.06.25.9`.
- Apple Daily Changelog now renders the header from the latest changelog day and the release contract requires that latest Swift changelog day to match the shipped release, making today’s version entry harder to miss or drift.

### 2026.06.25.8

- Advanced visible Apple app versioning to `v2026.06.25.8`.
- Expanded the shared Web Create intake gate so backend voice inventory matching, region/base language-code normalization, per-language preview overrides, and voice inventory failures are directly covered.

### 2026.06.25.7

- Advanced visible Apple app versioning to `v2026.06.25.7`.
- Expanded the shared Web Create intake gate so backend-visible EPUB discovery, latest-server-book defaults, generated-source skips, upload validation, and narration-history start defaults are directly covered.

### 2026.06.25.6

- Advanced visible Apple app versioning to `v2026.06.25.6`.
- Expanded the shared Web job-progress pipeline gate so book and subtitle job settings summaries stay covered alongside stage health and generated-file utilities.

### 2026.06.25.5

- Advanced visible Apple app versioning to `v2026.06.25.5`.
- Expanded the shared Web Library pipeline gate so it now covers Library page metadata, LibraryList helpers, row media/actions/status components, and resume badge behavior before full Vitest/build checks.

### 2026.06.25.4

- Advanced visible Apple app versioning to `v2026.06.25.4`.
- Apple Create now keeps backend-scoped server EPUB choices visible even when source metadata omits the `.epub` suffix or display name, restoring available-book picker rows across iPad, iPhone, and Apple TV.
- Re-synchronized the release changelog, Info plist versions, Xcode build settings, and in-app changelog data so today’s build appears as a June 25 release.

## 2026-06-24

### 2026.06.24.27

- Advanced visible Apple app versioning to `v2026.06.24.27`.
- Apple Create now exposes advanced metadata JSON editors for subtitle and YouTube jobs so iPad/iPhone can review and apply full nested metadata payloads beyond the high-value native fields.

### 2026.06.24.26

- Advanced visible Apple app versioning to `v2026.06.24.26`.
- Clarified Apple generated-book Create labels so continuation context appears as source-book title, author, genre, and summary instead of generic metadata fields.

### 2026.06.24.25

- Advanced visible Apple app versioning to `v2026.06.24.25`.
- Apple Create generated-book jobs now accept source-book title, author, genre, and summary context so iPad/iPhone can start continuation-style books with explicit source metadata.

### 2026.06.24.24

- Advanced visible Apple app versioning to `v2026.06.24.24`.
- The guarded Apple physical-device update helper now runs a non-mutating CoreDevice health preflight before confirmed installs, while keeping installed-app metadata verification as a separate post-install check.

### 2026.06.24.23

- Advanced visible Apple app versioning to `v2026.06.24.23`.
- Apple Jobs and Library now show a visible offline-export progress overlay while the backend prepares an offline player archive.

### 2026.06.24.22

- Advanced visible Apple app versioning to `v2026.06.24.22`.
- Apple Jobs rows now show a compact running-job health line with the latest backend stage, elapsed runtime, and ETA from progress events.

### 2026.06.24.21

- Advanced visible Apple app versioning to `v2026.06.24.21`.
- Apple Create now routes successful submissions directly to the created job in Jobs, selects the matching Jobs category, and starts Jobs auto-refresh so newly submitted book, subtitle, and video jobs are immediately visible.

### 2026.06.24.20

- Advanced visible Apple app versioning to `v2026.06.24.20`.
- Apple Create Narrate EPUB now reuses prior narration job audio, output, translation, transliteration, lookup-cache, and chunking settings while still preserving any fields edited in the current form.

### 2026.06.24.19

- Advanced visible Apple app versioning to `v2026.06.24.19`.
- Added repo-owned Make wrappers for the shared Apple device app pipeline contract, backend, source-sync, and non-physical shared preflight commands so ebook-tools can dogfood the reusable pipeline from its own checkout.

### 2026.06.24.18

- Advanced visible Apple app versioning to `v2026.06.24.18`.
- Added `make verify-apple-local-surfaces`, a single non-physical verification gate that runs Apple contracts and then compiles all local Apple surfaces before any attended physical-device update.

### 2026.06.24.17

- Advanced visible Apple app versioning to `v2026.06.24.17`.
- Added `make build-apple-local-surfaces`, a single non-physical build gate that chains iPhone simulator, iPad simulator, Apple TV simulator, and local Mac Designed for iPad/iPhone compile checks before attended device deploys.

### 2026.06.24.16

- Advanced visible Apple app versioning to `v2026.06.24.16`.
- Added repo-owned `make build-apple-iphone-simulator`, `make build-apple-ipad-simulator`, and `make build-apple-ios-simulators` compile gates so iPhone and iPad simulator builds can run without launching full journeys or touching physical devices.

### 2026.06.24.15

- Advanced visible Apple app versioning to `v2026.06.24.15`.
- Added a repo-owned `make build-apple-tvos-simulator` compile gate for the Apple TV app so tvOS-only Swift regressions can be caught before full XCUITest journeys or physical-device deploys.

### 2026.06.24.14

- Advanced visible Apple app versioning to `v2026.06.24.14`.
- Apple Library rows now expose read-only Source Details on iPhone, iPad, and Apple TV with stored-source, file, type, path, status, and media diagnostics.

### 2026.06.24.13

- Advanced visible Apple app versioning to `v2026.06.24.13`.
- Apple Library source replacement now opens a review sheet before upload and accepts the same common book/video source extensions as Web.

### 2026.06.24.12

- Advanced visible Apple app versioning to `v2026.06.24.12`.
- Apple Library rows on iPhone and iPad now expose an Edit Metadata sheet for title, author, genre, language, and ISBN, using the same backend PATCH contract as Web.
- iPad and local Mac Designed for iPad Create now keep generated-book sentence count plus Narrate EPUB output and sentence-range settings in the right-hand job settings pane instead of the left setup pane.

### 2026.06.24.10

- Advanced visible Apple app versioning to `v2026.06.24.10`.
- Apple Library rows can now call the shared backend external metadata enrichment endpoint and refresh the row with the returned title, cover, genre, ISBN, and source details.

### 2026.06.24.9

- Advanced visible Apple app versioning to `v2026.06.24.9`.
- Jobs and Library rows on Apple surfaces can now request the shared backend offline-player export zip and open the returned download URL, matching the Web export action for completed media.

### 2026.06.24.8

- Advanced visible Apple app versioning to `v2026.06.24.8`.
- On iPad and local Mac Designed for iPad, Apple Create now keeps the navigation rail compact and reserves the wide right-hand detail area for language, narration, output, status, and submit settings.

### 2026.06.24.7

- Advanced visible Apple app versioning to `v2026.06.24.7`.
- Apple Create subtitle and YouTube TV metadata now show and edit TVMaze poster/still artwork URLs, expose the YouTube thumbnail URL, and include TMDB/IMDb ID fields before submission.

### 2026.06.24.6

- Advanced visible Apple app versioning to `v2026.06.24.6`.
- Apple Create on iPad gives the right-hand job settings pane priority over the setup pane and adds subtitle/YouTube metadata cache clearing controls backed by the shared runtime contract.

### 2026.06.24.5

- Advanced visible Apple app versioning to `v2026.06.24.5`.
- Apple Create subtitle metadata lookup now exposes an editable lookup filename before Lookup or Refresh, matching the Web metadata loader for renamed or manually selected subtitle sources.

### 2026.06.24.4

- Advanced visible Apple app versioning to `v2026.06.24.4`.
- Apple Create subtitle jobs can now load TV metadata before submission, edit job label/show/episode fields on iPad, and send the enriched metadata JSON with the job.

### 2026.06.24.3

- Advanced visible Apple app versioning to `v2026.06.24.3`.
- Apple Create YouTube Dub can now load TV and YouTube metadata before submission, edit the key title/channel/series fields on iPad, and send the enriched metadata payload with the job.

### 2026.06.24.2

- Advanced visible Apple app versioning to `v2026.06.24.2`.
- Apple Create YouTube Dub can now inspect embedded subtitle streams in a selected NAS video, extract text subtitle tracks through the backend, refresh the NAS library, and select the extracted subtitle for the job.

### 2026.06.24.1

- Advanced visible Apple app versioning to `v2026.06.24.1`.
- iPad and local Mac Designed for iPad Create now use a two-column detail editor, keeping source/setup fields on the left and narration, output, status, and submit settings on the right.

## 2026-06-23

### 2026.06.23.96

- Advanced visible Apple app versioning to `v2026.06.23.96`.
- On iPad and local Mac Designed for iPad, Apple Create now keeps the job type and creation settings in the detail panel instead of spending sidebar space on job settings.

### 2026.06.23.95

- Advanced visible Apple app versioning to `v2026.06.23.95`.
- Apple Create generated-book mode now reuses recent generated-book prompt, language, voice, narration, output, lookup, and image defaults without borrowing Narrate EPUB history.

### 2026.06.23.94

- Advanced visible Apple app versioning to `v2026.06.23.94`.
- Apple Create now mirrors Web rerun behavior for untouched subtitle and YouTube dubbing jobs by reusing recent sources, time offsets, translation settings, and video tuning defaults.

### 2026.06.23.93

- Advanced visible Apple app versioning to `v2026.06.23.93`.
- Apple Create subtitle jobs now remember the Show Original preference per API/user scope, matching Web's returning-user subtitle default.

### 2026.06.23.92

- Advanced visible Apple app versioning to `v2026.06.23.92`.
- Apple Create YouTube dubbing now exposes and remembers the NAS base directory, matching Web's alternate video-root refresh flow.

### 2026.06.23.91

- Advanced visible Apple app versioning to `v2026.06.23.91`.
- Apple Create now remembers shared input language, target languages, and lookup-cache defaults per API/user scope across generated book, Narrate EPUB, subtitle, and video jobs.

### 2026.06.23.90

- Advanced visible Apple app versioning to `v2026.06.23.90`.
- Apple Create now remembers the last YouTube dubbing NAS video/subtitle selection per API/user scope and restores it when those files are still available.

### 2026.06.23.89

- Advanced visible Apple app versioning to `v2026.06.23.89`.
- Apple Create subtitle jobs now decode source modification timestamps and default to the latest usable SRT/VTT source, matching Web source-selection behavior.

### 2026.06.23.88

- Advanced visible Apple app versioning to `v2026.06.23.88`.
- Apple Create now reuses recent book/narration job history for untouched Narrate EPUB defaults, including input/base paths, resume start sentence, languages, and lookup-cache preference.

### 2026.06.23.87

- Advanced visible Apple app versioning to `v2026.06.23.87`.
- `/api/pipelines/files` now returns EPUB metadata and sorts backend-visible EPUBs newest-first, so Web and Apple Create auto-fill the latest NAS ebook when no source was edited.
- The local macOS Designed for iPad/iPhone build helper now supports dry-run/destination inspection and reports the Xcode-resolved app path.

### 2026.06.23.86

- Advanced visible Apple app versioning to `v2026.06.23.86`.
- Apple Create now loads the shared TTS voice inventory, adds language-matched voice choices for source/target narration, and previews selected voices through the backend audio synthesis route.

### 2026.06.23.85

- Advanced visible Apple app versioning to `v2026.06.23.85`.
- Apple Create now loads backend subtitle sources and NAS YouTube/video library entries, with source pickers that prefill subtitle jobs and YouTube dubbing jobs without manual path entry.

### 2026.06.23.84

- Advanced visible Apple app versioning to `v2026.06.23.84`.
- Added a repeatable local macOS Designed for iPad/iPhone build target plus a guarded command-line helper for unattended iPhone/iPad build-install updates when explicitly confirmed.

### 2026.06.23.83

- Advanced visible Apple app versioning to `v2026.06.23.83`.
- Apple Create Narrate EPUB now loads backend-visible EPUBs from `/api/pipelines/files`, offers a server EPUB picker, and auto-fills the preferred or first NAS EPUB when the source is still empty.

### 2026.06.23.82

- Advanced visible Apple app versioning to `v2026.06.23.82`.
- Web and Apple Create chapter loading now keeps runtime ingestion caches separate for same-named EPUBs in different folders, preventing stale chapter data from another source file.

### 2026.06.23.81

- Advanced visible Apple app versioning to `v2026.06.23.81`.
- Web and Apple Create chapter loading now invalidates cached refined sentences when the source EPUB changes, keeping chapter ranges fresh after file edits or replacements.

### 2026.06.23.80

- Advanced visible Apple app versioning to `v2026.06.23.80`.
- Web and Apple Create chapter loading now reuses a validated backend content-index cache, avoiding repeated EPUB section parsing when users reopen the chapter picker.

### 2026.06.23.79

- Advanced visible Apple app versioning to `v2026.06.23.79`.
- Apple Create now accepts the same backend default aliases as Web creation surfaces for translation providers and transliteration modes, including `gtrans`, `googletranslate`, `ollama`, and `python-module`.

### 2026.06.23.78

- Advanced visible Apple app versioning to `v2026.06.23.78`.
- Web Subtitle Tool Jobs presentation now lives in a focused module with direct pipeline coverage for download-link resolution, metadata labels, retry summaries, and narrated-library move eligibility.

### 2026.06.23.77

- Advanced visible Apple app versioning to `v2026.06.23.77`.
- Web Subtitle Tool Jobs helpers now live in a focused module with direct pipeline coverage for retry summaries, generated subtitle files, missing-result selection, and newest-first ordering.

### 2026.06.23.76

- Advanced visible Apple app versioning to `v2026.06.23.76`.
- Web Subtitle Tool TV metadata draft helpers now live in a focused module with direct pipeline coverage for record coercion, editable metadata copying, text cleanup, and episode-code formatting.

### 2026.06.23.75

- Advanced visible Apple app versioning to `v2026.06.23.75`.
- Web Subtitle Tool source selection now lives in a focused module with direct pipeline coverage for ASS avoidance, latest-source picking, and metadata source labels.

### 2026.06.23.74

- Advanced visible Apple app versioning to `v2026.06.23.74`.
- Web Subtitle Tool submitted-job feedback formatting now lives in a focused module so user-visible creation summaries stay pinned independently from the page shell.

### 2026.06.23.73

- Advanced visible Apple app versioning to `v2026.06.23.73`.
- Web Subtitle Tool backend language-default mapping now lives in a focused module so target-language options and default input language stay pinned outside the page shell.

### 2026.06.23.72

- Advanced visible Apple app versioning to `v2026.06.23.72`.
- Web Subtitle Tool rerun and prefill mapping now lives in a focused module so existing-job recreation stays pinned independently from the page shell.

### 2026.06.23.71

- Advanced visible Apple app versioning to `v2026.06.23.71`.
- Web Subtitle Tool submit and timecode normalization helpers now live in a focused module so creation payload tests target the Web-to-Apple parity contract directly.

### 2026.06.23.70

- Advanced visible Apple app versioning to `v2026.06.23.70`.
- Web Subtitle Tool submit orchestration now lives in a focused hook with coverage for backend request handoff, field normalization, success feedback, intake refresh, and failure cleanup.

### 2026.06.23.69

- Advanced visible Apple app versioning to `v2026.06.23.69`.
- Web Subtitle Tool submit status now lives in a focused hook with coverage for queue-capacity rejection, request failures, and submit busy-state transitions.

### 2026.06.23.68

- Advanced visible Apple app versioning to `v2026.06.23.68`.
- Web Subtitle Tool tab state and newest-first job sorting now live in a focused hook with coverage for tab changes and Jobs panel ordering.

### 2026.06.23.67

- Advanced visible Apple app versioning to `v2026.06.23.67`.
- Web Subtitle Tool processing options now live in a focused hook with coverage for form defaults and prefill/normalization setters.

### 2026.06.23.66

- Advanced visible Apple app versioning to `v2026.06.23.66`.
- Web Subtitle Tool source mode and upload-file state now live in a focused hook with coverage for ASS-source detection, upload labels, and stale error clearing.

### 2026.06.23.65

- Advanced visible Apple app versioning to `v2026.06.23.65`.
- Web Subtitle Tool submit feedback now lives in a focused hook with coverage for submitted summary formatting and empty optional details.

### 2026.06.23.64

- Advanced visible Apple app versioning to `v2026.06.23.64`.
- Web Subtitle Tool language state now lives in a focused hook with coverage for shared preferences, backend target-language options, and normalized input/target handlers.

### 2026.06.23.63

- Advanced visible Apple app versioning to `v2026.06.23.63`.
- Web Subtitle Tool rerun/prefill application now lives in a focused hook with coverage for full, partial, absent, and updated parameter snapshots.

### 2026.06.23.62

- Advanced visible Apple app versioning to `v2026.06.23.62`.
- Web Subtitle Tool show-original subtitle preference now lives in a focused hook with coverage for stored values, persistence, and storage failures.

### 2026.06.23.61

- Advanced visible Apple app versioning to `v2026.06.23.61`.
- Web Subtitle Tool backend language-default loading now lives in a focused hook with coverage for target lists, default input language, failed fetches, and stale responses.

### 2026.06.23.60

- Advanced visible Apple app versioning to `v2026.06.23.60`.
- Web Subtitle Tool model-option loading now lives in a focused hook with coverage for success, empty, failed, and late-response flows.

### 2026.06.23.59

- Advanced visible Apple app versioning to `v2026.06.23.59`.
- Web Subtitle Tool completed-result fetching now lives in a focused hook with coverage for dedupe, partial failures, and late-response cancellation.

### 2026.06.23.58

- Advanced visible Apple app versioning to `v2026.06.23.58`.
- Web Subtitle Tool source listing, selection preservation, refresh, and delete state now live in a focused hook with coverage for empty, failed, cancelled, and confirmed flows.

### 2026.06.23.57

- Advanced visible Apple app versioning to `v2026.06.23.57`.
- Web Subtitle Tool TV metadata lookup state now lives in a focused hook with stale-request and draft-edit coverage, shrinking the page shell while preserving the existing metadata workflow.

### 2026.06.23.56

- Advanced visible Apple app versioning to `v2026.06.23.56`.
- Web Subtitle Tool and Video Dubbing now reuse the Create job-intake status callout and disable new submissions when the backend queue is at capacity.

### 2026.06.23.55

- Advanced visible Apple app versioning to `v2026.06.23.55`.
- Web and Apple Create now show delayed job count plus soft and hard queue limits in the job intake status.

### 2026.06.23.54

- Advanced visible Apple app versioning to `v2026.06.23.54`.
- Web and Apple Create now show a visible "Checking job intake..." state while the queue snapshot is loading.

### 2026.06.23.53

- Advanced visible Apple app versioning to `v2026.06.23.53`.
- Web Create now refreshes backend job intake status only after a successful enqueue, matching the Apple Create behavior and avoiding misleading refreshes after rejected submissions.

### 2026.06.23.52

- Advanced visible Apple app versioning to `v2026.06.23.52`.
- Web and Apple Create now refresh backend job intake status after successful submission, keeping queue pressure counts current after enqueue.

### 2026.06.23.51

- Advanced visible Apple app versioning to `v2026.06.23.51`.
- Web and Apple Create now show backend job intake status before submission, warning under queue pressure and blocking submit when the backend is at capacity.

### 2026.06.23.50

- Advanced visible Apple app versioning to `v2026.06.23.50`.
- Web admin System status now shows backend job intake pressure, pending depth, and running jobs before long job submissions.

### 2026.06.23.49

- Advanced visible Apple app versioning to `v2026.06.23.49`.
- Apple Create on iPhone and iPad now includes an Open Web Create handoff that deep-links to the matching advanced Web creation surface.

### 2026.06.23.48

- Advanced visible Apple app versioning to `v2026.06.23.48`.
- Apple generated-book and Narrate EPUB creation now preserve multi-target backend defaults in the visible Additional target languages field.

### 2026.06.23.47

- Advanced visible Apple app versioning to `v2026.06.23.47`.
- Web book narration now preserves multi-target defaults from persisted preferences, backend defaults, and latest-job settings in the visible Additional target languages field.

### 2026.06.23.46

- Advanced visible Apple app versioning to `v2026.06.23.46`.
- Web book narration rerun/prefill now preserves additional target languages instead of collapsing multi-target history back to a single target.

### 2026.06.23.45

- Advanced visible Apple app versioning to `v2026.06.23.45`.
- Web book narration now exposes additional target languages and submits selected plus manual targets as a de-duplicated multi-target list, matching Apple Create behavior.

### 2026.06.23.44

- Advanced visible Apple app versioning to `v2026.06.23.44`.
- Apple generated-book and Narrate EPUB creation now expose per-target-language voice override pickers, matching the Web voice override payload shape while preserving the global target voice fallback.

### 2026.06.23.43

- Advanced visible Apple app versioning to `v2026.06.23.43`.
- Apple Narrate EPUB end-sentence entry now uses punctuation-capable input on iPhone and iPad, making Web-aligned `+offset` windows practical from the software keyboard.

### 2026.06.23.42

- Advanced visible Apple app versioning to `v2026.06.23.42`.
- Apple generated-book and Narrate EPUB creation now show Web-aligned estimated audio duration, and Narrate EPUB accepts `+offset` end-sentence windows before submit.

### 2026.06.23.41

- Advanced visible Apple app versioning to `v2026.06.23.41`.
- Apple Narrate EPUB chapter selection now supports a consecutive start-to-end chapter range, matching the Web processing-window behavior.

### 2026.06.23.40

- Advanced visible Apple app versioning to `v2026.06.23.40`.
- Apple Narrate EPUB creation can now load a server EPUB chapter index and apply a selected chapter range to the submitted sentence window.

### 2026.06.23.39

- Advanced visible Apple app versioning to `v2026.06.23.39`.
- Apple Create now derives Web-aligned output slugs from source filenames, stripping final file extensions from EPUB, subtitle, and video paths before submission.

### 2026.06.23.38

- Advanced visible Apple app versioning to `v2026.06.23.38`.
- Apple Narrate EPUB creation now exposes optional title, author, and genre metadata fields and submits them through Web-aligned book metadata/config aliases.

### 2026.06.23.37

- Advanced visible Apple app versioning to `v2026.06.23.37`.
- Web and Apple book creation now submit structured `book_genres` arrays alongside visible `book_genre` text, keeping edited and lookup genres aligned across surfaces.

### 2026.06.23.36

- Advanced visible Apple app versioning to `v2026.06.23.36`.
- In-memory book lookup enrichment now keeps `book_isbn`, `book_genre`, and `book_genres` aligned in active pipeline request config after metadata persistence.

### 2026.06.23.35

- Advanced visible Apple app versioning to `v2026.06.23.35`.
- Persisted book lookup metadata now keeps `book_isbn`, `book_genre`, and `book_genres` in job media metadata and config after lookup enrichment.

### 2026.06.23.34

- Advanced visible Apple app versioning to `v2026.06.23.34`.
- Backend book lookup payloads now emit `book_isbn`, `book_genre`, and `book_genres` aliases directly across OpenLibrary, Google Books fallback, and unified metadata results.

### 2026.06.23.33

- Advanced visible Apple app versioning to `v2026.06.23.33`.
- Google Books fallback metadata now preserves `language`, `book_language`, and genre aliases so Web and Apple book creation receive the same enriched lookup shape when OpenLibrary falls through.

### 2026.06.23.32

- Advanced visible Apple app versioning to `v2026.06.23.32`.
- Web and Apple book creation now preserve `book_language` in metadata/config payloads, and OpenLibrary lookup can carry source language hints into Web submissions.

### 2026.06.23.31

- Advanced visible Apple app versioning to `v2026.06.23.31`.
- Web book metadata lookup now persists preview genres into `book_genre`, so submitted config overrides carry the selected lookup genre without manual editing.

### 2026.06.23.30

- Advanced visible Apple app versioning to `v2026.06.23.30`.
- Web book narration now promotes edited genre and ISBN metadata into config overrides, matching the Apple `book_genre` and `book_isbn` payload shape.

### 2026.06.23.29

- Advanced visible Apple app versioning to `v2026.06.23.29`.
- Apple generated-book and Narrate EPUB metadata now expose ISBN and submit Web-aligned `book_genre` and `book_isbn` aliases.

### 2026.06.23.28

- Advanced visible Apple app versioning to `v2026.06.23.28`.
- Apple generated-book and Narrate EPUB voice overrides now mirror the Web payload shape in both pipeline inputs and pipeline overrides.

### 2026.06.23.27

- Advanced visible Apple app versioning to `v2026.06.23.27`.
- Apple generated-book and Narrate EPUB target voice overrides now apply across every submitted target language.

### 2026.06.23.26

- Advanced visible Apple app versioning to `v2026.06.23.26`.
- Apple generated-book and Narrate EPUB creation now expose Web-aligned additional target languages and submit multi-target `target_languages` arrays.

### 2026.06.23.25

- Advanced visible Apple app versioning to `v2026.06.23.25`.
- Apple generated-book creation now exposes Web-aligned image API URL overrides for selecting home Draw Things/image worker nodes.

### 2026.06.23.24

- Advanced visible Apple app versioning to `v2026.06.23.24`.
- Apple generated-book and Narrate EPUB creation now expose Web-aligned worker threads, queue size, and max job worker overrides for backend performance tuning.

### 2026.06.23.23

- Advanced visible Apple app versioning to `v2026.06.23.23`.
- Apple generated-book and Narrate EPUB creation now expose a Web-aligned cover file path field, submitting `book_cover_file` through metadata and config.

### 2026.06.23.22

- Advanced visible Apple app versioning to `v2026.06.23.22`.
- Apple generated-book and Narrate EPUB creation now expose Web-aligned metadata summary and year fields, submitting them through `book_metadata` and matching book config keys.

### 2026.06.23.21

- Advanced visible Apple app versioning to `v2026.06.23.21`.
- Apple generated-book and Narrate EPUB creation now expose the Web-aligned optional LLM model picker and submit `ollama_model` when selected.

### 2026.06.23.20

- Advanced visible Apple app versioning to `v2026.06.23.20`.
- Apple generated-book and Narrate EPUB creation now expose a target-language voice override that submits the backend `voice_overrides` payload when selected.

### 2026.06.23.19

- Advanced visible Apple app versioning to `v2026.06.23.19`.
- Apple generated-book and Narrate EPUB creation now expose Web-aligned sentences-per-file and stitch-full-book output controls before submit.

### 2026.06.23.18

- Advanced visible Apple app versioning to `v2026.06.23.18`.
- Apple generated-book and Narrate EPUB creation now expose Web-aligned translation provider, translation batch, transliteration mode/model, and lookup cache batch controls before submit.

### 2026.06.23.17

- Advanced visible Apple app versioning to `v2026.06.23.17`.
- Apple Narrate EPUB creation on iPhone and iPad now exposes Web-aligned start and end sentence range controls before submit.

### 2026.06.23.16

- Advanced visible Apple app versioning to `v2026.06.23.16`.
- Apple generated-book and Narrate EPUB creation on iPhone and iPad now expose Web-aligned narration controls for audio generation, audio mode, audio quality, written mode, and tempo before submit.

### 2026.06.23.15

- Advanced visible Apple app versioning to `v2026.06.23.15`.
- Apple generated-book and Narrate EPUB creation on iPhone and iPad now expose Web-aligned HTML and PDF output toggles before submit.

### 2026.06.23.14

- Advanced visible Apple app versioning to `v2026.06.23.14`.
- Apple generated-book creation on iPhone and iPad now lets illustration jobs optionally set image worker concurrency and image API timeout before submit.

### 2026.06.23.13

- Advanced visible Apple app versioning to `v2026.06.23.13`.
- Apple generated-book creation on iPhone and iPad now lets illustration jobs seed from the previous generated image and enable backend blank-image detection before submit.

### 2026.06.23.12

- Advanced visible Apple app versioning to `v2026.06.23.12`.
- Apple generated-book creation on iPhone and iPad now lets illustration jobs optionally set image steps, CFG scale, and sampler name before submit.

### 2026.06.23.11

- Advanced visible Apple app versioning to `v2026.06.23.11`.
- Apple generated-book creation on iPhone and iPad now lets Prompt plan illustration jobs group sentences into shared images and tune prompt-plan batch size before submit.

### 2026.06.23.10

- Advanced visible Apple app versioning to `v2026.06.23.10`.
- Apple generated-book creation on iPhone and iPad now lets Illustrations jobs set backend image width and height before submit.

### 2026.06.23.09

- Advanced visible Apple app versioning to `v2026.06.23.09`.
- Apple generated-book creation on iPhone and iPad now lets Illustrations jobs choose Prompt plan or Visual canon before submit.

### 2026.06.23.08

- Advanced visible Apple app versioning to `v2026.06.23.08`.
- Apple generated-book creation on iPhone and iPad now lets Illustrations jobs tune the backend image prompt context count before submit.

### 2026.06.23.07

- Advanced visible Apple app versioning to `v2026.06.23.07`.
- Apple generated-book creation on iPhone and iPad now lets Illustrations jobs choose the backend image style template before submit.

### 2026.06.23.06

- Advanced visible Apple app versioning to `v2026.06.23.06`.
- Apple generated-book creation on iPhone and iPad now includes an Illustrations toggle that follows backend defaults and submits `add_images` with the job payload.

### 2026.06.23.05

- Advanced visible Apple app versioning to `v2026.06.23.05`.
- Backend generated-media search now keeps only the first match span plus the occurrence count, preserving Web and Apple search responses while avoiding large per-chunk match tuple allocations for common terms.
- The shared Apple device app pipeline backend gate now covers the repeated-term search contract for ebook-tools.

### 2026.06.23.04

- Advanced visible Apple app versioning to `v2026.06.23.04`.
- Web Subtitle Tool now uses a tested source-selection refresh rule, clearing stale selections after deletes and choosing the latest usable subtitle source when needed.
- The shared Apple device app pipeline now includes the Subtitle Tool focused Web check for ebook-tools.

### 2026.06.23.03

- Advanced visible Apple app versioning to `v2026.06.23.03`.
- Web Video Dubbing now uses a tested selection fallback after deleting a NAS/YouTube video, preserving the current selection when possible and choosing the next default subtitle when needed.
- The shared Apple device app pipeline now includes the Video Dubbing focused Web check for ebook-tools.

### 2026.06.23.02

- Advanced visible Apple app versioning to `v2026.06.23.02`.
- Web Library metadata saves now use a tested update plan that preserves source upload ordering, changed-ISBN apply behavior, and explicit ISBN clears.
- The shared Apple device app pipeline now runs a Library-focused Web smoke check for ebook-tools and collapses Vite environment debug dumps while preserving generated-artifact cleanup.

### 2026.06.23.01

- Advanced visible Apple app versioning to `v2026.06.23.01`.
- Apple Jobs rows now show compact generated-book creation summary context from backend metadata, including warnings, creation messages, sample sentences, or seed EPUB paths.

### Web UI

- Refactored the Job Detail creation-summary section into a reusable Web component while preserving its metadata-tab behavior and adding focused coverage for generated-book summary messages, sample sentences, seed EPUB paths, and warnings.

## 2026-06-22

### Backend/API

- Fixed admin job-list pagination when active in-memory jobs are present, while keeping the cheaper persisted-store page path for admin lists with no active jobs.
- Added backend contract coverage for `/api/pipelines/jobs` pagination metadata, normalized access payloads, generated files, job labels, and Apple/Web job parameter snapshots.
- Optimized `/api/pipelines/jobs` list rows to skip filesystem image prompt summary reads while preserving rich image-generation summaries on single-job status responses.

### Web UI

- Web Create generated-audiobook fields now apply backend topic, title, and genre defaults from `/api/books/options` while preserving any prompt edits already typed before defaults arrive, matching the Apple Create behavior.

### 2026.06.22.170

- Advanced visible Apple app versioning to `v2026.06.22.170`.
- Apple playback now decodes shared media manifest diagnostics and shows compact file, chunk, timing, audio, image, and gap counts when the backend provides them.

### 2026.06.22.169

- Advanced visible Apple app versioning to `v2026.06.22.169`.
- Library rows on iPhone/iPad now open an ISBN metadata sheet that previews `/api/library/isbn/lookup` results before applying the ISBN through `/api/library/items/{job_id}/isbn`.

### 2026.06.22.168

- Advanced visible Apple app versioning to `v2026.06.22.168`.
- Library rows on iPhone/iPad now expose Apply ISBN Metadata, posting the entered ISBN to `/api/library/items/{job_id}/isbn` and refreshing the row from the backend response.

### 2026.06.22.167

- Advanced visible Apple app versioning to `v2026.06.22.167`.
- Library rows on iPhone/iPad now expose Replace Source File, using the existing `/api/library/items/{job_id}/upload-source` backend route to upload a new EPUB/PDF source and refresh the row metadata.

### 2026.06.22.166

- Advanced visible Apple app versioning to `v2026.06.22.166`.
- Apple Create now exposes an iPhone/iPad YouTube Dub mode for existing backend/NAS video and subtitle paths, submitting `/api/subtitles/youtube/dub` with Web-aligned language, voice, clip-window, batching, output, and lookup-cache options.

### 2026.06.22.165

- Advanced visible Apple app versioning to `v2026.06.22.165`.
- Apple Create Subtitles now exposes Web-matched worker count and subtitle batch-size tuning on iPhone/iPad and submits `worker_count` plus `batch_size`.

### 2026.06.22.164

- Advanced visible Apple app versioning to `v2026.06.22.164`.
- Apple Create Subtitles now exposes the Web/backend mirror-batches-to-source option on iPhone/iPad and submits the selected `mirror_batches_to_source_dir` field.

### 2026.06.22.163

- Advanced visible Apple app versioning to `v2026.06.22.163`.
- Apple Create Subtitles now exposes LLM batch-size tuning on iPhone/iPad and submits the matching Web/backend `translation_batch_size` field.

### 2026.06.22.162

- Advanced visible Apple app versioning to `v2026.06.22.162`.
- Apple Create Subtitles now exposes transliteration mode and transliteration model controls on iPhone/iPad, matching the Web subtitle options and submitting the selected backend fields.

### 2026.06.22.161

- Advanced visible Apple app versioning to `v2026.06.22.161`.
- Apple Create Subtitles now exposes ASS font size and emphasis controls on iPhone/iPad and submits the matching Web/backend subtitle typography fields.

### 2026.06.22.160

- Advanced visible Apple app versioning to `v2026.06.22.160`.
- Apple Create Subtitles now exposes translation provider and LLM model controls on iPhone/iPad, and submits the selected backend values with subtitle jobs.

### 2026.06.22.159

- Advanced visible Apple app versioning to `v2026.06.22.159`.
- Apple Create Subtitles now validates and normalizes start/end timecodes on iPhone/iPad before submitting, matching the Web `MM:SS`, `HH:MM:SS`, and `+offset` behavior.

### 2026.06.22.158

- Advanced visible Apple app versioning to `v2026.06.22.158`.
- Apple Create Subtitles can now choose a local SRT/VTT/ASS file on iPhone/iPad and upload it directly with the subtitle job, matching the Web upload flow.

### 2026.06.22.157

- Advanced visible Apple app versioning to `v2026.06.22.157`.
- Apple Create now adds an iPhone/iPad subtitle job mode for existing server-side subtitle paths, including language, output format, timing, and key output toggles.

### 2026.06.22.156

- Advanced visible Apple app versioning to `v2026.06.22.156`.
- Apple Create Narrate EPUB now supports iPhone/iPad document import, uploads the selected EPUB through `/api/pipelines/files/upload`, and submits the narration job using the returned backend file path.

### 2026.06.22.155

- Advanced visible Apple app versioning to `v2026.06.22.155`.
- Apple Create now adds an iPhone/iPad Narrate EPUB mode for server-side EPUB paths, submitting `/api/pipelines` with the same backend defaults used by generated audiobook jobs.

### 2026.06.22.154

- Advanced visible Apple app versioning to `v2026.06.22.154`.
- Apple Create now keeps backend-provided narration voices such as `macOS-auto-male` selectable and submits the exact voice value used by the shared Web defaults contract.

### 2026.06.22.153

- Advanced visible Apple app versioning to `v2026.06.22.153`.
- Apple Create now loads backend book-creation defaults and bounds from `/api/books/options`, preserves user edits when defaults arrive, and submits generated-audiobook jobs with the same pipeline defaults used by Web.

### 2026.06.22.152

- Advanced visible Apple app versioning to `v2026.06.22.152`.
- Added a native Apple Create section for generated audiobook jobs, reusing backend-aligned creation payloads and routing submitted jobs into the shared Jobs flow.

### 2026.06.22.151

- Advanced visible Apple app versioning to `v2026.06.22.151`.
- Added native Apple request models and API client plumbing for pipeline creation, generated books, subtitle jobs, YouTube dubbing, and EPUB upload so Web-only creation flows can move onto iPhone, iPad, and Apple TV surfaces.

### 2026.06.22.150

- Advanced visible Apple app versioning to `v2026.06.22.150`.
- Moved video player header controls, timeline pills, dismiss chrome, and info badge rendering into `VideoPlayerHeaderComponents.swift`, keeping `VideoPlayerHeaderView.swift` focused on platform layout and timing labels.

### 2026.06.22.149

- Advanced visible Apple app versioning to `v2026.06.22.149`.
- Moved subtitle token line rendering, word highlighting, token tap/lookup gestures, and overlay token colors into `SubtitleOverlayTokenViews.swift`, keeping the base subtitle overlay focused on display assembly, reset controls, frame reporting, and magnification.

### 2026.06.22.148

- Advanced visible Apple app versioning to `v2026.06.22.148`.
- Moved library row title, language, media variant, summary, duration, sentence count, and TV metadata extraction into `LibraryRowView+Metadata.swift`, keeping the base row file centered on layout and styling.

### 2026.06.22.147

- Advanced visible Apple app versioning to `v2026.06.22.147`.
- Moved transcript selection hit-testing, drag range updates, tap tolerance, and delayed lookup scheduling into `InteractiveTranscriptView+Selection.swift`, keeping the core transcript view focused on layout composition.

### 2026.06.22.146

- Advanced visible Apple app versioning to `v2026.06.22.146`.
- Moved interactive player header scaling, top-padding, pinch magnification, and collapse toggle behavior into `InteractivePlayerView+HeaderBehavior.swift`, keeping the overlay file centered on visible badge and progress-pill layout.

### 2026.06.22.145

- Advanced visible Apple app versioning to `v2026.06.22.145`.
- Moved Jobs filter styling and Apple TV offline download menu actions into `JobsFilterPicker.swift` and `JobsView+OfflineMenu.swift`, keeping the Jobs screen focused on list routing, search, and resume state.

### 2026.06.22.144

- Advanced visible Apple app versioning to `v2026.06.22.144`.
- Moved browse section tabs, refresh styling, and sidebar swipe chrome into `LibraryBrowseChrome.swift` so the library shell can stay focused on navigation and selection state.

### 2026.06.22.143

- Advanced visible Apple app versioning to `v2026.06.22.143`.
- Moved interactive player speed and jump header-pill UI into `InteractivePlayerView+HeaderPills.swift`, leaving the reading-bed extension focused on music source and ambient playback behavior.

### 2026.06.22.142

- Advanced visible Apple app versioning to `v2026.06.22.142`.
- Moved job playback video presentation, preview gestures, fullscreen routing, and player construction into `JobPlaybackView+Video.swift`, keeping the base job playback view focused on lifecycle and layout composition.

### 2026.06.22.141

- Advanced visible Apple app versioning to `v2026.06.22.141`.
- Split library playback loading, Now Playing integration, and resume routing into focused `LibraryPlaybackView` extensions while keeping the base view centered on layout composition.

### 2026.06.22.140

- Advanced visible Apple app versioning to `v2026.06.22.140`.
- Moved subtitle track selection, fetch, streaming parse, and cache persistence into `VideoPlayerView+SubtitleLoading.swift`, keeping `VideoPlayerView+Subtitles.swift` focused on display and navigation controls.

### 2026.06.22.139

- Advanced visible Apple app versioning to `v2026.06.22.139`.
- Moved subtitle playback highlight and shadow-selection logic into `SubtitleOverlayView+Highlighting.swift`, keeping the subtitle overlay focused on rendering and gestures.

### 2026.06.22.138

- Advanced visible Apple app versioning to `v2026.06.22.138`.
- Moved Jobs row title, metadata, progress, status, and cover URL presentation helpers into `JobRowView+Presentation.swift`, keeping `JobRowView.swift` focused on row layout and platform styling.

### 2026.06.22.137

- Advanced visible Apple app versioning to `v2026.06.22.137`.
- Moved transcript track auto-scale measurement, resize handlers, and delayed fit recalculation into `InteractiveTranscriptView+AutoScale.swift`, keeping the core transcript view focused on layout composition.

### 2026.06.22.136

- Advanced visible Apple app versioning to `v2026.06.22.136`.
- Moved timeline active-display builders and active-index resolution into `TextPlayerTimeline+ActiveDisplay.swift`, keeping the base timeline builder focused on sentence runtime construction.

### 2026.06.22.135

- Advanced visible Apple app versioning to `v2026.06.22.135`.
- Moved library video preview, fullscreen presentation, tvOS video body, and video resume/progress helpers into `LibraryPlaybackView+Video.swift`, keeping the main library playback view focused on load and content state.

### 2026.06.22.134

- Advanced visible Apple app versioning to `v2026.06.22.134`.
- Moved the tvOS video playback overlay header and bottom controls into `VideoPlayerOverlayView+TVLayout.swift`, keeping the shared video overlay focused on iOS and subtitle orchestration.

### 2026.06.22.133

- Advanced visible Apple app versioning to `v2026.06.22.133`.
- Moved the tvOS transcript overlay and split-layout handlers into `InteractiveTranscriptView+TVLayout.swift`, keeping the core transcript view less platform-specific.

### 2026.06.22.132

- Advanced visible Apple app versioning to `v2026.06.22.132`.
- Moved the growing June 22 changelog entry list into `AppChangelogData+2026-06-22.swift`, leaving `AppChangelogData.swift` as the compact day index for future daily dogfood entries.

### 2026.06.22.131

- Advanced visible Apple app versioning to `v2026.06.22.131`.
- Split the public backend runtime descriptor into named auth, client config, and Apple pipeline sections, with regression coverage that every response gets fresh environment/profile lists for simulator and device preflights.

### 2026.06.22.130

- Advanced visible Apple app versioning to `v2026.06.22.130`.
- Moved iPad hardware-keyboard first-responder reclaim, software-keyboard guards, focus updates, and window-touch reclaim into `InteractivePlayerShortcutFocus.swift`, keeping shortcut support focused on controller lifecycle and key-command mapping.

### 2026.06.22.129

- Advanced visible Apple app versioning to `v2026.06.22.129`.
- Centralized text-player token reveal counts, current-token selection, and segment-end reveal tolerance into one timeline helper so live display, active sentence, and track-switch settling states use the same playback rules.

### 2026.06.22.128

- Advanced visible Apple app versioning to `v2026.06.22.128`.
- Moved text-player sentence track filtering, hidden-track controls, selection mapping, and playback shadow mapping into `TextPlayerSentenceView.swift`, keeping text player views focused on the frame shell and shared styling helpers.

### 2026.06.22.127

- Advanced visible Apple app versioning to `v2026.06.22.127`.
- Moved text-player variant headers, token flow composition, platform font sizing, seek lookup, and token color state into `TextPlayerVariantView.swift`, keeping text player views focused on frame and sentence orchestration.

### 2026.06.22.126

- Advanced visible Apple app versioning to `v2026.06.22.126`.
- Moved the reusable text-player token flow layout into `TextPlayerTokenFlowLayout.swift`, keeping text player views focused on sentence and variant composition.

### 2026.06.22.125

- Advanced visible Apple app versioning to `v2026.06.22.125`.
- Moved text-player token chip rendering, tap gestures, context menu, and dictionary lookup presenter into `TextPlayerTokenWordView.swift`, keeping text player views focused on flow and variant composition.

### 2026.06.22.124

- Advanced visible Apple app versioning to `v2026.06.22.124`.
- Moved text-player token coordinate-space and preference-key plumbing into `TextPlayerTokenGeometry.swift`, keeping text player rendering focused on sentence, variant, and token views.

### 2026.06.22.123

- Advanced visible Apple app versioning to `v2026.06.22.123`.
- Moved shortcut dispatch identity, throttling, and UIKit fallback scheduling into `InteractivePlayerShortcutDispatch.swift`, keeping iPad keyboard support focused on responder ownership and key-command wiring.

### 2026.06.22.122

- Advanced visible Apple app versioning to `v2026.06.22.122`.
- Moved the iPad hardware-keyboard GameController fallback into `InteractivePlayerShortcutHardwareFallback.swift`, keeping shortcut support focused on responder ownership and UIKit key commands.

### 2026.06.22.121

- Advanced visible Apple app versioning to `v2026.06.22.121`.
- Moved player menu pickers and selection handlers into `InteractivePlayerView+MenuControls.swift`, keeping the menu file focused on header imagery, the control bar shell, and TV text-size controls.

### 2026.06.22.120

- Advanced visible Apple app versioning to `v2026.06.22.120`.
- Moved interactive transcript composition into `InteractivePlayerView+InteractiveContent.swift`, keeping `InteractivePlayerView+Layout.swift` focused on the screen shell and overlay layers.

### 2026.06.22.119

- Advanced visible Apple app versioning to `v2026.06.22.119`.
- Moved interactive player lifecycle observers and playback side-effect handlers into `InteractivePlayerView+LifecycleObservers.swift`, keeping `InteractivePlayerView+Layout.swift` focused on screen composition.

### 2026.06.22.118

- Advanced visible Apple app versioning to `v2026.06.22.118`.
- Moved iPad hardware-keyboard input host views and the touch observer into `InteractivePlayerShortcutHostViews.swift`, keeping shortcut dispatch focused on command routing.

### 2026.06.22.117

- Advanced visible Apple app versioning to `v2026.06.22.117`.
- Moved tvOS playback focus and remote navigation handlers into `VideoPlayerOverlayTVFocus.swift`, keeping the video overlay view focused on composition and chrome rendering.

### 2026.06.22.116

- Advanced visible Apple app versioning to `v2026.06.22.116`.
- Moved subtitle selection, token frame reporting, and display-building models into `SubtitleOverlayModels.swift`, keeping `SubtitleOverlayView.swift` focused on overlay layout, gestures, and token rendering.

### 2026.06.22.115

- Advanced visible Apple app versioning to `v2026.06.22.115`.
- Moved Library playback metadata, cover, language, media selection, subtitle track, and video metadata derivation into `LibraryPlaybackMetadata.swift`, keeping `LibraryPlaybackView.swift` focused on screen lifecycle, layout, and playback actions.

### 2026.06.22.114

- Advanced visible Apple app versioning to `v2026.06.22.114`.
- Moved video overlay subtitle drag selection, phone subtitle positioning, and shared overlay labels into `VideoPlayerOverlayInteraction.swift`, keeping `VideoPlayerOverlayView.swift` focused on composition and TV focus orchestration.

### 2026.06.22.113

- Advanced visible Apple app versioning to `v2026.06.22.113`.
- Moved shared media search state, actions, pill buttons, and input controls into `MediaSearchControls.swift`, keeping `MediaSearchView.swift` focused on panel and overlay presentation.

### 2026.06.22.112

- Advanced visible Apple app versioning to `v2026.06.22.112`.
- Moved shared platform slider, picker, playback button, focus, gesture, and list-background helpers into `PlatformControls.swift`, keeping `PlatformAdapter.swift` focused on detection, metrics, typography, and colors.

### 2026.06.22.111

- Advanced visible Apple app versioning to `v2026.06.22.111`.
- Moved Settings connection, playback, changelog, voice, and notification section rendering into `PlaybackSettingsSections.swift`, keeping `PlaybackSettingsView.swift` focused on state, lifecycle, and backend descriptor checks.

### 2026.06.22.110

- Advanced visible Apple app versioning to `v2026.06.22.110`.
- Moved daily changelog entries into `AppChangelogData.swift`, keeping the shared changelog model/API small while preserving the visible changelog on iPhone, iPad, and Apple TV.

### 2026.06.22.109

- Advanced visible Apple app versioning to `v2026.06.22.109`.
- Moved linguist bubble answer rendering plus shared close/font controls into `LinguistBubbleContentControls.swift`, keeping the main bubble view focused on state, measurement, and gestures.

### 2026.06.22.108

- Advanced visible Apple app versioning to `v2026.06.22.108`.
- Moved linguist bubble picker option models and picker-data builders into `LinguistBubblePickerModels.swift`, keeping `LinguistBubblePickerUI.swift` focused on overlay rendering.

### 2026.06.22.107

- Advanced visible Apple app versioning to `v2026.06.22.107`.
- Split iOS and tvOS linguist bubble header controls into platform-specific SwiftUI extension files while keeping shared selector menus in the common header controls file.

### 2026.06.22.106

- Advanced visible Apple app versioning to `v2026.06.22.106`.
- Moved linguist bubble header rows and selector controls into `LinguistBubbleHeaderControls.swift`, keeping the main bubble view focused on state, lifecycle, and content.
- Reworked the tvOS changelog into a deterministic focus-paged entry window so the Siri Remote can move through older daily entries without relying on nested scroll gesture handling.

### 2026.06.22.105

- Advanced visible Apple app versioning to `v2026.06.22.105`.
- Moved linguist bubble model/voice label parsing and model grouping out of the main SwiftUI view into the shared text utilities file, keeping the bubble view focused on layout and controls.

### 2026.06.22.104

- Advanced visible Apple app versioning to `v2026.06.22.104`.
- Added non-secret Apple pipeline identity metadata to the backend runtime descriptor and made the shared backend checker assert the ebook-tools manifest id.
- Reworked the tvOS visible changelog into compact rows inside a real bounded scroll view with focus-following movement, a wider login card, and an up/down position affordance so the Siri Remote can reveal older daily entries.

### 2026.06.22.103

- Advanced visible Apple app versioning to `v2026.06.22.103`.
- Reused the shared video time formatter for TV playback scrubber labels instead of keeping a duplicate formatter inside the tvOS controls view.

### 2026.06.22.102

- Advanced visible Apple app versioning to `v2026.06.22.102`.
- Moved the TV playback timeline pill into the tvOS playback controls module so the overlay stays focused on layout and focus orchestration.

### 2026.06.22.101

- Advanced visible Apple app versioning to `v2026.06.22.101`.
- Moved the tvOS changelog visible-row, position-label, and remote-movement calculations into one focused helper so full-day changelog scrolling remains predictable as daily entries grow.

### 2026.06.22.100

- Advanced visible Apple app versioning to `v2026.06.22.100`.
- Made the tvOS login and settings changelog use the bounded remote-scroll list for the full current-day changelog, with a position counter proving the Siri Remote can move beyond the first visible rows.

### 2026.06.22.99

- Advanced visible Apple app versioning to `v2026.06.22.99`.
- Hardened the tvOS changelog remote-scroll regression so it tracks the newest daily entry automatically and keeps proving older rows can be revealed after future version bumps.

### 2026.06.22.98

- Advanced visible Apple app versioning to `v2026.06.22.98`.
- Split the Apple API client endpoint methods into focused Auth, Library/Jobs, Linguist, Notification, Pipeline Media, and Playback State service extensions while keeping shared transport/auth handling centralized.

### 2026.06.22.97

- Advanced visible Apple app versioning to `v2026.06.22.97`.
- Split Pipeline sentence metadata and job timing API payloads into dedicated model files so media file/chunk decoding is no longer coupled to timed-text contracts.

### 2026.06.22.96

- Advanced visible Apple app versioning to `v2026.06.22.96`.
- Made the tvOS daily changelog in login and settings use capped, remote-focusable rows so the Siri Remote can move through entries beyond the first visible rows.
- Added a DEBUG-only E2E launch flag so simulator UI tests can force the login surface without reusing stored sessions.
- Moved Library browse and Pipeline job status/progress API models into a dedicated Models file, leaving the broad API model file focused on generic JSON and media metadata helpers.

### 2026.06.22.94

- Advanced visible Apple app versioning to `v2026.06.22.94`.
- Moved assistant lookup, structured linguist, model list, voice inventory, and audio synthesis API models into a dedicated Models file.

### 2026.06.22.93

- Advanced visible Apple app versioning to `v2026.06.22.93`.
- Moved login, session, OAuth, and backend runtime descriptor API models into a dedicated Models file so authentication contract decoding is separated from unrelated API payloads.

### 2026.06.22.92

- Advanced visible Apple app versioning to `v2026.06.22.92`.
- Moved pipeline media, chunk sentence, audio-track, and timing API models into a dedicated Models file so media playback decoding no longer lives in the broad API model file.

### 2026.06.22.91

- Advanced visible Apple app versioning to `v2026.06.22.91`.
- Moved reading-bed, bookmark, and resume-position API models into a dedicated Models file so playback state decoding no longer lives in the broad API model file.

### 2026.06.22.90

- Advanced visible Apple app versioning to `v2026.06.22.90`.
- Moved push-notification API request and response models into a dedicated Models file so notification registration and preference decoding no longer live in the broad API model file.

### 2026.06.22.89

- Advanced visible Apple app versioning to `v2026.06.22.89`.
- Moved lookup-cache API response models into a dedicated Models file so dictionary cache decoding no longer lives in the broad API model file.

### 2026.06.22.88

- Advanced visible Apple app versioning to `v2026.06.22.88`.
- Moved media-search API response models into a dedicated Models file so the large shared API model file no longer owns search-specific decoding and logging.

### 2026.06.22.87

- Advanced visible Apple app versioning to `v2026.06.22.87`.
- Moved media-search async search state and result-target calculations into a dedicated view-model source file so the SwiftUI search view stays focused on controls and layout.

### 2026.06.22.86

- Advanced visible Apple app versioning to `v2026.06.22.86`.
- Moved media-search result display models, result lists, and result rows into a dedicated SwiftUI file so search orchestration is separated from result presentation.

### 2026.06.22.85

- Advanced visible Apple app versioning to `v2026.06.22.85`.
- Moved the interactive player keyboard shortcut help overlay into its own SwiftUI source file so input bridge code no longer carries overlay layout and keycap rendering.

### 2026.06.22.84

- Advanced visible Apple app versioning to `v2026.06.22.84`.
- Moved backwards-compatible MyLinguist/Video linguist bubble state and wrapper adapters into their own SwiftUI compatibility file, leaving the core bubble view focused on layout and interaction.

### 2026.06.22.83

- Advanced visible Apple app versioning to `v2026.06.22.83`.
- Moved shared row metadata traversal and nested-path lookup into a dedicated helper so Jobs and Library rows no longer carry duplicate recursive parsing code.
- Made the TV changelog respond directly to Siri Remote up/down moves so the bounded daily log can scroll past the first visible rows.

### 2026.06.22.82

- Advanced visible Apple app versioning to `v2026.06.22.82`.
- Moved job-row YouTube thumbnail parsing and cover URL normalization into a dedicated helper so the SwiftUI row view stays focused on row state and layout.

### 2026.06.22.81

- Advanced visible Apple app versioning to `v2026.06.22.81`.
- Moved the library row compact and landscape shells into the shared library-row components file so browsing row layout matches the job row pattern.

### 2026.06.22.80

- Advanced visible Apple app versioning to `v2026.06.22.80`.
- Moved the job row compact and landscape shells into the shared job-row components file so responsive row layout is separated from metadata and cover-resolution logic.

### 2026.06.22.79

- Advanced visible Apple app versioning to `v2026.06.22.79`.
- Moved the library playback header, loading, error, unavailable, and image-reel chrome into a dedicated SwiftUI file so the playback view stays focused on orchestration and resume behavior.

### 2026.06.22.78

- Advanced visible Apple app versioning to `v2026.06.22.78`.
- Added a backend runtime descriptor guard so the public Apple pipeline preflight contract rejects secret-like metadata keys close to the helper that builds it.

### 2026.06.22.77

- Advanced visible Apple app versioning to `v2026.06.22.77`.
- Made TV changelog rows individually focusable so the Siri Remote can move down through the full daily change list instead of stopping after the first visible lines.

### 2026.06.22.76

- Advanced visible Apple app versioning to `v2026.06.22.76`.
- Moved shared language flag roles, entries, and resolver tables into a dedicated Swift source file.

### 2026.06.22.75

- Advanced visible Apple app versioning to `v2026.06.22.75`.
- Moved shared player glyph marks and cover artwork stack into a dedicated SwiftUI source file.

### 2026.06.22.74

- Advanced visible Apple app versioning to `v2026.06.22.74`.
- Moved shared player language flag row and badge UI into a dedicated SwiftUI source file.

### 2026.06.22.73

- Advanced visible Apple app versioning to `v2026.06.22.73`.
- Made the TV changelog summary a focusable, bounded scroll area so the Siri Remote can reveal the full daily entry list.

### 2026.06.22.72

- Advanced visible Apple app versioning to `v2026.06.22.72`.
- Moved shared player channel variants and metrics out of the visual channel badge file.

### 2026.06.22.71

- Advanced visible Apple app versioning to `v2026.06.22.71`.
- Moved job-type glyph mapping out of the shared channel badge UI file.

### 2026.06.22.70

- Advanced visible Apple app versioning to `v2026.06.22.70`.
- Moved MyLinguist preference keys and TTS voice storage out of the channel badge UI file.

### 2026.06.22.69

- Advanced visible Apple app versioning to `v2026.06.22.69`.
- Moved the visible changelog summary UI into its own Swift source file.

### 2026.06.22.68

- Advanced visible Apple app versioning to `v2026.06.22.68`.
- Moved the iPad browse-list collapse gesture helper into its own Swift source file.

### 2026.06.22.67

- Advanced visible Apple app versioning to `v2026.06.22.67`.
- Moved shared browse resume helpers into their own Swift source file.

### 2026.06.22.66

- Advanced visible Apple app versioning to `v2026.06.22.66`.
- Moved browse resume/iCloud snapshot refresh into a shared provider used by Jobs, Library, and Search.

### 2026.06.22.65

- Advanced visible Apple app versioning to `v2026.06.22.65`.
- Moved the public backend runtime descriptor into a dedicated helper with direct contract coverage for Apple pipeline preflights.

### 2026.06.22.64

- Advanced visible Apple app versioning to `v2026.06.22.64`.
- Moved browse resume notification filtering and resume-availability checks into shared helpers used by Jobs, Library, and Search.

### 2026.06.22.63

- Advanced visible Apple app versioning to `v2026.06.22.63`.
- Moved shared browse resume badge and context-menu label formatting into one formatter used by Jobs, Library, and Search.

### 2026.06.22.62

- Advanced visible Apple app versioning to `v2026.06.22.62`.
- Moved the iPad browse list collapse gesture into one shared SwiftUI modifier used by both Jobs and Library lists.

### 2026.06.22.61

- Advanced visible Apple app versioning to `v2026.06.22.61`.
- Moved job playback video-player wiring into one shared SwiftUI helper across preview, fullscreen, and tvOS playback paths.

### 2026.06.22.60

- Advanced visible Apple app versioning to `v2026.06.22.60`.
- Moved library playback video-player wiring into one shared SwiftUI helper across preview, fullscreen, and tvOS playback paths.

### 2026.06.22.59

- Advanced visible Apple app versioning to `v2026.06.22.59`.
- Moved shared player language flag row items into a dedicated SwiftUI subview with a stable row layout.

### 2026.06.22.58

- Advanced visible Apple app versioning to `v2026.06.22.58`.
- Made interactive player audio track mode changes atomic so toggling original/translation audio cannot publish a transient no-track state.

### 2026.06.22.57

- Advanced visible Apple app versioning to `v2026.06.22.57`.
- Moved tvOS jobs offline menu actions into named SwiftUI handlers.

### 2026.06.22.56

- Advanced visible Apple app versioning to `v2026.06.22.56`.
- Moved tvOS library offline menu actions into named SwiftUI handlers.

### 2026.06.22.55

- Advanced visible Apple app versioning to `v2026.06.22.55`.
- Moved interactive player header language flag rows into one SwiftUI helper with a named role-toggle handler.

### 2026.06.22.54

- Advanced visible Apple app versioning to `v2026.06.22.54`.
- Moved shared player language flag role toggles into a named SwiftUI handler.

### 2026.06.22.53

- Advanced visible Apple app versioning to `v2026.06.22.53`.
- Moved shared media search result row selection into a named SwiftUI handler.

### 2026.06.22.52

- Advanced visible Apple app versioning to `v2026.06.22.52`.
- Moved shared media search submit events into a named SwiftUI handler.

### 2026.06.22.51

- Advanced visible Apple app versioning to `v2026.06.22.51`.
- Moved shared media search clear and dismiss buttons into named SwiftUI handlers.

### 2026.06.22.50

- Advanced visible Apple app versioning to `v2026.06.22.50`.
- Moved interactive header timeline taps and tvOS header long-press toggles into named SwiftUI handlers.

### 2026.06.22.49

- Advanced visible Apple app versioning to `v2026.06.22.49`.
- Moved iPhone transcript bubble backdrop and content tap handling into named SwiftUI handlers.

### 2026.06.22.48

- Advanced visible Apple app versioning to `v2026.06.22.48`.
- Moved iPad split transcript bubble backdrop and content tap handling into named SwiftUI handlers.

### 2026.06.22.47

- Advanced visible Apple app versioning to `v2026.06.22.47`.
- Moved interactive text-player bookmark menu add, jump, and remove rows into named SwiftUI helpers.

### 2026.06.22.46

- Advanced visible Apple app versioning to `v2026.06.22.46`.
- Moved interactive text-player tvOS directional navigation into named SwiftUI focus handlers.

### 2026.06.22.45

- Advanced visible Apple app versioning to `v2026.06.22.45`.
- Moved tvOS overlay header, bubble, and timeline-pill focus events into named SwiftUI handlers.

### 2026.06.22.44

- Advanced visible Apple app versioning to `v2026.06.22.44`.
- Moved tvOS playback button, scrubber, and controls-bar focus events into named SwiftUI handlers.

### 2026.06.22.43

- Advanced visible Apple app versioning to `v2026.06.22.43`.
- Moved bookmark ribbon menu add, jump, and remove rows into named SwiftUI helpers.

### 2026.06.22.42

- Advanced visible Apple app versioning to `v2026.06.22.42`.
- Moved video bookmark menu jump and remove rows into named SwiftUI helpers.

### 2026.06.22.41

- Advanced visible Apple app versioning to `v2026.06.22.41`.
- Moved video subtitle settings close, segment, and track selection work into named SwiftUI handlers.

### 2026.06.22.40

- Advanced visible Apple app versioning to `v2026.06.22.40`.
- Moved shared video speed menu rate rows and selection work into named SwiftUI helpers.

### 2026.06.22.39

- Advanced visible Apple app versioning to `v2026.06.22.39`.
- Moved interactive player menu rows for audio, speed, reading-bed, and settings commands into named SwiftUI helpers.
- Updated the shared Apple pipeline rule so physical device installs are attended and only run when explicitly requested for a named device.

### 2026.06.22.38

- Advanced visible Apple app versioning to `v2026.06.22.38`.
- Moved iPad interactive player keyboard shortcut commands into named SwiftUI handlers.

### 2026.06.22.37

- Advanced visible Apple app versioning to `v2026.06.22.37`.
- Moved interactive player music-picker, bookmark-identity, and reading-bed URL reactions into named SwiftUI handlers.

### 2026.06.22.36

- Advanced visible Apple app versioning to `v2026.06.22.36`.
- Moved interactive transcript bubble geometry and iPad split layout updates into named SwiftUI handlers.

### 2026.06.22.35

- Advanced visible Apple app versioning to `v2026.06.22.35`.
- Moved subtitle overlay token-frame preference and clear-state updates into named SwiftUI handlers.

### 2026.06.22.34

- Advanced visible Apple app versioning to `v2026.06.22.34`.
- Moved text-player token-frame and tap-exclusion preference changes into named SwiftUI handlers.

### 2026.06.22.33

- Advanced visible Apple app versioning to `v2026.06.22.33`.
- Moved text-player visible and hidden track header toggles into named SwiftUI handlers.

### 2026.06.22.32

- Advanced visible Apple app versioning to `v2026.06.22.32`.
- Moved text and video shortcut-help overlay backdrop and close-button dismissals into named SwiftUI handlers.

### 2026.06.22.31

- Advanced visible Apple app versioning to `v2026.06.22.31`.
- Moved Jobs and Library browse row taps plus tvOS filter long-press refresh actions into named SwiftUI handlers.

### 2026.06.22.30

- Advanced visible Apple app versioning to `v2026.06.22.30`.
- Moved tvOS transcript track tap and long-press focus actions into named SwiftUI handlers.

### 2026.06.22.29

- Advanced visible Apple app versioning to `v2026.06.22.29`.
- Moved video overlay subtitle settings, phone bubble backdrop, playback-change, token-frame, and subtitle drag work into named SwiftUI handlers.

### 2026.06.22.28

- Advanced visible Apple app versioning to `v2026.06.22.28`.
- Moved Jobs and Library browse row selection, delete, search, and tvOS offline menu work into named SwiftUI handlers.

### 2026.06.22.27

- Advanced visible Apple app versioning to `v2026.06.22.27`.
- Moved playback host fullscreen video dismissal, edge-swipe back, and preview drag work into named SwiftUI handlers.

### 2026.06.22.26

- Advanced visible Apple app versioning to `v2026.06.22.26`.
- Centralized backend request session-token parsing for Authorization headers and `access_token` query fallback.

### 2026.06.22.25

- Advanced visible Apple app versioning to `v2026.06.22.25`.
- Moved bookmark ribbon add, jump, remove, and tvOS focus movement work into named SwiftUI handlers.

### 2026.06.22.24

- Advanced visible Apple app versioning to `v2026.06.22.24`.
- Moved tvOS Library and Jobs offline menu remove/download commands into named SwiftUI handlers.

### 2026.06.22.23

- Advanced visible Apple app versioning to `v2026.06.22.23`.
- Matched the Library browse list to the Jobs row-builder structure so iPad and tvOS row actions are easier to audit.

### 2026.06.22.22

- Advanced visible Apple app versioning to `v2026.06.22.22`.
- Moved offline download, retry, and remove-copy menu work into named SwiftUI handlers.

### 2026.06.22.21

- Advanced visible Apple app versioning to `v2026.06.22.21`.
- Moved Apple Music picker dismiss, authorization, search, clear, stop, tab, suggestion-load, and result-selection work into named SwiftUI handlers.

### 2026.06.22.20

- Advanced visible Apple app versioning to `v2026.06.22.20`.
- Moved interactive text search overlay toggle, dismiss, submit, query-change, and result-selection work into named SwiftUI handlers.

### 2026.06.22.19

- Advanced visible Apple app versioning to `v2026.06.22.19`.
- Moved video search overlay toggle, dismiss, submit, query-change, and result-selection work into named SwiftUI handlers.

### 2026.06.22.18

- Advanced visible Apple app versioning to `v2026.06.22.18`.
- Moved interactive player and video bookmark menu commands plus remote bookmark create/delete work into named SwiftUI handlers.

### 2026.06.22.17

- Advanced visible Apple app versioning to `v2026.06.22.17`.
- Moved interactive player menu selection, playback-rate, reading-bed, text-size, seek, and voice-reset commands into named SwiftUI handlers.

### 2026.06.22.16

- Advanced visible Apple app versioning to `v2026.06.22.16`.
- Moved background music overlay transport, volume, scrubbing, and song-selection commands into named SwiftUI handlers.

### 2026.06.22.15

- Advanced visible Apple app versioning to `v2026.06.22.15`.
- Moved Jobs and Library browse list lifecycle, resume-store updates, and sidebar-collapse drag handling into named SwiftUI handlers.

### 2026.06.22.14

- Advanced visible Apple app versioning to `v2026.06.22.14`.
- Moved combined browse search focus, resume-store updates, search clearing, and result selection into named SwiftUI handlers.

### 2026.06.22.13

- Advanced visible Apple app versioning to `v2026.06.22.13`.
- Moved shared media search submit, clear, dismiss, result-selection, tvOS focus, and async search/debounce work into named SwiftUI handlers.

### 2026.06.22.12

- Advanced visible Apple app versioning to `v2026.06.22.12`.
- Moved transcript audio-duration recording, auto-scale measurement, bubble-change recalculation, playback cleanup, and disappear cleanup into named SwiftUI lifecycle handlers.

### 2026.06.22.11

- Advanced visible Apple app versioning to `v2026.06.22.11`.
- Moved job and library playback host lifecycle work into named SwiftUI handlers so load, start-over, now-playing, scene-phase, and teardown reactions are easier to audit on iPad and tvOS.

### 2026.06.22.10

- Advanced visible Apple app versioning to `v2026.06.22.10`.
- Moved video player setup, URL-change, subtitle, bookmark, and playback state reactions into named SwiftUI lifecycle handlers so iPad and tvOS playback changes are easier to review.

### 2026.06.22.09

- Advanced visible Apple app versioning to `v2026.06.22.09`.
- Removed tvOS video control menu type erasure so bookmark and playback speed menus stay concrete SwiftUI views through the focusable controls bar.

### 2026.06.22.08

- Advanced visible Apple app versioning to `v2026.06.22.08`.
- Removed transcript track layout type erasure so phone, iPad split, and tvOS transcript branches pass the measured track view through typed SwiftUI helpers.

### 2026.06.22.07

- Advanced visible Apple app versioning to `v2026.06.22.07`.
- Replaced the interactive player layout's erased lifecycle `AnyView` chain with staged typed SwiftUI modifiers and named playback/header handlers.

### 2026.06.22.06

- Advanced visible Apple app versioning to `v2026.06.22.06`.
- Replaced the interactive player header overlay's erased `AnyView` branch with typed SwiftUI builders while preserving the existing phone, iPad, and tvOS header layouts.

### 2026.06.22.05

- Advanced visible Apple app versioning to `v2026.06.22.05`.
- Replaced the browse shell's erased `AnyView` section picker handoff with a typed SwiftUI `BrowseSectionPicker` shared by Jobs, Library, Search, and Settings.

### 2026.06.22.04

- Advanced visible Apple app versioning to `v2026.06.22.04`.
- Split release version metadata and in-app changelog rendering out of `AppTheme.swift` into focused Shared SwiftUI files.
- Hardened MacBook backend test setup so pytest uses a local HuggingFace cache when external model storage is offline, while production runtime paths still fail visibly if misconfigured.

### 2026.06.22.03

- Advanced visible Apple app versioning to `v2026.06.22.03`.
- Refactored Library and Jobs row actions so selection, delete, and move-to-library commands route through named SwiftUI methods instead of inline row-builder closures.

### 2026.06.22.02

- Advanced visible Apple app versioning to `v2026.06.22.02`.
- Refactored the Apple browse shell so refresh, selection, search, sign-out, and split-view navigation are handled by named SwiftUI actions instead of inline view-builder closures.

### 2026.06.22.01

- Advanced visible Apple app versioning to `v2026.06.22.01`.
- Added token-safe backend auth/session duration metrics so slow login reports can be diagnosed from Prometheus without exposing credentials or session tokens.

## 2026-06-21

### 2026.06.21.11

- Advanced visible Apple app versioning to `v2026.06.21.11`.
- Moved root notification, keyboard-shortcut, session-restore, and offline sync lifecycle hooks into focused SwiftUI modifiers so the app shell is easier to iterate safely across iPhone, iPad, and tvOS.

### 2026.06.21.10

- Advanced visible Apple app versioning to `v2026.06.21.10`.
- Hardened the in-app version badge so iPad browse/login headers render the release text inside an explicit fixed-size shape instead of accepting narrow text proposals.
- Kept the shared pipeline rule that simulator runtimes must match detected physical device OS versions across ebook-tools and Finance Review.

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
