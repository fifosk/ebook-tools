# Cross-Surface Parity And Optimization Plan

Last updated: 2026-06-24

## Goal

Bring ebook-tools toward one coherent experience across Web, iPhone, iPad, and Apple TV while preserving existing behavior:

- Web remains the richest creation and administration surface.
- iPad and iPhone gain attended, native creation flows for practical job types.
- Apple TV stays playback-first, with creation limited to safe browse/review controls.
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
- `web/src/pages/LibraryPage.tsx` - 1162 lines. Status: TV/YouTube/library
  title, author, genre, thumbnail, upload-date, ISBN preview merge/cover, and
  tab bucketing and pagination helpers now live in
  `web/src/pages/library/libraryPageMetadata.ts` with focused Vitest coverage.
  Metadata edit submission now also delegates its trimmed payload and changed
  ISBN apply decision to the same tested helper, preserving source upload
  ordering and explicit ISBN clears.
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
  coverage.
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
  when needed.
- `web/src/components/video-subtitles/SubtitleTrackOverlay.tsx` - 1119 lines.
  Status: subtitle cue lookup, token navigation, selection shadowing, clamp
  math, track variant mapping, and TTS voice option helpers now live in
  `web/src/components/video-subtitles/subtitleTrackOverlayUtils.ts` with
  focused Vitest coverage.
- `web/src/components/JobProgress.tsx` - 931 lines. Status: generated-file
  stat lookup, batch progress, sentence/playable stage progress,
  lookup-cache progress, parallelism overview entries, fallback display rows,
  unavailable-translation detection, metadata entry splitting, narrated
  subtitle detection, and progress label helpers now live in
  `web/src/components/job-progress/jobProgressUtils.ts` with focused Vitest
  coverage. OpenLibrary metadata lookup query state, success/error handling,
  backend cache clearing, and reload side effects now live in
  `web/src/components/job-progress/useJobProgressMetadataLookup.ts` with
  focused hook coverage.
- `web/src/components/LibraryList.tsx` - 703 lines. Status: layout type
  detection, title/author/genre fallback labels, and author/genre/language
  grouping now live in `web/src/components/library-list/libraryListUtils.ts`
  with focused Vitest coverage. Book summary, TV/episode metadata, subtitle
  genre/summary/image, YouTube metadata, source-badge, and media asset URL
  resolvers now live in `web/src/components/library-list/libraryListMediaUtils.ts`
  with focused Vitest coverage. Permission defaults, export readiness, and
  disabled action-state rules now live in
  `web/src/components/library-list/libraryListActions.ts` with focused Vitest
  coverage.
- `web/src/components/PlayerPanel.tsx` - 1014 lines. Status: selected text
  item, selected chunk, and active text chunk resolution now live in
  `web/src/components/player-panel/utils.ts` with focused Vitest coverage.
  Browser storage reads/writes used by PlayerPanel, interactive text, reading
  bed, media memory, and bookmarks now route through
  `web/src/utils/browserStorage.ts` with focused Vitest coverage. Media-session
  seek/track skip handling, keyboard navigation, and registered sentence
  sequence skipping now live in
  `web/src/components/player-panel/usePlayerPanelMediaNavigation.ts` with
  focused hook coverage.
- `web/src/components/Sidebar.tsx` - 556 lines. Status: pipeline-view
  detection, sidebar language/label/status/stage/glyph/progress resolution,
  and image-wait status now live in
  `web/src/components/sidebar/sidebarUtils.ts` with focused Vitest coverage.
- `web/src/components/book-narration/BookNarrationForm.tsx` - 708 lines.
  Status: recent-job path normalization, resume-window inference, latest
  input/base selection, latest language/lookup-cache defaults, and rerun
  prefill state mapping, section metadata merging, edited-field preservation,
  submit-requirement resolution, backend image-default merging, and edited
  image-default restoration, plus default-settings compaction and target-language
  normalization now live in
  `web/src/components/book-narration/bookNarrationFormUtils.ts` with focused
  Vitest coverage.

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
  presentation/helper files. Create draft value types, shared language and mode
  models, history/default structs, and creation tuning/format/provider enums
  now live in `AppleBookCreateModels.swift`, while job-history payload parsing
  lives in `AppleBookCreateHistoryParsing.swift`; subtitle and YouTube request
  body builders live in `AppleBookCreateMediaPayloads.swift`, keeping the
  support file as a thin namespace and the view model focused on submission
  work. Output control subviews live in
  `AppleBookCreateOutputControls.swift`, letting
  `AppleBookCreateOutputSection.swift` own only section-level routing.
  Media metadata controls live in `AppleBookCreateMediaMetadataControls.swift`
  while `AppleBookCreateMediaMetadataSections.swift` owns the metadata section
  routing. Advanced metadata JSON editing and artwork preview subviews now live
  in `AppleBookCreateMetadataViews.swift`, trimming repeated metadata UI while
  preserving the tvOS-safe JSON editor fallback. EPUB/subtitle file import
  normalization now lives in `AppleBookCreateFileImport.swift`, metadata lookup
  source-name derivation now lives in `AppleBookCreateMetadataSources.swift`,
  and Create persistence key construction now lives in
  `AppleBookCreateStorageKeys.swift`, keeping local file, lookup, and
  UserDefaults formats contract-pinned outside the main view. Narration
  language/voice routing now lives in
  `AppleBookCreateNarrationSection.swift`, and the
  iOS/iPad searchable full-language selector lives in
  `AppleBookCreateLanguageSelector.swift`. Source selection for newest-first server
  EPUBs, subtitle jobs, and NAS YouTube dubbing lives in
  `AppleBookCreateSourceSection.swift`. Subtitle time-range and YouTube
  offset-range validation now use pure support helpers that preserve the
  existing visible error messages. Backend default resolution and edited-field
  preservation now live in support too, so backend-driven Apple Create defaults
  stay pinned outside the SwiftUI state assignment code. Backend language and
  voice inventory option building is also centralized in support, preserving
  selected voices that are absent from backend inventory. The Apple journey
  runner can now select Create picker options and assert non-empty field values,
  with opt-in iPhone/iPad Create-readiness Make targets that verify Narrate
  EPUB, subtitle, and YouTube/NAS default source loading against a populated
  API.
  Apple Create language controls are now contract-pinned to the shared
  backend/Web language catalog, so iPhone/iPad searchable selectors and tvOS
  pickers keep the full Web-supported language list even when runtime defaults
  or older option responses are sparse. The iPad regular-width Create layout now
  keeps the left setup pane source-only and moves Book, Metadata, Job Settings,
  Narration, Output, status, and submit controls into the right-side settings
  pane so creation settings use the detail area instead of reading like sidebar
  content. Create status and submit sections now live in
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
  ids, auth headers, tokens, or file names. Offline export create/download
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
  pickers lighter on NAS-backed folders.
- Keep all auth/session headers and token handling out of logs and docs.

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
  server path to `/api/pipelines`. Narrate EPUB history defaults now reuse prior audio, output, translation, transliteration, lookup-cache, and chunking settings while preserving any fields edited in the current form.
- Route success to the new job in Jobs and start auto-refresh. Status: Apple
  Create now switches to Jobs after successful submission, selects the created
  job, aligns the Jobs filter with the created job's category, and starts the
  Jobs auto-refresh loop so fresh generated-book, Narrate EPUB, subtitle, and
  YouTube jobs are immediately visible.

Do not add creation to Apple TV in this milestone.

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
  `web/src/components/library-list/libraryListMediaUtils.ts`.
- Isolate Library list action gating before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for permission defaults, export
  readiness, and disabled action states from
  `web/src/components/library-list/libraryListActions.ts`.
- Isolate Player panel active selection before visual redesign. Status:
  `PlayerPanel.tsx` now imports tested helpers for selected text item,
  selected chunk, and active text chunk resolution from
  `web/src/components/player-panel/utils.ts`, and player preference storage now
  uses the shared safe browser storage wrapper.
- Keep generated-audiobook defaults consistent across Web and Apple. Status:
  Web Create now applies backend topic, title, genre, author, sentence,
  generated-source image, and pipeline defaults from `/api/books/options`
  through tested helper functions, preserving explicit prompt edits, including
  cleared fields, that happen before defaults arrive. Apple Create now also
  accepts multi-target backend defaults, using the first target for the native
  picker and preserving remaining de-duplicated targets in the visible
  Additional target languages field.
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
  source selection. Native time fields validate and normalize Web-style
  `MM:SS`, `HH:MM:SS`, and `+offset` values before submit.
- Generated book job creation on iPad. Status: Apple Create submits
  generated-book jobs through `/api/books/jobs`; generated-book mode now also
  exposes source-book title, author, genre, and summary context on iPhone/iPad
  and sends those fields through the shared generator contract so
  continuation-style jobs can start with explicit source metadata.
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
  job. Apple Create now also exposes advanced metadata JSON editors for
  subtitle and YouTube jobs, so iPad/iPhone can review and apply full nested
  metadata payloads beyond the high-value native fields before submission.
- Library source reupload on iPhone/iPad. Status: Library row context menus now
  expose Replace Source File, open a document picker for common book/video
  source files, review the selected file before upload, post it to
  `/api/library/items/{job_id}/upload-source`, and replace the refreshed row
  returned by the backend. Apple TV remains playback-first.
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

- Cross-surface job templates: save a Web configuration and reuse it from Apple.
- Draft jobs: start on iPad, finish advanced settings on Web.
- Creation handoff: Apple app opens the corresponding Web creation URL for unsupported advanced options. Status:
  iPhone/iPad Apple Create now exposes Open Web Create, derives a token-free Web URL from the configured API base,
  and maps native creation modes to validated Web `?view=` deep links.
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
- Smart resume cards: show "continue listening", "newly completed", and "needs attention" across all surfaces.
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
  export progress overlay while the backend archive is being prepared.

## Verification Contract

Every cross-surface change should pass the relevant subset:

- Backend: targeted `pytest` for touched routers/services.
- Web: focused Vitest files plus a production/export build. Use the package
  manager available in the checkout, for example `npm --prefix web test -- --run
  ...` and `npm --prefix web run build`; the Web build script should remain
  package-manager neutral. For ebook-tools, prefer the shared pipeline runner
  `python3 scripts/run_app_web_checks.py --app ebook-tools`, which runs the
  registered Create, Library, Video Dubbing, and Subtitle Tool focused checks,
  production/export build, and generated-artifact cleanup.
- Apple: release contract, iOS/tvOS simulator builds, the iPhone/iPad simulator compile lanes, the tvOS simulator compile lane, the local Apple surface build gate, the local Apple verification gate, guarded CoreDevice preflight before confirmed physical-device updates, shared Apple pipeline preflight targets, and shared pipeline simulator smokes.
- Pipeline: `check_app_source_sync.py`, `check_app_backend.py`, and deploy-delta tests when version/deploy ledger changes.

Physical device deployment remains attended and explicit only.
