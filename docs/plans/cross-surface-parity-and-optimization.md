# Cross-Surface Parity And Optimization Plan

Last updated: 2026-06-23

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
- `web/src/pages/VideoDubbingPage.tsx` - 1156 lines. Status: inline
  subtitle defaulting, playable subtitle filtering, metadata source-name
  resolution, embedded subtitle extractability, voice inventory option
  building, NAS refresh video/subtitle selection, YouTube Dub request payload
  building and clip-offset validation, subtitle extraction/availability
  messages, and job-parameter prefill mapping now live in
  `web/src/pages/video-dubbing/videoDubbingUtils.ts` with focused Vitest
  coverage.
- `web/src/pages/SubtitleToolPage.tsx` - 761 lines. Status: source ordering,
  latest-source selection, submitted-job summary formatting, and rerun prefill
  snapshot mapping, submit validation/payload normalization, and Web-style
  timecode parsing, metadata source-name resolution, ASS selection detection,
  completed-result fetch selection, job sorting, and backend language-default
  normalization, multipart submit `FormData` construction, and metadata draft
  update helpers now live in `web/src/pages/subtitle-tool/subtitleToolUtils.ts`
  with focused Vitest coverage.
- `web/src/components/video-subtitles/SubtitleTrackOverlay.tsx` - 1119 lines.
  Status: subtitle cue lookup, token navigation, selection shadowing, clamp
  math, track variant mapping, and TTS voice option helpers now live in
  `web/src/components/video-subtitles/subtitleTrackOverlayUtils.ts` with
  focused Vitest coverage.
- `web/src/components/JobProgress.tsx` - 962 lines. Status: generated-file
  stat lookup, batch progress, sentence/playable stage progress,
  lookup-cache progress, parallelism overview entries, fallback display rows,
  unavailable-translation detection, and progress label helpers now live in
  `web/src/components/job-progress/jobProgressUtils.ts` with focused Vitest
  coverage.
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
  `web/src/utils/browserStorage.ts` with focused Vitest coverage.
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

- Upload/reupload library source files. Status: iPhone/iPad Library rows can
  replace an existing library item's EPUB/PDF source through the same
  `/api/library/items/{job_id}/upload-source` backend route used by Web.
- ISBN metadata preview/apply. Status: iPhone/iPad Library rows can fetch
  `/api/library/isbn/lookup` previews and then apply the ISBN through
  `/api/library/items/{job_id}/isbn`, matching the Web lookup/apply contract.
  Remaining parity gaps: richer source metadata review before upload and
  TV-safe read-only source diagnostics.

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
  snapshots; service tests pin active admin pagination and persisted-only
  store pagination.
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
  ids, auth headers, tokens, or file names.
- Prefer precomputed or cached job summary fields for list rows while keeping full metadata available on detail/media routes.
- Avoid avoidable library repository reads in shared search paths. Status:
  `/api/pipelines/search` now defers the library item lookup until the pipeline
  job is missing, so normal active-job media searches avoid a library sync
  lookup while preserving library fallback behavior for archived items and
  unknown-job 404s.
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
  server path to `/api/pipelines`.
- Route success to the new job in Jobs and start auto-refresh.

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
  Web Create now applies backend topic, title, and genre defaults from
  `/api/books/options` while preserving prompt edits that happen before defaults
  arrive.
- Keep Zustand selectors granular to avoid wide re-renders.
- Use visual redesign work only after the core component ownership is smaller.

### Milestone 4: Expand Native Creation

After Narrate Ebook:

- Subtitle job creation on iPad/iPhone. Status: Apple Create submits existing
  server-side subtitle paths or local SRT/VTT/ASS uploads with languages,
  output format, timing, output toggles, provider/model selection, ASS
  typography, transliteration mode/model, LLM batch-size tuning, and
  worker/render batch-size tuning, and mirror-to-source control through
  `/api/subtitles/jobs`; native time fields validate and normalize Web-style
  `MM:SS`, `HH:MM:SS`, and `+offset` values before submit. Remaining parity
  gap: rich TV/film metadata lookup/editing.
- Generated book job creation on iPad.
- YouTube dubbing as iPad-first review/submit flow. Status: Apple Create now
  exposes a path-based iPhone/iPad YouTube Dub mode for existing backend/NAS
  video and subtitle files and submits `/api/subtitles/youtube/dub` with
  language, voice, clip-window, batching, provider/model, output, and
  lookup-cache options. Remaining parity gaps: NAS library picker, inline
  subtitle extraction, voice preview, and rich TV/YouTube metadata lookup/editing.
- Library source reupload on iPhone/iPad. Status: Library row context menus now
  expose Replace Source File, open a document picker for EPUB/PDF sources, post
  the file to `/api/library/items/{job_id}/upload-source`, and replace the
  refreshed row returned by the backend. Apple TV remains playback-first.
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
- Creation handoff: Apple app opens the corresponding Web creation URL for unsupported advanced options.
- Job health timeline: show backend stage durations and slow phases in Web and iPad.
- Backend queue pressure indicator: expose accepting/backpressure state in Settings before users submit long jobs.
- Smart resume cards: show "continue listening", "newly completed", and "needs attention" across all surfaces.
- Shared media diagnostics: surface missing timing/audio/image assets without
  opening logs. Status: media manifest responses now include a token-safe
  aggregate diagnostics object with media, chunk, audio, image, timing,
  metadata, URL, and size counts; Web Job Detail now shows a compact manifest
  health strip when diagnostics are available, and Apple playback now decodes
  and shows the same aggregate counts in a compact native strip.
- Offline export from Apple: request `/api/exports` for a completed job/library item and show status in Jobs.

## Verification Contract

Every cross-surface change should pass the relevant subset:

- Backend: targeted `pytest` for touched routers/services.
- Web: `pnpm --dir web test` or focused Vitest files, plus `pnpm --dir web build` for UI changes.
- Apple: release contract, iOS/tvOS simulator builds, and shared pipeline simulator smokes.
- Pipeline: `check_app_source_sync.py`, `check_app_backend.py`, and deploy-delta tests when version/deploy ledger changes.

Physical device deployment remains attended and explicit only.
