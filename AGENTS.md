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
- **Metadata Storage:** `storage/<job_id>/metadata/` now persists a compact `job.json` manifest (with `chunk_manifest` summaries) plus per-chunk JSON files (`chunk_0000.json`, `chunk_0001.json`, …) for highlight timelines. Use `MetadataLoader` in `modules/metadata_manager.py` to read either the new chunked format or legacy single-file payloads.
- **Subtitles:** `modules/subtitles/processing.py` handles colourised subtitle rendering, supporting per-word SRT highlighting, optional ASS exports, configurable start/end time windows (including relative offsets), and the new `original_language`/`show_original` options exposed on `SubtitlesPage.tsx` via `modules/webapi/routers/subtitles.py`.
- **Alignment:** `modules/align/backends/whisperx_adapter.py` shells out to the WhisperX CLI when `forced_alignment_enabled` and `alignment_backend` are configured, allowing `modules/render/audio_pipeline.py` to pull real word tokens whenever the TTS backend omits them. The pipeline now auto-selects the WhisperX model per target language (honouring `alignment_model_overrides` when provided) and logs the choice so drift investigations stay transparent. Set `EBOOK_HIGHLIGHT_POLICY=forced` to fail jobs that would otherwise fall back to inferred timings.
- **Timing Policies:** Use `char_weighted_highlighting_default=true` (or `EBOOK_CHAR_WEIGHTED_HIGHLIGHTING_DEFAULT=1`) to prefer character-weighted timings and pair it with `char_weighted_punctuation_boost=true` (`EBOOK_CHAR_WEIGHTED_PUNCTUATION_BOOST=1`) when you want punctuation-aware pacing before the renderer falls back to uniform inference.

## Audio, Metadata & Highlighting Cheat Sheet
- **Audio generation.** `modules/render/audio_pipeline.py` streams translation tasks into the active backend from `modules/audio/backends/`. `AudioWorker` records whether the tokens came from the backend, WhisperX (`modules/align/backends/whisperx_adapter.py`), char-weighted inference, or uniform fallbacks and stores that policy in each sentence’s `highlighting_summary`. Sentence synthesis only inserts the fixed `SILENCE_DURATION_MS` spacer between contiguous segments (original → translation, etc.) and drops the trailing pad so highlighting now ends when speech does.
- **Metadata creation.** `modules/services/job_manager/persistence.py` writes `metadata/job.json`, `metadata/chunk_manifest.json`, and per-chunk files (`metadata/chunk_XXXX.json`). `MetadataLoader` in `modules/metadata_manager.py` can load both the chunked format and the legacy single-file payload, so always run metadata reads through it to stay forward-compatible.
- **Highlighting controls.** `EBOOK_HIGHLIGHT_POLICY` decides whether a job may fall back to inferred timings, while `char_weighted_highlighting_default`/`char_weighted_punctuation_boost` (or their env vars) tune character-weighted inference. Every chunk exposes this provenance through `highlighting_summary` and the frontend surfaces it via `/api/jobs/{job_id}/timing`.
- **Update expectation.** Whenever the audio stack, metadata layout, or highlighting logic changes, update these bullets plus the relevant docs (`README.md`, `docs/sentence_highlighting.md`, `docs/interactive_reader_metadata.md`) so downstream agents do not need to reverse-engineer the current behaviour.

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
