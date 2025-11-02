# Repository Agent Notes

## Purpose
This repository powers the ebook-tools platform, bundling a FastAPI backend, background job helpers, and a Vite/React frontend for rendering and managing multimedia ebook assets.

## Key Entry Points
- **Backend:** `modules/webapi/application.py` exposes the FastAPI app factory referenced by `python -m modules.webapi` and the `ebook-tools-api` console script.
- **CLI / Orchestration:** `ebook-tools.py` and `scripts/` house helper commands for running pipelines locally.
- **Frontend:** `web/` contains the Vite application. Source files live under `web/src/`, while built assets default to `web/dist/`.
- **Frontend Book Flows:** `web/src/pages/NewImmersiveBookPage.tsx` unifies the submission and settings experience behind the sidebar entry “Add book,” sharing language state with `web/src/pages/CreateBookPage.tsx` and `web/src/components/PipelineSubmissionForm.tsx` via `web/src/context/LanguageProvider.tsx`.
- **Search:** `modules/webapi/routes.py` exposes `/api/pipelines/search`, which now requires a `job_id` query parameter, scans that job's persisted chunks for snippets surfaced in the frontend `MediaSearchPanel`, and falls back to library metadata when the pipeline job has already been archived.
- **Audio Voices:** `modules/webapi/routers/audio.py` serves `/api/audio/voices` for language-specific voice inventories and `/api/audio` for preview synthesis consumed by the `PipelineSubmissionForm` voice picker.
- **Library:** `modules/library/` now splits the domain into `library_models`, `library_repository`, `library_metadata`, `library_sync`, and the lightweight `library_service` facade consumed by `modules/webapi/routers/library.py`; the frontend experience lives in `web/src/pages/LibraryPage.tsx` and related components.
- **Subtitles:** `modules/subtitles/processing.py` handles colourised subtitle rendering, supporting per-word SRT highlighting, optional ASS exports, configurable start/end time windows (including relative offsets), and the new `original_language`/`show_original` options exposed on `SubtitlesPage.tsx` via `modules/webapi/routers/subtitles.py`.

## Common Workflows
- Create a virtual environment and install dependencies with `pip install -e .[dev]`.
- Start the API for local development with `uvicorn modules.webapi.application:create_app --factory --reload`.
- Run the test suite via `pytest` from the repository root.
- Library storage defaults to `/Volumes/Data/Video/Library`; override via `library_root` in `config/config.local.json` or the `LIBRARY_ROOT` environment variable when running services locally.

## Style Reminders
- Prefer explicit imports and keep module-level side effects minimal.
- Align with the FastAPI conventions already present: Pydantic models in `modules/webapi/schemas/`, services under `modules/services/`, and routers under `modules/webapi/`.
- Frontend components follow a co-located CSS Modules pattern (`Component.tsx` with `Component.module.css`).

## Updating These Notes
Whenever a task introduces new subsystems, moves files, or changes the recommended commands, add or adjust the relevant sections above so future agents land with accurate context.
