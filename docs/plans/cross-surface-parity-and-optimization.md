# Cross-Surface Parity And Optimization Plan

Last updated: 2026-06-22

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

- `web/src/pages/LibraryPage.tsx` - 1361 lines.
- `web/src/pages/VideoDubbingPage.tsx` - 1330 lines.
- `web/src/components/video-subtitles/SubtitleTrackOverlay.tsx` - 1276 lines.
- `web/src/components/JobProgress.tsx` - 1254 lines.
- `web/src/components/LibraryList.tsx` - 1148 lines.
- `web/src/components/PlayerPanel.tsx` - 1085 lines.
- `web/src/components/Sidebar.tsx` - 963 lines.
- `web/src/components/book-narration/BookNarrationForm.tsx` - 956 lines.

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

Current Apple UI does not yet expose:

- Narrate Ebook document import/upload submission.
- Subtitle job submission.
- YouTube dubbing submission.
- Upload/reupload library source files.

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
- Add lightweight timing/log counters around job list, library list, media manifest, and search endpoints.
- Prefer precomputed or cached job summary fields for list rows while keeping full metadata available on detail/media routes.
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
now also expose a Narrate EPUB mode for server-side EPUB paths. Document
import/upload remains the next native creation step because it maps best to the
current Apple browse/playback model once file picking is ready.

Target Apple UX:

- Add a `New Job` entry to the iPad/iPhone browse shell.
- Use SwiftUI `Form`/`NavigationStack` with sections for source, languages, audio, output, and advanced settings.
- Support simple existing-file submission first. Status: iPhone/iPad support
  server-side EPUB path submission through the Apple Create form.
- Add EPUB file import/upload next using document picker on iPad/iPhone.
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
- Keep Zustand selectors granular to avoid wide re-renders.
- Use visual redesign work only after the core component ownership is smaller.

### Milestone 4: Expand Native Creation

After Narrate Ebook:

- Subtitle job creation on iPad/iPhone.
- Generated book job creation on iPad.
- YouTube dubbing as iPad-first review/submit flow.
- Apple TV gets read-only job templates or retry controls only if remote navigation stays simple.

## Feature Backlog

Suggested features to evaluate after parity scaffolding:

- Cross-surface job templates: save a Web configuration and reuse it from Apple.
- Draft jobs: start on iPad, finish advanced settings on Web.
- Creation handoff: Apple app opens the corresponding Web creation URL for unsupported advanced options.
- Job health timeline: show backend stage durations and slow phases in Web and iPad.
- Backend queue pressure indicator: expose accepting/backpressure state in Settings before users submit long jobs.
- Smart resume cards: show "continue listening", "newly completed", and "needs attention" across all surfaces.
- Shared media diagnostics: surface missing timing/audio/image assets without opening logs.
- Offline export from Apple: request `/api/exports` for a completed job/library item and show status in Jobs.

## Verification Contract

Every cross-surface change should pass the relevant subset:

- Backend: targeted `pytest` for touched routers/services.
- Web: `pnpm --dir web test` or focused Vitest files, plus `pnpm --dir web build` for UI changes.
- Apple: release contract, iOS/tvOS simulator builds, and shared pipeline simulator smokes.
- Pipeline: `check_app_source_sync.py`, `check_app_backend.py`, and deploy-delta tests when version/deploy ledger changes.

Physical device deployment remains attended and explicit only.
