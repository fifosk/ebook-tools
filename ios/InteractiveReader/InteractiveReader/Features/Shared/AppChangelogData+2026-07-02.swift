extension AppChangelogData {
    static let july2Entries: [AppChangelogEntry] = [
                AppChangelogEntry(
                    id: "apple-header-language-pills-restore-from-metadata",
                    title: "Language pills re-enable",
                    detail: "Apple reader header language pills now keep known book language roles selectable while chunks hydrate or single-track audio is active, so disabling Original or Translation can be reversed without stale single-track memory forcing the pill grey."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-source-support-controls",
                    title: "YouTube sources are focused",
                    detail: "Apple YouTube Dub Create controls now keep video discovery, Download Station handoff, and embedded-subtitle extraction in focused SwiftUI files while preserving NAS/video source selection across iPad, iPhone, Apple TV, and Mac iPad-style builds."
                ),
                AppChangelogEntry(
                    id: "apple-create-source-support-controls",
                    title: "Create sources are focused",
                    detail: "Apple Create source support controls for chapter ranges, subtitle sources, file imports, and busy source-action rows now live in a focused SwiftUI file while preserving source-picker behavior across iPad, iPhone, Apple TV, and Mac iPad-style builds."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-audio-keeps-both-text-lanes",
                    title: "Single audio keeps both texts",
                    detail: "Apple reader single-track audio selection now keeps all renderable text tracks visible and lets inactive Original/Translation pills be re-enabled from transcript-backed lanes, so Original-only or Translation-only playback changes the narrated lane without hiding the companion transcript lane."
                ),
                AppChangelogEntry(
                    id: "web-video-dubbing-presentation-helper",
                    title: "Video source display is focused",
                    detail: "Web Video Dubbing presentation helpers for source badges, subtitle labels, stream labels, byte/date/count formatting, output paths, and job labels now live in a focused module while preserving existing imports, keeping source display behavior easier to compare with Apple YouTube Dub."
                ),
                AppChangelogEntry(
                    id: "web-youtube-video-utils-helper",
                    title: "YouTube helper is focused",
                    detail: "Web YouTube video search/download helper logic now lives in a focused tested module covering subtitle defaults, quality labels, source badges, provider lookup, and discovery metadata summaries, trimming the page shell for Apple YouTube Dub parity work."
                ),
                AppChangelogEntry(
                    id: "apple-track-pill-real-lane-support",
                    title: "Track pills match real lanes",
                    detail: "Apple reader track pills now treat one-file combined audio as a mixed fallback rather than an independently selectable Translation lane, while two-stream combined audio and dedicated Original/Translation tracks still support single-track and both-track playback."
                ),
                AppChangelogEntry(
                    id: "backend-create-book-options-helper",
                    title: "Create defaults are focused",
                    detail: "Backend generated-book option/default construction now lives in a focused router support module, keeping /api/books/options easier to compare across Web Narrate Ebook and Apple Create while preserving the same response contract."
                ),
                AppChangelogEntry(
                    id: "apple-changelog-june30-shard",
                    title: "June history is slimmer",
                    detail: "Apple in-app changelog entries for June 30 now live in a dated shard too, keeping the root changelog source focused on the day index as device-visible history grows."
                ),
                AppChangelogEntry(
                    id: "apple-changelog-shard-test-routing",
                    title: "Changelog shard gates hold",
                    detail: "make test-changed now treats dated Apple in-app changelog shards as release metadata, so shard-only edits still run release-version and Apple contract gates without unnecessary simulator builds."
                ),
                AppChangelogEntry(
                    id: "apple-language-pill-empty-active-state",
                    title: "Track pills stay honest",
                    detail: "Apple reader language/audio pills now keep inactive lanes visually inactive during transient loading states while still supporting Original + Translation, Original-only, and Translation-only playback modes."
                ),
                AppChangelogEntry(
                    id: "apple-changelog-july2-shard",
                    title: "Changelog data is slimmer",
                    detail: "Apple in-app changelog entries for July 2 now live in a dated shard, keeping the root changelog day index smaller as Web, backend, and Apple dogfood checkpoints accumulate."
                ),
                AppChangelogEntry(
                    id: "apple-header-pill-shared-toggle",
                    title: "Track pills share one toggle",
                    detail: "Apple reader header language/audio pills now route taps through the shared guarded audio-mode toggle, preserving Original-only or Translation-only states while allowing the inactive companion pill to restore both-track playback without disabling the wrong lane."
                ),
                AppChangelogEntry(
                    id: "backend-library-route-telemetry-module",
                    title: "Library telemetry is focused",
                    detail: "Backend Library route telemetry now lives in a focused router support module while preserving the same token-safe duration metrics and logs used by Web and Apple Library actions."
                ),
                AppChangelogEntry(
                    id: "web-video-dubbing-page-state-hook",
                    title: "Video Dubbing shell is focused",
                    detail: "Web Video Dubbing tab state, status notices, template handoff extras, and initial NAS refresh now live in a focused page-state hook with coverage, keeping the page coordinator closer to Apple YouTube Dub parity checks."
                ),
                AppChangelogEntry(
                    id: "apple-header-pill-live-role-toggle",
                    title: "Track pills keep live state",
                    detail: "Apple reader header language pill taps now recompute live active audio roles before changing lanes, preserving Original-only, Translation-only, and Original + Translation modes after resume or chunk hydration updates."
                ),
                AppChangelogEntry(
                    id: "web-library-search-results-hook",
                    title: "Library loading is focused",
                    detail: "Web Library inventory loading, selected-entry reconciliation, error resets, and batched resume evidence now live in a focused hook shared by the Library page and its regression gate."
                ),
                AppChangelogEntry(
                    id: "web-book-narration-base-state-hook",
                    title: "Narrate Ebook defaults are focused",
                    detail: "Web Narrate Ebook base form state now lives in a focused hook covering shared language defaults, generated-source mode, image defaults, and prefilled image flags before Apple Create parity comparisons."
                ),
                AppChangelogEntry(
                    id: "web-book-narration-form-shell",
                    title: "Narrate Ebook shell is focused",
                    detail: "Web Narrate Ebook form chrome now lives in a focused shell component covering header, step tabs, submit status, template save, and submit routing while the form coordinator stays centered on Create state orchestration."
                ),
                AppChangelogEntry(
                    id: "apple-header-pill-visible-role-toggle",
                    title: "Track pills keep both modes",
                    detail: "Apple reader header pill taps now apply the exact role set shown in the header, so both-track playback can be restored by enabling the inactive companion pill while Original-only and Translation-only stay stable single-track modes."
                ),
                AppChangelogEntry(
                    id: "web-live-media-normalise-helper",
                    title: "Web playback snapshots are shared",
                    detail: "Web live-media snapshot normalization, storage URL resolution, chunk assembly, and progress-generated file parsing now live in a focused helper shared by online playback, Library media, and offline export playback."
                ),
                AppChangelogEntry(
                    id: "apple-audio-shortcuts-sequence-lane",
                    title: "Track pills and shortcuts agree",
                    detail: "Apple reader audio shortcuts now use the same guarded track-toggle path as the header pills, and sequence mode prefers the combined lane before stale single-track evidence when calculating timeline duration and header progress."
                ),
                AppChangelogEntry(
                    id: "web-player-viewer-state-hook",
                    title: "Web player state is slimmer",
                    detail: "Web playback viewer renderability, fullscreen preference, document/chrome state, and wake-lock activation now live in a focused PlayerPanel hook with direct playback-gate coverage."
                ),
                AppChangelogEntry(
                    id: "apple-language-pills-guarded-multiselect",
                    title: "Language pills support both tracks",
                    detail: "Apple reader language pills now behave as guarded multi-select toggles: inactive Original or Translation pills add that lane, active pills remove only themselves when the other lane remains active, and stale chunk state is clamped so the last playable lane stays selected."
                ),
                AppChangelogEntry(
                    id: "apple-audio-menu-track-modes",
                    title: "Audio menu supports both tracks",
                    detail: "Apple reader Audio controls now expose Original + Translation, Original-only, and Translation-only as first-class choices, with the header pill label following the live audio mode instead of stale single-track resume memory."
                ),
                AppChangelogEntry(
                    id: "apple-header-language-pills-enable-both",
                    title: "Language pills restore both tracks",
                    detail: "Apple reader header language pills now route through the shared audio-mode toggle, so Original-only or Translation-only can be expanded back to both tracks by tapping the inactive companion pill while stale single-track resume memory no longer keeps the pill grey."
                ),
                AppChangelogEntry(
                    id: "apple-settings-intake-contract-visible",
                    title: "Settings shows intake readiness",
                    detail: "Apple Settings now shows a dedicated Job Intake Contract row so device preflights can verify queue-pressure parity before native Create opens."
                ),
                AppChangelogEntry(
                    id: "apple-sequence-resume-retry-keeps-track",
                    title: "First Translation resumes correctly",
                    detail: "Apple reader sequence resume retries now keep the same resolved track as the initial in-sentence seek, preventing job open from starting in Translation and then retrying the first sentence on Original."
                ),
                AppChangelogEntry(
                    id: "apple-resume-track-flip-log-check",
                    title: "Resume logs catch track flips",
                    detail: "Apple playback transport log verification now rejects sequence resume retries that change tracks for the same saved sentence and time, so physical Apple TV logs catch this regression directly."
                ),
                AppChangelogEntry(
                    id: "apple-header-language-pills-toggle-roles",
                    title: "Language pills toggle cleanly",
                    detail: "Apple reader header language pills now use true toggle semantics: when Original and Translation are both active, tapping Original disables only Original and keeps Translation active, with the symmetric behavior for Translation."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-pills-restore-both",
                    title: "Single-track pills stay selected",
                    detail: "Apple reader track pills and shortcuts now keep Original-only and Translation-only as valid states, then require the inactive companion lane to be enabled before returning to both tracks."
                ),
                AppChangelogEntry(
                    id: "apple-visible-translation-beats-stale-original",
                    title: "Translation pill stays active",
                    detail: "Apple reader lifecycle refreshes now let a visible Translation-only user selection beat stale Original resume memory, so Apple TV does not deactivate the Translation pill after lazy metadata or track-availability updates."
                ),
                AppChangelogEntry(
                    id: "library-media-translation-track-evidence",
                    title: "Library Translation stays available",
                    detail: "Library media responses now preserve chunk audio and timing track evidence for Apple playback, so Apple TV, iPad, and iPhone keep the Translation pill selectable while sentence text loads lazily."
                ),
                AppChangelogEntry(
                    id: "apple-audio-backed-text-track-availability",
                    title: "Translation stays selectable while loading",
                    detail: "Apple reader text-track availability now also follows playable Original and Translation audio lanes while lazy chunk metadata loads, so Apple TV does not grey out Translation for completed jobs whose media response starts without inline sentences."
                ),
                AppChangelogEntry(
                    id: "shared-jobs-pagination-stable-order",
                    title: "Jobs stay ordered across pages",
                    detail: "Shared backend job listing now sorts visible jobs newest-first before slicing and leaves service-provided pages in that order, keeping Web and Apple Jobs views stable across paginated refreshes."
                ),
                AppChangelogEntry(
                    id: "apple-timing-track-alias-resilience",
                    title: "Translation timing survives aliases",
                    detail: "Apple reader timing decode now accepts target, translated, and dubbed timing-track aliases and tolerates translation-only timing payloads without a mix track, keeping Translation selectable across live, archived, and offline media."
                ),
                AppChangelogEntry(
                    id: "backend-media-timing-track-canonical-roles",
                    title: "Media timing roles are canonical",
                    detail: "Backend media manifests now publish chunk timing tracks through the same Original, Translation, and Mix role mapping as audio tracks, so Web and Apple diagnostics agree on whether a translation lane is available."
                ),
                AppChangelogEntry(
                    id: "apple-target-audio-translation-role",
                    title: "Translation track stays available",
                    detail: "Apple reader media context now treats target, translated, and dubbed audio aliases as Translation tracks, keeping the TV language pill selectable when archived or library media uses those backend-visible names."
                ),
                AppChangelogEntry(
                    id: "apple-tv-header-single-track-role-tap",
                    title: "TV track pills select directly",
                    detail: "Apple reader header language pills now use the same durable single-track selection path as slider, jump, and batch handoffs, so choosing Translation stamps the audio lane before tvOS playback is reconfigured."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-live-lane-resume-clock",
                    title: "Track switching and resume recover",
                    detail: "Apple reader Original/Translation pills now let the live single-track toggle override stale loaded-lane memory, and Job/Library resume recording shares a track-local player clock so pause or relaunch can continue nearer the last spoken word."
                ),
                AppChangelogEntry(
                    id: "apple-header-role-selection-resume-clock",
                    title: "Track selection and resume hold better",
                    detail: "Apple reader header language pills now select the tapped lane directly, and Job/Library resume recording stores the selected-track player clock so resume can continue nearer the last spoken word."
                ),
                AppChangelogEntry(
                    id: "apple-combined-translation-role-resume-clock",
                    title: "Translation and resume are steadier",
                    detail: "Apple reader header roles now expose Translation whenever combined audio carries that stream, and single-track resume uses the exact player clock before falling back to rendered highlight time so playback can continue from the last spoken position."
                ),
                AppChangelogEntry(
                    id: "apple-custom-multi-track-toggle-restore",
                    title: "Track toggles stay selected",
                    detail: "Apple reader lifecycle refreshes now honor an explicit Original + Translation visible-track selection before restoring a stale single-track lane, so turning Translation back on remains active after metadata or sentence-batch updates."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-status-notices-panel",
                    title: "Subtitle Tool feedback is cleaner",
                    detail: "Web Subtitle Tool submit errors, template handoff and save messages, intake status, loading-template notices, and submitted-job summaries now render through a focused component with rendered coverage and focused-suite routing."
                ),
                AppChangelogEntry(
                    id: "web-video-downloaded-list-panel",
                    title: "Downloaded video sources are cleaner",
                    detail: "Web Video Dubbing downloaded-video rows, detached discovered-source display, subtitle picker, embedded stream chooser, and delete/extract actions now live in a focused component with rendered coverage and changed-test routing."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-context-rebuild-reprepare",
                    title: "Single-track refreshes stay synced",
                    detail: "Apple reader live-media and chunk-metadata context rebuilds now reprepare Original-only or Translation-only audio at the recent sentence anchor, so batch refreshes cannot keep stale timing or audio URLs while rendering advances."
                ),
                AppChangelogEntry(
                    id: "apple-durable-single-track-eof-lane",
                    title: "Single-track batches stay selected",
                    detail: "Apple reader Original-only and Translation-only playback now keeps the selected lane as durable view-model state across sentence-batch endings and metadata refreshes, so rendering stays synced to the playing audio."
                ),
                AppChangelogEntry(
                    id: "web-video-discovery-panel",
                    title: "Video discovery is cleaner",
                    detail: "Web Video Dubbing source provider buttons, query/search status, remote candidate rendering, and Download Station handoff chrome now live in a focused component with rendered coverage and changed-test routing."
                ),
                AppChangelogEntry(
                    id: "web-video-tv-metadata-preview",
                    title: "Video metadata is cleaner",
                    detail: "Web Video Dubbing TVMaze metadata preview, artwork, editable job/show/episode fields, and raw payload rendering now live in a focused component with rendered coverage, keeping the Web flow easier to compare with Apple Create metadata review."
                ),
                AppChangelogEntry(
                    id: "apple-sequence-eof-no-single-track-inference",
                    title: "Batch endings keep all tracks",
                    detail: "Apple reader combined and sequence batch endings no longer infer Original-only or Translation-only mode from the final segment URL after the sequence plan has ended, preventing the next batch from resetting to the last spoken track."
                ),
                AppChangelogEntry(
                    id: "backend-provider-catalog-helper",
                    title: "Provider routing is cleaner",
                    detail: "Backend acquisition provider discoverability now lives in a focused catalog shared by discovery routing and the provider registry, reducing the chance that Web and Apple Create expose a provider the backend handler map cannot route."
                ),
                AppChangelogEntry(
                    id: "backend-provider-roots-direct-imports",
                    title: "Source handling is less coupled",
                    detail: "Backend acquisition file discovery, artifact preparation, and Download Station handoff now import source-root resolution from the focused provider-roots helper directly, keeping provider payload assembly out of reusable Web and Apple Create source paths."
                ),
                AppChangelogEntry(
                    id: "backend-provider-roots-helper",
                    title: "Source roots are cleaner",
                    detail: "Backend acquisition provider root resolution now lives in a focused helper module, keeping books, NAS video, manual-download, environment, and safe-stat readability logic reusable for Web and Apple Create without bloating the provider registry payload builder."
                ),
                AppChangelogEntry(
                    id: "apple-selected-timing-stale-sequence-override",
                    title: "Single-track batches resist resets",
                    detail: "Apple reader original-only and translation-only batch handoffs now let the stored selected timing lane override a stale enabled sequence controller, preventing end-of-batch resets where narration stays selected but rendering falls back to combined."
                ),
                AppChangelogEntry(
                    id: "web-video-dubbing-feedback-panel",
                    title: "Video feedback is focused",
                    detail: "Web Video Dubbing page feedback, template status, template errors, and intake callout rendering now live in a focused panel with rendered coverage and changed-test routing, trimming the page coordinator without changing the cross-surface Create workflow."
                ),
                AppChangelogEntry(
                    id: "apple-selected-timing-lane-render-sync",
                    title: "Single-track rendering stays pinned",
                    detail: "Apple reader original-only and translation-only rendering now treats the selected timing lane as durable single-track evidence before transient audio-manager or picker state, so no-URL EOF recovery and batch refreshes cannot reset rendering back to combined while narration stays on the selected lane."
                ),
                AppChangelogEntry(
                    id: "backend-manual-root-readiness-helper",
                    title: "Default sources stay cleaner",
                    detail: "Backend acquisition provider readiness now resolves manual download roots through one helper that keeps NAS video roots discoverable while excluding them from explicit manual-download default fallback policy, preserving Web and Apple Create default-source semantics."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-selected-timing-eof",
                    title: "Single-track batch ends stay pinned",
                    detail: "Apple reader original-only and translation-only playback now treats the selected timing URL stamped by single-track loading as durable lane evidence at sentence-batch EOF, preventing AVPlayer queue cleanup from resetting rendering back to combined while narration advances."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-watchdog-reader-recovery",
                    title: "TV reader starts recover better",
                    detail: "Apple TV Music-bed watchdogs now recover reader starts that still have a pending interactive autoplay sentence but no reader player, and restore narration volume if reader audio is playing or requested but remains muted outside a sentence transition."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-anchor-slow-hydration",
                    title: "Single-track batches wait longer",
                    detail: "Apple reader original-only and translation-only end-of-batch anchors now survive slower NAS and device metadata hydration for up to 60 seconds, so the selected audio lane does not reset before the next batch becomes renderable."
                ),
                AppChangelogEntry(
                    id: "apple-interactive-autoplay-longer-retry",
                    title: "Autoplay starts are sturdier",
                    detail: "Apple reader Job and Library autoplay now validate tracked resume/start sentences against the loaded job, allow start-only placeholder chunks to resolve their first sentence for metadata hydration, and share a longer bounded retry schedule, reducing stale-start autoplay stalls while tvOS Music-bed E2E remains under active hardening."
                ),
                AppChangelogEntry(
                    id: "apple-e2e-xcode-service-retry",
                    title: "TV simulator tests recover once",
                    detail: "Apple E2E Xcode runs now go through a narrow retry wrapper that cleans stale result and DerivedData paths and retries once only for the known mobile.notification_proxy secure-connection simulator service failure, keeping tvOS Music-bed automation from stopping before app assertions."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-loaded-lane-priority-eof",
                    title: "Single-track batch ends hold",
                    detail: "Apple reader original-only and translation-only playback now lets the single audio lane that was actually loaded beat stale preferred state at sentence-batch EOF, so end-of-batch handoffs cannot reset rendering away from the selected track."
                ),
                AppChangelogEntry(
                    id: "backend-provider-defaults-helper",
                    title: "Default sources are leaner",
                    detail: "Backend acquisition Default sources readiness now lives in a focused provider-defaults helper with direct coverage, keeping Web and Apple Create default book and video source fanout policy reusable outside the provider registry payload builder."
                ),
                AppChangelogEntry(
                    id: "backend-discovery-routing-table",
                    title: "Discovery routing is guarded",
                    detail: "Backend acquisition discovery now dispatches providers through a registry-aligned routing table with direct coverage, so Web and Apple Create provider metadata cannot drift from backend discovery handlers."
                ),
                AppChangelogEntry(
                    id: "backend-internet-archive-provider-helper",
                    title: "Archive discovery is leaner",
                    detail: "Backend Internet Archive acquisition discovery now lives with the focused Archive helper module, keeping Archive search, source-id bridge lookups, EPUB candidate construction, and token-safe handoff metadata out of the shared provider fanout while preserving Web and Apple Create contracts."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-mode-stamp",
                    title: "Single-track batches hold",
                    detail: "Apple reader original-only and translation-only playback now stamps the current SwiftUI audio mode into the view model before sentence-batch default setup runs, so the selected track cannot reset and drift rendering."
                ),
                AppChangelogEntry(
                    id: "backend-openlibrary-discovery-provider-helper",
                    title: "Open Library discovery is leaner",
                    detail: "Backend Open Library acquisition discovery now lives with the focused Open Library helper module, keeping metadata-only candidate construction and media-metadata lookup payload shaping out of the shared provider fanout while preserving Web and Apple Create contracts."
                ),
                AppChangelogEntry(
                    id: "backend-gutenberg-discovery-provider-helper",
                    title: "Gutenberg discovery is leaner",
                    detail: "Backend Project Gutenberg acquisition discovery now lives with the focused Gutenberg helper module, keeping Gutendex API calls and public-domain candidate construction out of the shared provider fanout while preserving Web and Apple Create contracts."
                ),
                AppChangelogEntry(
                    id: "backend-indexer-discovery-helper-module",
                    title: "Indexer discovery is leaner",
                    detail: "Backend Newznab and Torznab acquisition discovery now lives with the focused indexer helper module, keeping review-only metadata candidate construction, source-reference storage, and token-safe indexer error handling out of the shared provider fanout."
                ),
                AppChangelogEntry(
                    id: "backend-youtube-discovery-helper-module",
                    title: "YouTube discovery is leaner",
                    detail: "Backend YouTube URL and search acquisition discovery now lives with the focused YouTube helper module, keeping metadata candidate construction and token-safe API error handling out of the shared provider fanout while preserving Web and Apple Create contracts."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-restore-applies-selection",
                    title: "Single-track restore stays selected",
                    detail: "Apple reader resume and visible-track restore paths now reapply the full original-only or translation-only audio selection instead of only assigning a matching option id, keeping the durable loaded lane intact when sentence batches end or resume opens in single-track mode."
                ),
                AppChangelogEntry(
                    id: "backend-file-backed-discovery-helper",
                    title: "File discovery is leaner",
                    detail: "Backend local EPUB, manual download, and NAS video discovery now share a focused file-backed provider helper module, keeping filesystem scanning and candidate shaping out of the large acquisition fanout while preserving Web and Apple Create source picker behavior."
                ),
                AppChangelogEntry(
                    id: "backend-acquisition-models-module",
                    title: "Discovery models are shared",
                    detail: "Backend acquisition discovery result models now live in a focused shared module and are re-exported through existing package APIs, making provider helpers easier to split without changing Web or Apple Create contracts."
                ),
                AppChangelogEntry(
                    id: "backend-discovery-normalization-helper",
                    title: "Discovery requests are leaner",
                    detail: "Backend acquisition discovery request normalization now lives in focused tested helpers for media kind, provider, query, limit, language, and Internet Archive source-id handling, keeping Web and Apple Create discovery fanout easier to maintain."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-loaded-lane-handoff",
                    title: "Single-track batches stay synced",
                    detail: "Apple reader original-only and translation-only playback now remembers the single audio lane that was actually loaded and uses it for batch EOF and render-active checks, so transient picker refreshes cannot drift rendering from narration."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-eof-active-url-guard",
                    title: "Batch endings keep their track",
                    detail: "Apple reader original-only and translation-only batch endings now validate EOF callbacks against the active single audio URL before selecting the next sentence batch, so stale hidden-track endings cannot reset audio selection or drift rendering."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-passive-hydration-guard",
                    title: "Hydrated batches keep their lane",
                    detail: "Apple reader passive hydrated-batch setup now refuses to expand a remembered original-only or translation-only lane back to combined audio just because both text tracks are available, keeping rendering and narration aligned."
                ),
                AppChangelogEntry(
                    id: "backend-default-discovery-planning-helper",
                    title: "Default discovery stays aligned",
                    detail: "Backend Default sources discovery planning now lives in a focused tested helper, keeping local, manual-download, NAS, and remote-provider ordering rules aligned for Web and Apple Create source pickers."
                ),
                AppChangelogEntry(
                    id: "backend-youtube-discovery-helper",
                    title: "YouTube discovery is leaner",
                    detail: "Backend YouTube acquisition discovery now shares focused tested helpers for URL parsing, metadata normalization, duration parsing, API-key lookup, and token-safe error reason extraction across Web and Apple Create video discovery."
                ),
                AppChangelogEntry(
                    id: "backend-indexer-discovery-helper",
                    title: "Indexer discovery is leaner",
                    detail: "Backend Newznab and Torznab acquisition discovery now shares focused tested helpers for endpoint, key, category, sanitized API URL, XML feed, and published-date handling across Web and Apple video source pickers."
                ),
                AppChangelogEntry(
                    id: "backend-openlibrary-discovery-helper",
                    title: "Open Library discovery is leaner",
                    detail: "Backend Open Library acquisition discovery now shares focused tested helpers for work and book key normalization, metadata URLs, and cover URLs, keeping Web and Apple Create book metadata handoff easier to maintain."
                ),
                AppChangelogEntry(
                    id: "backend-internet-archive-discovery-helper",
                    title: "Archive discovery is leaner",
                    detail: "Backend Internet Archive acquisition discovery now shares focused tested helpers for search queries, EPUB eligibility, download URLs, metadata fetches, and rights classification used by Web and Apple Create book discovery."
                ),
                AppChangelogEntry(
                    id: "backend-gutenberg-discovery-helper",
                    title: "Gutenberg discovery is leaner",
                    detail: "Backend Project Gutenberg acquisition discovery now shares focused tested helpers for Gutendex search parameters, EPUB and HTML URL selection, and contributor normalization used by Web and Apple Create book discovery."
                ),
                AppChangelogEntry(
                    id: "backend-source-candidate-helper",
                    title: "Source discovery is leaner",
                    detail: "Backend local, manual-download, and NAS acquisition discovery now shares focused tested helpers for source paths, display titles, zero-byte EPUB filtering, and newest-first manual source ordering used by Web and Apple Create pickers."
                ),
                AppChangelogEntry(
                    id: "backend-discovery-value-helper",
                    title: "Discovery values are leaner",
                    detail: "Backend acquisition discovery now shares focused tested value-normalization helpers for safe identifiers, string and sequence coercion, and integer parsing across public-catalog and video providers."
                )
    ]
}
