# Cross-Surface Parity And Optimization Plan

Last updated: 2026-06-24

## Goal

Bring ebook-tools toward one coherent experience across Web, iPhone, iPad, and Apple TV while preserving existing behavior:

- Web remains the richest creation and administration surface.
- iPad and iPhone gain attended, native creation flows for practical job types.
- Apple TV stays playback-first, with native creation limited to server/NAS-backed job setup.
- Backend APIs stay reusable, observable, and friendly to simulator/device pipelines.

## Current Surface Inventory

### Web UI

The Web app is a Vite + React + TypeScript app in `web/`.

Key state and shell files:

- `web/src/App.tsx`
- `web/src/components/Sidebar.tsx`
- `web/src/components/app/MainContent.tsx`
- `web/src/stores/jobsStore.ts`
- `web/src/stores/uiStore.ts`

Web-only or Web-primary creation flows:

- Narrate Ebook: `web/src/pages/NewImmersiveBookPage.tsx`, `web/src/components/book-narration/BookNarrationForm.tsx`, submits `/api/pipelines`.
- Generated book: `web/src/pages/CreateBookPage.tsx`, `web/src/api/createBook.ts`, submits `/api/books/jobs`.
- Subtitle job: `web/src/pages/SubtitleToolPage.tsx`, `web/src/api/client/subtitles.ts`, submits `/api/subtitles/jobs`.
- YouTube dubbing: `web/src/pages/VideoDubbingPage.tsx`, `web/src/api/client/subtitles.ts`, submits `/api/subtitles/youtube/dub`.
- Library source upload: `web/src/pages/LibraryPage.tsx`, calls `/api/library/items/{job_id}/upload-source`.

Large Web UI hotspots to split before redesign work:

- `web/src/hooks/useLiveMedia.ts` - 813 lines. Status: live media state
  types, empty-state creation, media bucket merging, generated-file extraction,
  chunk merging, audio-track detection, and chunk-sentence detection now live
  in `web/src/hooks/liveMediaState.ts`; modern and legacy timing normalization
  now lives in `web/src/hooks/liveMediaTiming.ts` with focused Vitest coverage.
- `web/src/pages/LibraryPage.tsx` - 815 lines. Status: TV/YouTube/library
  title, author, genre, thumbnail, upload-date, ISBN preview merge/cover, and
  tab bucketing and pagination helpers now live in
  `web/src/pages/library/libraryPageMetadata.ts` with focused Vitest coverage.
  Metadata edit submission now also delegates its trimmed payload and changed
  ISBN apply decision to the same tested helper, preserving source upload
  ordering and explicit ISBN clears. The details metadata tab presentation now
  lives in `web/src/pages/library/LibraryMetadataTab.tsx`, keeping YouTube and
  timestamp formatting with the shared metadata helpers. The overview tab
  presentation, including cover/TV artwork, play/edit/enrichment actions, ISBN
  preview, and source replacement form, now lives in
  `web/src/pages/library/LibraryOverviewTab.tsx`. Detail tab switching and
  sharing/permission editing now live in `LibraryDetailTabs.tsx` and
  `LibraryPermissionsTab.tsx`.
- `web/src/pages/VideoDubbingPage.tsx` - 1140 lines. Status: inline
  subtitle defaulting, playable subtitle filtering, metadata source-name
  resolution, embedded subtitle extractability, voice inventory option
  building, NAS refresh video/subtitle selection, YouTube Dub request payload
  building and clip-offset validation, TV/YouTube metadata draft update and
  preservation helpers, subtitle extraction/availability messages, and
  job-parameter prefill mapping now live in
  `web/src/pages/video-dubbing/videoDubbingUtils.ts` with focused Vitest
  coverage. Video deletion selection fallback now lives there too, preserving
  the current selection when deleting a different video and choosing the next
  default subtitle/language when deleting the selected video. NAS base-dir,
  selected-video, and selected-subtitle persistence now lives in
  `web/src/pages/video-dubbing/useVideoDubbingSelectionState.ts`, restoring
  the last Web NAS source on page load and trimming/clearing local-storage
  values through the shared browser-storage helper. TVMaze/YouTube metadata
  lookup state, stale-response suppression, source-change resets, cache clear
  handlers, and editable metadata draft preservation now live in
  `web/src/pages/video-dubbing/useVideoDubbingMetadata.ts` with focused hook
  coverage. Backend target-language loading, shared language preference
  updates, sorted option construction, subtitle-language fallback, and target
  language-code resolution now live in
  `web/src/pages/video-dubbing/useVideoDubbingLanguageState.ts` with focused
  hook coverage, including a guard against treating a raw subtitle language
  code as an arbitrary catalog label. Voice inventory loading, target-language
  voice option construction, sample synthesis, browser audio cleanup, and
  preview error handling now live in
  `web/src/pages/video-dubbing/useVideoDubbingVoiceState.ts` with focused hook
  coverage. Translation model inventory loading, model-load error handling, and
  selected translation/transliteration provider/model state now live in
  `web/src/pages/video-dubbing/useVideoDubbingModelState.ts` with focused hook
  coverage. Clip-window, mix, resolution, batch/flush, split/stitch,
  transliteration, lookup-cache, backend-default, and output-prefill state now
  live in `web/src/pages/video-dubbing/useVideoDubbingOutputState.ts` with
  focused hook coverage. Embedded subtitle stream inspection, extraction,
  stream selection, subtitle deletion, and related progress/error state now
  live in `web/src/pages/video-dubbing/useVideoDubbingSubtitleExtraction.ts`
  with focused hook coverage. NAS video library refresh, load errors, local
  video deletion, prefill/current-selection fallback, and post-delete fallback
  selection now live in
  `web/src/pages/video-dubbing/useVideoDubbingLibraryState.ts` with focused hook
  coverage. The YouTube Dub template payload builder reuses the same generated
  request payload and strips sensitive metadata keys before saving through
  `/api/creation/templates`. The repo-owned `test-web-video-dubbing-focused`
  target now runs the full Video Dubbing utility/hook/page slice so the reusable
  Apple pipeline Web gate can keep this split work covered with one stable app
  command.
- `web/src/pages/SubtitleToolPage.tsx` - 761 lines. Status: source ordering,
  latest-source selection, submitted-job summary formatting, and rerun prefill
  snapshot mapping, submit validation/payload normalization, and Web-style
  timecode parsing, metadata source-name resolution, ASS selection detection,
  completed-result fetch selection, job sorting, and backend language-default
  normalization, multipart submit `FormData` construction, and metadata draft
  update helpers now live in `web/src/pages/subtitle-tool/subtitleToolUtils.ts`
  with focused Vitest coverage. TV metadata lookup state, stale response
  suppression, draft editing, and clear behavior now live in
  `web/src/pages/subtitle-tool/useSubtitleTvMetadata.ts` with focused hook
  coverage. Source listing, selected-source preservation, refresh, delete, and
  source message/error state now live in
  `web/src/pages/subtitle-tool/useSubtitleSources.ts` with focused hook coverage.
  Completed subtitle-job result fetching, dedupe, partial-failure tolerance, and
  late-response cancellation now live in
  `web/src/pages/subtitle-tool/useSubtitleJobResults.ts` with focused hook
  coverage. Model-option loading, empty responses, failed fetches, and
  late-response cancellation now live in
  `web/src/pages/subtitle-tool/useSubtitleModels.ts` with focused hook
  coverage. Backend language-default loading, default input-language application,
  failure logging, and stale-response protection now live in
  `web/src/pages/subtitle-tool/useSubtitleLanguageDefaults.ts` with focused
  hook coverage. Show-original subtitle preference loading and persistence now
  live in `web/src/pages/subtitle-tool/useSubtitleShowOriginalPreference.ts`
  with focused local-storage failure coverage. Rerun/prefill parameter
  application now lives in `web/src/pages/subtitle-tool/useSubtitlePrefill.ts`
  with focused hook coverage. Shared language preferences, backend
  target-language options, sorted dropdown options, and input/target handlers
  now live in `web/src/pages/subtitle-tool/useSubtitleLanguageState.ts` with
  focused hook coverage.
  Source-list refresh selection also stays pinned in the utility module, clearing
  stale selections after deletes and choosing the latest usable subtitle source
  when needed. The subtitle template payload builder mirrors resolved submit
  field names and strips sensitive metadata keys before saving through
  `/api/creation/templates`. The repo-owned `test-web-subtitle-tool-focused`
  target now runs the full Subtitle Tool utility/hook slice so the reusable
  Apple pipeline Web gate can keep this split work covered with one stable app
  command.
- `web/src/components/video-subtitles/SubtitleTrackOverlay.tsx` - 1119 lines.
  Status: subtitle cue lookup, token navigation, selection shadowing, clamp
  math, track variant mapping, and TTS voice option helpers now live in
  `web/src/components/video-subtitles/subtitleTrackOverlayUtils.ts` with
  focused Vitest coverage.
- `web/src/components/JobProgress.tsx` - 496 lines. Status: generated-file
  stat lookup, batch progress, sentence/playable stage progress,
  lookup-cache progress, parallelism overview entries, fallback display rows,
  unavailable-translation detection, metadata entry splitting, narrated
  subtitle detection, and progress label helpers now live in
  `web/src/components/job-progress/jobProgressUtils.ts` with focused Vitest
  coverage. OpenLibrary metadata lookup query state, success/error handling,
  backend cache clearing, and reload side effects now live in
  `web/src/components/job-progress/useJobProgressMetadataLookup.ts` with
  focused hook coverage. Job detail tabs and permission editing chrome now live
  in `JobProgressTabs.tsx` and `JobProgressPermissionsSection.tsx`. Header
  status/action chrome now lives in `JobProgressHeader.tsx`, and stage-progress
  presentation now lives in `JobProgressStageSection.tsx`. Latest progress
  metrics now live in `JobProgressLatestSection.tsx`. Metadata tab cover,
  lookup, display rows, technical rows, and reload action now live in
  `JobProgressMetadataSection.tsx`. Overview tab parameters, image-cluster
  status, notices, batch stats, parallelism, tuning, and fallback sections now
  live in `JobProgressOverviewSection.tsx`. Job lifecycle timing summary now
  lives in `JobProgressTimingSummary.tsx`.
- `web/src/components/LibraryList.tsx` - 624 lines. Status: layout type
  detection, title/author/genre fallback labels, and author/genre/language
  grouping now live in `web/src/components/library-list/libraryListUtils.ts`
  with focused Vitest coverage. Book summary, TV/episode metadata, subtitle
  genre/summary/image, YouTube metadata, source-badge, and media asset URL
  resolvers now live in `web/src/components/library-list/libraryListMediaUtils.ts`
  with focused Vitest coverage. Permission defaults, export readiness, and
  disabled action-state rules now live in
  `web/src/components/library-list/libraryListActions.ts` with focused Vitest
  coverage. Reusable row/card action buttons now live in
  `web/src/components/library-list/LibraryItemActions.tsx` with focused
  rendered coverage. Library item status badges now live in
  `web/src/components/library-list/LibraryStatusBadge.tsx` with focused
  rendered coverage.
- `web/src/components/PlayerPanel.tsx` - 884 lines. Status: selected text
  item, selected chunk, and active text chunk resolution now live in
  `web/src/components/player-panel/utils.ts` with focused Vitest coverage.
  Browser storage reads/writes used by PlayerPanel, interactive text, reading
  bed, media memory, and bookmarks now route through
  `web/src/utils/browserStorage.ts` with focused Vitest coverage. Media-session
  seek/track skip handling, keyboard navigation, and registered sentence
  sequence skipping now live in
  `web/src/components/player-panel/usePlayerPanelMediaNavigation.ts` with
  focused hook coverage. Panel/fullscreen navigation control variants now live
  in `web/src/components/player-panel/PlayerPanelNavigationGroups.tsx` with
  focused prop-routing coverage. Player content empty/stage wrapper now lives
  in `web/src/components/player-panel/PlayerPanelContent.tsx` with focused
  rendered coverage. Boundary states for load errors, initial loading, and no
  selected job now live in `web/src/components/player-panel/PlayerPanelBoundaryState.tsx`
  with focused rendered coverage. Sentence-jump datalist rendering now lives in
  `web/src/components/player-panel/PlayerPanelSentenceJumpDatalist.tsx` with
  focused rendered coverage. Compact search panel visibility now lives in
  `web/src/components/player-panel/PlayerPanelSearchSlot.tsx` with focused
  rendered coverage for panel and fullscreen placement. Chapter active-id and
  jump-target resolution now live in `web/src/components/player-panel/utils.ts`
  with focused utility coverage. The repo-owned `test-web-playback-focused`
  target now covers live-media state/timing, PlayerPanel helper/rendering
  splits, subtitle overlay utilities, audio URL/chunk indexing, sequence
  planning, and browser-storage persistence so the reusable Apple pipeline Web
  gate can catch playback regressions alongside Create and Library work.
- `web/src/components/Sidebar.tsx` - 100 lines. Status: pipeline-view
  detection, sidebar language/label/status/stage/glyph/progress resolution,
  and image-wait status now live in
  `web/src/components/sidebar/sidebarUtils.ts` with focused Vitest coverage.
  Reusable job overview row rendering now lives in
  `web/src/components/sidebar/SidebarJobRow.tsx` with focused rendered coverage.
  Active-player entry rendering now lives in
  `web/src/components/sidebar/SidebarPlayerButton.tsx` with focused rendered
  coverage. Creation navigation for Narrate Ebook, generated books, subtitles,
  YouTube source review, and video dubbing now lives in
  `web/src/components/sidebar/SidebarCreationLinks.tsx` with focused rendered
  coverage. Admin navigation and observability links now live in
  `web/src/components/sidebar/SidebarAdminLinks.tsx` with focused rendered
  coverage. Job overview bucketing and section rendering now live in
  `web/src/components/sidebar/SidebarJobOverview.tsx` with focused rendered
  coverage.
- `web/src/components/book-narration/BookNarrationForm.tsx` - 675 lines.
  Status: recent-job path normalization, resume-window inference, latest
  input/base selection, latest language/lookup-cache defaults, and rerun
  prefill state mapping, section metadata merging, edited-field preservation,
  submit-requirement resolution, backend image-default merging, and edited
  image-default restoration, plus default-settings compaction and target-language
  normalization now live in
  `web/src/components/book-narration/bookNarrationFormUtils.ts` with focused
  Vitest coverage. Pipeline step tabs and submit action rendering now live in
  `web/src/components/book-narration/BookNarrationStepBar.tsx` with focused
  rendered coverage. Intake, missing-requirement, and submit-error messaging now
  live in `web/src/components/book-narration/BookNarrationSubmitStatus.tsx`
  with focused rendered coverage. Ebook/output file selection dialog routing now
  lives in `web/src/components/book-narration/BookNarrationFileDialog.tsx` with
  focused rendered coverage.

### Apple Apps

Apple currently focuses on auth, browse, playback, offline sync, bookmarks, and settings.

Key Apple files:

- Shell/browse: `ios/InteractiveReader/InteractiveReader/Features/Library/LibraryShellView.swift`
- Jobs list: `ios/InteractiveReader/InteractiveReader/Features/Jobs/JobsView.swift`
- API transport: `ios/InteractiveReader/InteractiveReader/Services/APIClient.swift`
- Job/library API methods: `ios/InteractiveReader/InteractiveReader/Services/APIClient+LibraryJobs.swift`
- Media API methods: `ios/InteractiveReader/InteractiveReader/Services/APIClient+PipelineMedia.swift`

Current Apple API client supports:

- Fetch library items via `/api/library/items`.
- Fetch jobs via `/api/pipelines/jobs`.
- Fetch job status via `/api/pipelines/{job_id}`.
- Delete jobs, delete library items, move jobs to Library.
- Fetch media/timing for jobs and library entries.
- Fetch book creation options via `/api/books/options`.
- Submit pipeline jobs via `/api/pipelines`.
- Upload EPUB files via `/api/pipelines/files/upload`.
- Submit generated book jobs via `/api/books/jobs`.
- Submit subtitle jobs via `/api/subtitles/jobs`.
- Submit YouTube dubbing jobs via `/api/subtitles/youtube/dub`.

Current Apple UI partially exposes:

- Native Create flow. Status: `AppleBookCreateView.swift` now delegates create
  mode availability, submit-button presentation, base-output derivation,
  subtitle model labels, subtitle model option-list construction, ASS/subtitle/
  YouTube clamp and formatting helpers, YouTube offset normalization, draft
  construction, backend default resolution, backend language/voice option
  building, source selection, and routing to focused `AppleBookCreate*`
  presentation/helper files. Create draft value types, shared language models,
  and history/default structs now live in `AppleBookCreateModels.swift`, while
  mode, submit-state, tuning, format, and provider options live in
  `AppleBookCreateOptions.swift`, and job-history payload parsing
  lives in `AppleBookCreateHistoryParsing.swift`; subtitle and YouTube request
  body builders live in `AppleBookCreateMediaPayloads.swift`, keeping the
  support file as a thin namespace and the view model focused on submission
  work. Subtitle and YouTube output control subviews live in
  `AppleBookCreateOutputControls.swift`; generated-book output controls live
  in `AppleBookCreateGeneratedOutputControls.swift`, while generated-book
  image controls live in `AppleBookCreateGeneratedImageControls.swift`.
  Reusable Create value controls live in `AppleBookCreateValueControls.swift`,
  letting `AppleBookCreateOutputSection.swift` own only section-level routing,
  while shared source action rows in `AppleBookCreateSourceControls.swift`
  keep EPUB, subtitle, and NAS video refresh/extract controls consistent through
  the shared busy action button in `AppleBookCreateMetadataViews.swift`.
  Media metadata controls live in `AppleBookCreateMediaMetadataControls.swift`
  while `AppleBookCreateMediaMetadataSections.swift` owns the metadata section
  routing. Advanced metadata JSON editing, artwork preview, status, and action
  subviews now live in `AppleBookCreateMetadataViews.swift`, trimming repeated metadata UI while
  preserving the tvOS-safe JSON editor fallback. Metadata JSON parsing/formatting
  helpers now live in `AppleBookCreateMetadataJSON.swift`, and subtitle/YouTube
  metadata lookup, cache clearing, and draft-editing actions now live in
  `AppleBookCreateViewModel+Metadata.swift`. EPUB/subtitle file
  import normalization and local import selection plans now live in
  `AppleBookCreateFileImport.swift`, metadata lookup
  source-name derivation now lives in `AppleBookCreateMetadataSources.swift`,
  and Create persistence key construction now lives in
  `AppleBookCreateStorageKeys.swift`, keeping API/user-scoped local file, lookup, and
  UserDefaults formats contract-pinned outside the main view. YouTube NAS
  base-dir/selection and subtitle show-original preference reads/writes now
  live in `AppleBookCreatePreferences.swift`, as do shared language and
  lookup-cache preference JSON reads/writes, keeping scoped trimming, removal,
  and codec behavior contract-pinned outside the main view. Create lifecycle
  loading, field-change, and section callback side effects are now named
  handlers in the view instead of inline modifier/section bodies, and
  successful job submission completion shares one intake-refresh/notify handler
  while the view model shares one submit-state/error wrapper in
  `AppleBookCreateViewModel+Submission.swift`.
  iOS document importer modifier wiring for local EPUB/subtitle selection now
  lives in `AppleBookCreateFileImporterModifier.swift`, keeping platform
  document-picker modifiers out of the main Create view while preserving the
  same iPad/iPhone import handlers.
  Narration language/voice routing now lives in
  `AppleBookCreateNarrationSection.swift`, and the
  iOS/iPad searchable full-language selector lives in
  `AppleBookCreateLanguageSelector.swift`. Source section routing lives in
  `AppleBookCreateSourceSection.swift`, while Narrate EPUB server-source,
  subtitle source, local-import, and chapter-range controls live in
  `AppleBookCreateSourceControls.swift`, and NAS YouTube video/subtitle plus
  embedded subtitle extraction controls live in
  `AppleBookCreateYoutubeSourceControls.swift`. Reusable default source selection
  decisions, including NAS YouTube scope refreshes, live in
  `AppleBookCreateSourceSelection.swift`. Subtitle time-range and YouTube
  offset-range validation now use pure support helpers that preserve the
  existing visible error messages. Backend default resolution and edited-field
  preservation now live in support too, so backend-driven Apple Create defaults
  stay pinned outside the SwiftUI state assignment code. Backend language and
  voice inventory option building is also centralized in support, including
  per-target-language voice override option maps, preserving selected voices
  that are absent from backend inventory. The Apple journey runner can now
  select Create picker options and assert non-empty field values, with opt-in
  iPhone/iPad Create-readiness Make targets that verify Narrate EPUB, subtitle,
  and YouTube/NAS default source loading against a populated API. The shared
  Create-readiness journey now also scrolls through generated-book output,
  subtitle processing, and YouTube dubbing settings controls after those
  defaults load, so unattended simulator checks prove the practical default
  settings are reachable across the native Create modes.
  Create lifecycle side-effect wiring now lives in
  `AppleBookCreateLifecycle.swift`, keeping task/on-change handlers and EPUB/
  subtitle delete confirmations target-wired outside the main Create view.
  Apple Create language controls are now contract-pinned to the shared
  backend/Web language catalog, so iPhone/iPad searchable selectors and tvOS
  pickers keep the full Web-supported language list even when runtime defaults
  or older option responses are sparse. `scripts/generate_language_catalogs.py`
  now regenerates the shared assets language list plus the Web and Apple catalog blocks from
  `modules/language_constants.py`, and the Apple contract gate runs the
  generator in `--check` mode so future language additions fail fast if a
  surface drifts. The iPad regular-width Create layout now
  keeps the left setup pane source-only and moves Book, Metadata, Job Settings,
  Narration, Output, status, and submit controls into the right-side settings
  pane so creation settings use the detail area instead of reading like sidebar
  content; the reusable Create container shell, list/form chrome, and
  regular-width split layout now live in `AppleBookCreateLayout.swift`. Create status and submit sections now live in
  `AppleBookCreateStatusViews.swift`, keeping loading, intake, success, Web
  handoff, and submit-button UI target-wired outside the main Create view.
- Upload/reupload library source files. Status: iPhone/iPad Library rows can
  replace an existing library item's source through the same
  `/api/library/items/{job_id}/upload-source` backend route used by Web. The
  native flow now reviews the selected replacement file before upload and
  accepts common book/video source extensions (`.epub`, `.pdf`, `.mp4`,
  `.mkv`, `.mov`, `.webm`) to match the Web edit form.
- ISBN metadata preview/apply. Status: iPhone/iPad Library rows can fetch
  `/api/library/isbn/lookup` previews and then apply the ISBN through
  `/api/library/items/{job_id}/isbn`, matching the Web lookup/apply contract.
- TV-safe source diagnostics. Status: iPhone, iPad, and Apple TV Library rows
  expose read-only Source Details with stored-source, file, type, relative path,
  status, and media completion diagnostics without upload/edit controls.

## Backend Optimization Targets

Initial backend hotspots to inspect before changing behavior:

- Job listing/count path: `modules/webapi/routes/jobs_routes.py`, `modules/services/pipeline_service.py`, `modules/services/job_manager/manager.py`, and `modules/services/job_manager/stores.py`.
- Metadata loading and chunk traversal: `modules/metadata_manager.py`, `modules/services/job_manager/persistence.py`, and `modules/webapi/routes/media/media_list.py`.
- Search across jobs/library: `modules/search/service.py` and `modules/webapi/routes/library_routes.py`.
- YouTube NAS inventory and linked-job indexing: `modules/webapi/routers/subtitle_utils/youtube_routes.py`.
- Library media payload building: `modules/library/library_service.py`, `modules/library/library_sync.py`, and `modules/webapi/routers/library.py`.

Optimization candidates:

- Guard paginated `/api/pipelines/jobs` response shape before changing list internals. Status:
  backend tests now pin `total`, `offset`, `limit`, newest-first route ordering,
  access payload normalization, generated files, job labels, and parameter
  snapshots; service tests pin active admin pagination, persisted-only
  store pagination, and metadata-only non-admin counts/lists that hydrate only
  the requested visible page.
- Audit repeated filesystem metadata reads during job list/library list rendering.
  Status: `/api/pipelines/jobs` now skips filesystem image prompt summary reads
  while preserving those rich summaries for single-job status responses.
- Add lightweight timing/log counters around job list, library list, media manifest, and search endpoints.
  Status: Library item listing now records a Prometheus duration histogram and
  token-safe aggregate logs for success/error paths without recording raw
  search queries, user identifiers, auth headers, or tokens. Pipeline media
  search now records the same token-safe duration and aggregate hit-count
  telemetry for blank, forbidden, not-found, and success outcomes. Pipeline job
  listing now records token-safe duration and pagination/result-count telemetry
  for success/error outcomes without logging user ids or job ids. Pipeline media
  manifests now record token-safe duration and aggregate category/file/chunk
  counts for completed and live manifest routes without logging job ids, user
  ids, auth headers, tokens, or file names. Sentence-image single and batch
  metadata lookups now record the same token-safe media-route duration
  telemetry and aggregate count/missing logs without logging job ids, user ids,
  auth headers, tokens, paths, filenames, or raw sentence content. Library
  media manifests now use the same token-safe aggregate route telemetry for
  success, missing-item, and error paths, without logging job ids, user ids,
  auth headers, tokens, NAS paths, or filenames. Offline export create/download
  routes now record token-safe duration telemetry and aggregate logs without
  logging source ids, export ids, user ids, file paths, filenames, auth headers,
  or tokens. Local media file streaming now records token-safe setup duration
  telemetry and aggregate logs for full, partial, unsatisfiable-range, and
  not-found results across storage and library media file downloads without
  logging paths, filenames, job ids, user ids, auth headers, tokens, or raw
  range values.
- Prefer precomputed or cached job summary fields for list rows while keeping
  full metadata available on detail/media routes. Status:
  `/api/pipelines/jobs` now uses compact row result summaries so list rendering
  preserves titles, book/media metadata, generated files, parameter snapshots,
  and Apple/Web recent-default fields without materializing heavy full pipeline
  results; single-job status/detail routes still return rich result payloads.
- Avoid avoidable library repository reads in shared search paths. Status:
  `/api/pipelines/search` now defers the library item lookup until the pipeline
  job is missing, so normal active-job media searches avoid a library sync
  lookup while preserving library fallback behavior for archived items and
  unknown-job 404s.
- Avoid avoidable chunk metadata reads in shared search paths. Status:
  generated media search now skips per-chunk metadata JSON reads when the
  generated chunk already carries id/range/sentence fields and a searchable
  text file, while preserving metadata fallbacks for sparse chunk entries and
  metadata-only sentence text; search also resolves the friendly job label
  once per job and reuses it across multiple chunk hits. Generated-files search
  also continues when a job root exists but its metadata manifest is absent,
  using the chunk data already present on the job and skipping eager manifest
  iteration in that case.
- Avoid full job hydration when tagging YouTube NAS inventory with linked jobs.
  Status: `/api/subtitles/youtube/library` now asks `PipelineJobManager` for
  visible `youtube_dub` metadata only, preserving role-based access checks while
  avoiding reconstruction of every visible stored job before Apple/Web Create
  default video pickers render. The route also records token-safe duration
  telemetry and aggregate video/subtitle/linked-job counts without logging NAS
  paths, filenames, job ids, user ids, auth headers, or tokens. The NAS scanner
  also reuses each `os.walk` folder file list for subtitle matching instead of
  re-reading the same directory once per video, keeping large default video
  pickers lighter on NAS-backed folders. Linked-job indexing is now filtered to
  the discovered video tokens, and empty NAS listings skip job metadata reads
  entirely.
- Keep backend source pickers resilient on NAS-backed folders. Status:
  `/api/pipelines/files` now stats each visible ebook/output candidate once and
  skips entries that disappear or become unreadable during listing; EPUB
  discovery now recurses into visible books-root subfolders while pruning hidden
  folders, so Web and Apple Create defaults can pick the latest NAS book even
  when ebooks are grouped by author or series. It also treats transient
  source/output directory scan failures as an empty picker response, preserving
  Web and Apple Create usability during NAS remounts or concurrent cleanup.
  Newest-first EPUB defaults are preserved, and EPUB matching is
  case-insensitive so NAS files ending in `.EPUB` are eligible for the same
  default-source flow. `/api/pipelines/files` deletion now treats
  already-vanished, in-scope EPUB sources as an idempotent cleanup success
  while still rejecting paths outside the books root. `/api/subtitles/sources`
  now applies the same transient directory-scan tolerance and stale-entry skip
  when building Web/Apple subtitle source pickers, and recursively discovers
  visible nested subtitle files while preserving SRT/VTT-first newest-default
  ordering, so NAS remounts, vanished subtitle paths, or series-organized
  subtitle folders do not become broken default selections.
  `/api/subtitles/delete-source` now treats already-vanished, in-scope subtitle
  sources as idempotent cleanup results while still rejecting paths outside the
  allowed base directory. EPUB and subtitle source picker routes now share
  token-safe duration telemetry with aggregate source/output counts and no NAS
  path, filename, job id, user id, auth header, or token logging. The
  manifest-registered `test-backend-pipeline-sources` target now covers EPUB
  source listing, vanished-source deletion, outside-root rejection, and local
  EPUB upload persistence through `/api/pipelines/files/upload`, so the shared
  backend pipeline protects the picker/import paths used by Web and Apple
  Create. The
  NAS YouTube/video scanner also skips video and subtitle sidecar candidates
  that vanish after `os.walk()` and prunes hidden folders/files, keeping Web
  Video Dubbing and Apple Create source pickers usable during concurrent
  downloads, cleanup, or temporary NAS staging folders. YouTube
  download finalization now applies the same stale-entry tolerance when sorting
  downloaded subtitle files, partial recovery files, and muxed output files, so
  a transient NAS directory race can still fall back to a usable downloaded
  artifact instead of losing a completed download. Downloaded-video cleanup
  uses the same stale-entry tolerance while discovering adjacent subtitle
  artifacts before folder removal. Already-vanished NAS video and subtitle
  sidecar selections with valid suffixes now return structured `missing`
  results instead of picker-breaking 404s.
- Keep all auth/session headers and token handling out of logs and docs.
  Status: the repo-owned `test-backend-auth-session` target now covers the
  password login, compact session restore payload, logout invalidation, missing
  or invalid token rejection, and auth route duration metric used by Web and
  Apple clients, and the shared Apple backend manifest runs it as an
  auth/session regression gate.

## Parity Roadmap

### Milestone 1: Shared Creation Contract

Define stable client DTOs for creation:

- `PipelineRequestPayload`
- EPUB upload response
- generated book request/response
- subtitle job request
- YouTube dubbing request

Expected Apple work:

- Add focused API client extensions for creation/upload.
- Add unit tests for encoding and path selection without printing tokens.
- Keep physical device deployment attended and on-request only.

Status: API plumbing and generated-book payload coverage are in place. Continue
expanding contract checks whenever a new Web-only creation flow becomes native.
Repo-owned physical-device helpers now expose attended preflight,
shared-pipeline signed-build-only, shared-pipeline deploy dry-run wrappers, and
a full-entitlement signing planner for cached-profile iPhone/iPad fallbacks; the
unattended deploy helper can now fall back from a failed Xcode CLI build to a
verified current signed full-entitlement app artifact before installing, so the
golden recipe preserves iCloud/Push/Sign in with Apple without hand-editing
`--skip-build` paths; the
legacy entitlement-stripping fallback requires
`APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES` so iCloud/Push/Sign in with Apple
validation keeps the full entitlement set by default. The shared-pipeline
runtime contract now advertises the native subtitle source cleanup endpoint
alongside source listing and submission endpoints, and the repo-owned deploy
readiness hook validates the Create, Library action, offline export, and
playback-state sections from `/api/system/runtime`, so Apple Settings,
Create-readiness preflights, and attended device-update preflights catch
backend/app drift before a simulator journey or device install tries to use
stale NAS cleanup, Library, export, bookmark, or resume controls. The shared-pipeline
office-iPad Create-readiness lane now has repo-owned
`apple-pipeline-ipad-create-readiness` and dry-run shortcuts that delegate to
the registered `ipados-create` app-owned journey without depending on an
available iPhone. Local office-iPad iteration now also has repo-owned
office-iPad local build gate and office-iPad local verification gate targets:
`build-apple-office-ipad-surfaces` and `verify-apple-office-ipad-surfaces`
compile the iPad simulator and local Mac Designed for iPad/iPhone
surfaces, plus the iPad-destination UITest build in the verification lane,
without invoking iPhone simulator or physical-device deployment helpers. The
shared pipeline also has a focused `make test-apple-local-surface-contract`
gate for simulator/local Mac surface wiring without compiling apps. Apple TV now has matching repo-owned
`test-e2e-tvos-create-readiness` and shared-pipeline
`apple-pipeline-tvos-create-readiness`/dry-run shortcuts through the registered
`tvos-create` journey, keeping native tvOS Create checks simulator-only unless
a physical Apple TV deploy is explicitly requested.

### Milestone 2: iPad/iPhone Native New Job

Apple started with generated audiobook creation because it does not require
attended document import and can safely reuse `/api/books/options`. iPhone/iPad
now also expose a Narrate EPUB mode for server-side EPUB paths and local EPUB
document import/upload through the same backend file endpoint used by Web.

Target Apple UX:

- Add a `New Job` entry to the iPad/iPhone browse shell.
- Use SwiftUI `Form`/`NavigationStack` with sections for source, languages, audio, output, and advanced settings.
- Support simple existing-file submission first. Status: iPhone/iPad support
  server-side EPUB path submission through the Apple Create form.
- Add EPUB file import/upload next using document picker on iPad/iPhone.
  Status: implemented in Apple Create Narrate EPUB by picking a local `.epub`,
  uploading it to `/api/pipelines/files/upload`, and submitting the returned
  server path to `/api/pipelines`. Narrate EPUB history defaults now reuse prior audio, output, translation, transliteration, lookup-cache, voice overrides, and chunking settings while preserving any fields edited in the current form; generated-book history also restores source-book continuation context and voice overrides. Create history no longer replaces newer backend-selected NAS EPUB/subtitle/video sources.
- Route success to the new job in Jobs and start auto-refresh. Status: Apple
  Create now switches to Jobs after successful submission, selects the created
  job, aligns the Jobs filter with the created job's category, and starts the
  Jobs auto-refresh loop so fresh generated-book, Narrate EPUB, subtitle, and
  YouTube jobs are immediately visible.

Keep Apple TV creation constrained to remote-friendly server/NAS workflows.
Status: the tvOS browse picker exposes Create, the native routing helper uses
the shared Create mode list, and local document import remains iOS/iPadOS-only
so Apple TV can submit generated-book, Narrate EPUB, subtitle, and YouTube jobs
from backend-visible sources without becoming the richest editing surface. The
strict Create-readiness journey can now run on tvOS via
`make test-e2e-tvos-create-readiness` and through the reusable pipeline
`tvos-create` profile. The tvOS Create view now runs the same server-backed
EPUB, subtitle, and YouTube NAS source refreshes as iPhone/iPad while keeping
local file import behind the iOS/iPadOS-only document picker.

### Milestone 3: Web UI Redesign

Redesign around the same information architecture as Apple:

- Jobs
- Library
- Search
- Create
- Settings/Admin

Refactor before restyling:

- Split large route files into page shell, toolbar, filters, list/detail, and action modules.
- Move repeated status/glyph/metadata row logic into shared components.
- Isolate Library metadata helpers before visual redesign. Status:
  `LibraryPage.tsx` now imports tested helpers for item type, fallback labels,
  nested TV/YouTube metadata, image URLs, counts, and upload dates from
  `web/src/pages/library/libraryPageMetadata.ts`.
- Isolate YouTube dubbing helpers before visual redesign. Status:
  `VideoDubbingPage.tsx` now imports tested helpers for inline subtitle
  extraction defaults, target-language voice option building, and rerun-prefill
  mapping from
  `web/src/pages/video-dubbing/videoDubbingUtils.ts`.
- Isolate job progress math before visual redesign. Status:
  `JobProgress.tsx` now imports tested helpers for generated-file stat lookup,
  LLM batch progress, lookup-cache progress, and progress labels from
  `web/src/components/job-progress/jobProgressUtils.ts`.
- Isolate subtitle overlay helpers before visual redesign. Status:
  `SubtitleTrackOverlay.tsx` now imports tested helpers for ASS cue lookup,
  token navigation, selection shadowing, clamping, variant mapping, and
  subtitle TTS voice options from
  `web/src/components/video-subtitles/subtitleTrackOverlayUtils.ts`.
- Isolate live media state helpers before visual redesign. Status:
  `useLiveMedia.ts` now imports tested helpers for live media state shape,
  generated-file extraction, media bucket merging, chunk merging, audio-track
  detection, and chunk-sentence detection from `web/src/hooks/liveMediaState.ts`,
  plus modern and legacy timing normalization from
  `web/src/hooks/liveMediaTiming.ts`.
- Isolate Library list grouping before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for row layout type detection,
  title/author/genre fallback labels, and author/genre/language grouping from
  `web/src/components/library-list/libraryListUtils.ts`.
- Isolate Library list media metadata resolvers before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for book summaries, TV/episode
  metadata, subtitle genre/summary/image values, YouTube metadata, source
  badges, and media asset URLs from
  `web/src/components/library-list/libraryListMediaUtils.ts`. Library row
  book/subtitle/video media cells, job-type glyphs, status stacks, and resume
  badges now live in focused `library-list` components with direct rendering
  coverage, leaving the main list responsible for grouping and routing.
- Isolate Library list action gating before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for permission defaults, export
  readiness, and disabled action states from
  `web/src/components/library-list/libraryListActions.ts`.
- Isolate Player panel active selection before visual redesign. Status:
  `PlayerPanel.tsx` now imports tested helpers for selected text item,
  selected chunk, and active text chunk resolution from
  `web/src/components/player-panel/utils.ts`, and player preference storage now
  uses the shared safe browser storage wrapper. Original/translation audio
  visibility persistence now lives in a focused tested hook so Web playback
  defaults can evolve alongside Apple playback settings without growing the
  panel coordinator. Active text selection, selected chunk lookup, interactive
  audio cataloging, and audio-driven active chunk fallback now live in a
  focused tested hook rather than inline in the panel coordinator. Interactive
  document preview/fallback content and placeholder visibility now resolve
  through a tested pure helper so the panel coordinator no longer owns those
  display-state branches inline. Panel chrome decisions for initial loading,
  media presence, playback/fullscreen disabled states, wake-lock intent,
  back-to-library visibility, and advanced-control gating now also live in a
  tested pure helper.
- Keep generated-audiobook defaults consistent across Web and Apple. Status:
  Web Create now applies backend topic, title, genre, author, sentence,
  generated-source image, and pipeline defaults from `/api/books/options`
  through tested helper functions, preserving explicit prompt edits, including
  cleared fields, that happen before defaults arrive. Apple Create now also
  accepts multi-target backend defaults, using the first target for the native
  picker and preserving remaining de-duplicated targets in the visible
  Additional target languages field. Web Create now also passes
  `/api/books/options` supported input/output language lists into the reusable
  Narrate Ebook form, and focused component/page tests prove backend-advertised
  languages appear in the pickers even when they are not selected defaults.
  `/api/books/options` now reads and normalizes generated-source image defaults
  from backend config so Web and Apple start from the same image
  pipeline/style/context/size values. Apple Create voice inventory matching and
  preview keys now normalize language selections through the same full Apple
  language catalog used by the pickers, instead of a narrow local name map, and
  native voice previews now carry localized sample sentences across the same
  backend/Web language catalog instead of only the original six languages. The
  manifest-registered `test-backend-audio-routes` target now exercises
  `/api/audio`, `/api/audio/voices`, and `/api/audio/match` with stubbed
  synthesis, so the shared pipeline catches voice inventory and preview drift
  before Apple Create or Web creation surfaces rely on it. The
  native preview sample catalog now lives in its own Create helper file and is
  wired into the Xcode project plus creation-payload compile contract so future
  catalog changes are verified across Apple targets. Focused parity tests now
  compare Web and Apple preview samples exactly, catching subtle punctuation or
  diacritic drift as well as missing language codes. The reusable Apple
  pipeline also has a focused `make test-apple-language-catalogs` contract so
  language picker regressions can be run directly without the full Apple suite.
- Keep Zustand selectors granular to avoid wide re-renders.
- Use visual redesign work only after the core component ownership is smaller.

### Milestone 4: Expand Native Creation

After Narrate Ebook:

- Subtitle job creation on iPad/iPhone. Status: Apple Create submits existing
  server-side subtitle paths or local SRT/VTT/ASS uploads with languages,
  output format, timing, output toggles, provider/model selection, ASS
  typography, transliteration mode/model, LLM batch-size tuning, and
  worker/render batch-size tuning, mirror-to-source control, and pre-submit TV
  metadata lookup plus job label/show/season/episode/title/airdate edits
  through `/api/subtitles/jobs`; the native metadata section now also exposes
  an editable lookup filename before lookup/refresh plus TV metadata cache
  clearing, editable TVMaze poster/episode-still artwork URL previews, and
  TMDB/IMDb ID edits. Server-side ASS sources now stay visible in Apple Create
  too, while SRT/VTT remain preferred defaults when available to match Web
  source selection, and Apple Create can delete selected backend subtitle
  sources through the same cleanup endpoint Web uses. Native time fields validate and normalize Web-style
  `MM:SS`, `HH:MM:SS`, and `+offset` values before submit.
- Generated book job creation on iPad. Status: Apple Create submits
  generated-book jobs through `/api/books/jobs`; generated-book mode now also
  exposes source-book title, author, genre, and summary context on iPhone/iPad
  and sends those fields through the shared generator contract so
  continuation-style jobs can start with explicit source metadata. The Create
  Book backend now normalizes that source context once per request and reuses it
  for sentence prompts, metadata, config, and pipeline snapshots so Web previews
  and Apple job submissions stay aligned; Narrate EPUB can delete selected
  backend EPUB sources through the same `/api/pipelines/files` cleanup endpoint
  Web uses; `/api/books/jobs` enqueue tests now pin the trimmed source-context
  snapshot before the background worker starts. Apple Create readiness preflight
  now also requires sane generated-book sentence bounds, language, voice, and
  pipeline defaults from `/api/books/options`, and the native Create readiness
  journey opens Generate before the media modes, scrolls as needed, and types a
  source-book continuation context so unattended iPhone/iPad simulator checks
  prove the generated-book controls are drivable. The shared pipeline also has
  a focused `make test-apple-create-readiness-contract` gate for the preflight
  parser/default-source/default-settings contract.
- YouTube dubbing as iPad-first review/submit flow. Status: Apple Create now
  exposes an iPhone/iPad YouTube Dub mode for backend/NAS video and subtitle
  files, including NAS library video/subtitle pickers, remembered base
  directories, embedded subtitle stream inspection/extraction through
  `/api/subtitles/youtube/subtitle-streams` and
  `/api/subtitles/youtube/extract-subtitles`, and
  `/api/subtitles/youtube/dub` submission with language, voice, clip-window,
  batching, provider/model, output, lookup-cache options, voice preview, and
  pre-submit TV/YouTube metadata lookup, TV/YouTube metadata cache clearing,
  editable TVMaze poster/episode-still and YouTube thumbnail URL previews,
  plus key title/channel/series/episode/TMDB/IMDb edits that are sent with the
  job. Apple YouTube dubbing now resolves target languages through the shared
  Apple catalog code map before submission, matching Web's `target_language`
  code payloads, and keeps video transliteration/lookup-cache toggles separate
  from book job settings so defaults do not leak across modes. Apple Create now
  also exposes advanced metadata JSON editors for
  subtitle and YouTube jobs, so iPad/iPhone can review and apply full nested
  metadata payloads beyond the high-value native fields before submission.
- Library source reupload on iPhone/iPad. Status: Library row context menus now
  expose Replace Source File, open a document picker for common book/video
  source files, review the selected file before upload, post it to
  `/api/library/items/{job_id}/upload-source`, and replace the refreshed row
  returned by the backend. Apple TV remains playback-first. The public runtime
  descriptor now advertises the shared Library action paths for listing,
  metadata edits, source upload, ISBN lookup/apply, and metadata enrichment, and
  the Apple client builds these paths through matching local constants.
- Library source diagnostics on Apple TV. Status: Library row context menus now
  expose read-only Source Details on Apple TV as well as iPhone/iPad, keeping
  remote navigation simple and avoiding mutation controls.
- Library ISBN metadata preview/apply on iPhone/iPad. Status: Library row
  context menus now expose Preview ISBN Metadata, fetch
  `/api/library/isbn/lookup` results in a sheet, and can then apply the ISBN
  through `/api/library/items/{job_id}/isbn` before replacing the refreshed row
  returned by the backend.
- Apple TV gets read-only job templates or retry controls only if remote navigation stays simple.

## Feature Backlog

Suggested features to evaluate after parity scaffolding:

- Cross-surface job templates: save a Web configuration and reuse it from Apple. Status:
  backend now exposes authenticated `/api/creation/templates` list/save/delete
  storage with recursive secret-key stripping, and the public runtime descriptor
  advertises the template endpoints for Web/Apple clients. Web Narrate Ebook and
  generated-book forms can now save sanitized creation templates from their
  current settings. Native Apple Create on iPhone/iPad can list those saved
  generated-book and Narrate EPUB templates, apply the Web form state into its
  source, language, narration, output, image, metadata, and worker controls, and
  delete stale saved templates after review. Applied fields are marked as edited
  so later backend/history defaults do not overwrite them. Apple Create also
  applies saved subtitle and YouTube dubbing templates into source, language,
  model, timing, output, metadata JSON, and tuning controls. Web Subtitle Tool
  and Video Dubbing can now save sanitized subtitle and YouTube templates from
  their current settings for Apple reuse.
- Draft jobs: start on iPad, finish advanced settings on Web.
- Creation handoff: Apple app opens the corresponding Web creation URL for unsupported advanced options. Status:
  iPhone/iPad Apple Create now exposes Open Web Create, derives a token-free Web URL from the configured API base,
  and maps native creation modes to validated Web `?view=` deep links. The
  shared Create-readiness journey now also verifies the native Web handoff
  button is reachable after driving generated-book, subtitle, and YouTube
  default settings.
- Job health timeline: show backend stage durations and slow phases in Web and iPad. Status:
  Apple Jobs rows now surface the latest backend stage with elapsed runtime
  and ETA from progress events, giving iPad/iPhone a compact health signal
  while jobs are running.
- Backend queue pressure indicator: expose accepting/backpressure state in Settings before users submit long jobs. Status:
  Web admin System status now shows job intake state, pending queue depth,
  active running jobs, and soft-limit warnings from the backend
  `/api/admin/system/status` response; `/api/pipelines/intake/status` now
  exposes a narrower authenticated editor/admin-safe queue snapshot for
  creation surfaces; Web book creation and Apple Create display that status
  before submit, show a loading state while the snapshot is checked, include
  delayed-job and soft/hard-limit details, warn under pressure, block
  submission when the backend hard queue limit is reached, and refresh the
  snapshot after successful enqueue. Web Subtitle Tool and Video Dubbing now
  reuse the same intake callout and capacity gate before enqueueing their own
  long-running jobs. The shared pipeline backend gate now includes the focused
  system-route pytest.
- Smart resume cards: show "continue listening", "newly completed", and "needs attention" across all surfaces. Status:
  Apple browse rows now surface local-only, iCloud-only, and synced resume
  evidence in the shared Library/Jobs/search row badge instead of hiding valid
  local fallback resume points; synced badges display the freshest stored
  resume point so iPhone, iPad, and tvOS list surfaces agree with the playback
  resume decision. Web Library rows now also read the existing per-job
  `media-memory:<job_id>` session resume cache and display a compact Continue
  badge next to the status badge without adding an extra list-time API
  waterfall. The public runtime descriptor now advertises bookmark and resume
  playback-state paths, including the batch resume list endpoint, so Apple and
  shared-pipeline preflights can catch playback-state contract drift; Apple
  Settings also surfaces this playback-state contract in the Create readiness
  journey so simulator checks validate the routes the app uses for bookmark and
  resume sync. Apple Library and Jobs list refresh now batch-fetch backend
  resume evidence for the visible row IDs through the shared snapshot provider,
  preserving the same local/iCloud badge decisions while avoiding one request
  per row. The filesystem resume service now resolves filtered `GET
  /api/resume?job_id=...` requests through direct per-job reads and sorts before
  applying the limit, so Web/Apple list badges do not scan every stored resume
  file and still return the freshest requested entries first. The repo-owned
  `test-backend-playback-state` target now covers resume routes, bookmark
  routes, and the optimized filtered resume service path, and the shared Apple
  backend pipeline manifest runs it as a playback-state regression gate. The
  repo-owned `test-backend-reading-beds` target now also covers the
  reading-bed catalog, admin upload/default update, uploaded file streaming,
  and cleanup fallback used by Web playback controls plus Apple playback and
  offline sync, and the shared Apple backend manifest runs it as a
  reading-bed regression gate. The repo-owned `test-backend-notifications`
  target now covers Apple Settings notification device registration,
  preferences, test sends, rich test sends, disabled-server messaging, and
  authentication guards without APNs credentials, and the shared Apple backend
  manifest runs it as a notification regression gate.
- Shared media diagnostics: surface missing timing/audio/image assets without
  opening logs. Status: media manifest responses now include a token-safe
  aggregate diagnostics object with media, chunk, audio, image, timing,
  metadata, URL, and size counts; Web Job Detail now shows a compact manifest
  health strip when diagnostics are available, and Apple playback now decodes
  and shows the same aggregate counts in a compact native strip.
- Offline export from Apple: request `/api/exports` for a completed job/library
  item and show status in Jobs. Status: Apple Jobs and Library rows can request
  offline player exports for completed media, disable duplicate export requests,
  open the returned download URL, and now show a visible Creating offline
  export progress overlay while the backend archive is being prepared. The
  public runtime descriptor now also advertises the offline export create path,
  download URL template, supported source kinds, and player type so Apple and
  shared pipeline preflights can detect export contract drift. Apple Settings
  and the Create readiness journey surface the Library action and offline
  export descriptor sections alongside Create so simulator checks catch drift
  before device deployment. The shared pipeline backend manifest now pins the
  offline export `sourceKinds` and `playerTypes` list values as well as the
  export URLs, so reusable backend preflight fails if the Web/Apple offline
  player payload contract changes. The manifest-registered
  `test-backend-offline-export` target now exercises the `/api/exports` create
  and download routes, including token-safe logging and Prometheus timing
  metrics, so Apple export actions are covered by the regular backend pipeline.

## Verification Contract

Every cross-surface change should pass the relevant subset:

- Backend: targeted `pytest` for touched routers/services, including the
  manifest-registered saved creation-template route slice when template
  behavior changes.
- Web: focused Vitest files plus a production/export build. Use the package
  manager available in the checkout, for example `npm --prefix web test -- --run
  ...` and `npm --prefix web run build`; the Web build script should remain
  package-manager neutral. For ebook-tools, prefer
  `make apple-pipeline-backend-tests`, which runs the manifest registered
  backend pytest bundle through the shared pipeline runner with generated-cache
  cleanup, and `make apple-pipeline-web-checks`, which calls the shared pipeline runner for
  the registered Create, saved-template, Library, Playback, Video Dubbing, and
  Subtitle Tool focused checks, production/export build, and generated-artifact
  cleanup.
- Apple: release contract, iOS/tvOS simulator builds, the iPhone/iPad simulator compile lanes, the iOS UITest build-for-testing lane, the tvOS simulator compile lane, the office-iPad local build/verification gates, the local Apple surface build gate, the local Apple verification gate, `make apple-device-preflight`, `make apple-device-signed-build-only`, `make apple-device-deploy-dry-run`, `make apple-device-full-entitlement-plan`, guarded CoreDevice preflight before confirmed physical-device updates, shared Apple pipeline preflight targets whose aggregate runs contract/backend-health/backend-pytest/Web checks plus simulator/journey orchestration dry-runs without source-sync or physical deployment, `make verify-apple-golden-pipeline` when source-sync is expected to pass before the non-physical aggregate gate, repo-owned shared simulator-smoke and app-owned-journey dry-runs including `make apple-pipeline-orchestration-dry-runs`, and shared pipeline simulator smokes.
- Pipeline: `check_app_source_sync.py`, `check_app_backend.py`, and deploy-delta tests when version/deploy ledger changes.

Physical device deployment remains attended and explicit only.
