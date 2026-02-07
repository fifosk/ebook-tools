# Test Suite Improvement Plan

## Current State

- **800 tests** (661 in `tests/`, 139 in `modules/`) — all green
- **88 test files** across 4 directory depths
- **1 pytest marker** defined (`integration`) — barely used (3 tests)
- **1 conftest.py** (root only) — minimal fixture sharing
- **No fine-grained selection** — `pytest` runs everything or nothing

---

## Part 1: Dead Code & Import Cleanup

Small hygiene pass — removes noise, makes linter-clean baseline.

### 1.1 Remove unused `import pytest` (6 files)

These files import `pytest` but never reference it (no decorators, no `pytest.raises`, etc.):

- `tests/modules/test_token_alignment.py`
- `tests/modules/test_translation_integration.py`
- `tests/modules/test_translation_batch.py`
- `tests/modules/core/test_storage_config.py`
- `tests/modules/core/test_pipeline_config_defaults.py`
- `tests/test_library_metadata_manager.py`

### 1.2 Remove unused `import os` in conftest.py

`tests/conftest.py:1` — `os` is imported but never used.

### 1.3 Remove other unused imports (~15 files)

Notable candidates:
- `tests/integration/test_cjk_tokenization.py` — unused `os`, `Tuple`
- `tests/modules/audio/test_piper_backend.py` — unused `io`, `wave`, `Path`, `Any`, `patch`
- `tests/modules/core/test_multi_sentence_chunks.py` — unused `math`, `Sequence`
- `tests/modules/core/test_pipeline_config_defaults.py` — unused `PipelineState`, `RenderPipeline`
- `tests/modules/services/test_job_manager_access_control.py` — unused `dataclass_replace`
- `tests/modules/config_manager/test_storage_settings.py` — unused `loader as cfg_loader`
- `tests/modules/webapi/test_storage_file_download.py` — unused `config_manager as cfg`
- `tests/render/test_output_writer.py` — unused `config_manager as cfg`
- `tests/test_create_book.py` — unused `config_manager as cfg`
- `tests/test_epub_job.py` — unused `config_manager`, `dependencies`
- `tests/test_main.py` — unused `logging_manager as log_mgr`

---

## Part 2: Pytest Marker System

Add domain-based markers so `pytest -m audio` runs only audio tests, etc. This is the biggest win for development-time test selection.

### 2.1 Define markers in `pyproject.toml`

```toml
[tool.pytest.ini_options]
markers = [
    "integration: end-to-end workflows requiring external services.",
    "audio: TTS backends, voice selection, audio highlighting.",
    "translation: translation engine, batch processing, CJK tokenization.",
    "metadata: metadata enrichment, structured conversion, library metadata.",
    "webapi: FastAPI routes, middleware, CORS, auth endpoints.",
    "pipeline: core rendering pipeline, multi-sentence chunks, timeline.",
    "services: job manager, pipeline service, file locator, assistant.",
    "cli: command-line interface, args parsing, user commands.",
    "auth: user management, session, auth service.",
    "library: library sync, indexer, repository.",
    "render: output writer, text pipeline, parallel dispatch.",
    "media: command runner, media backends.",
    "config: config manager, storage settings, runtime context.",
    "ramdisk: RAMDisk lifecycle, guard, mount/unmount.",
    "slow: tests that take >2s (WhisperX, Piper, pipelines).",
]
```

### 2.2 Apply markers to test files

Use `pytestmark = pytest.mark.<domain>` at module level (one line per file, no per-function decoration needed). Mapping:

| Marker | Test files |
|--------|-----------|
| `audio` | `test_piper_backend`, `test_tts_backends`, `test_tts_voice_selection`, `test_audio_highlight` |
| `translation` | `test_translation_batch`, `test_translation_integration`, `test_translation_engine_quality`, `test_token_alignment`, `test_googletrans_provider`, `test_translation_validation`, `test_translation_logging`, `test_translation_workers` |
| `metadata` | `test_metadata_enrichment`, `test_metadata_integration`, `test_structured_conversion` |
| `webapi` | All 13 files in `tests/modules/webapi/` |
| `pipeline` | `test_multi_sentence_chunks`, `test_exporter_audio_tracks`, `test_timeline_builder`, `test_rendering_exporters`, `test_pipeline_voice_logging` |
| `services` | `test_assistant`, `test_config_phase`, `test_file_locator`, `test_job_manager_*` (7 files), `test_request_factory`, `test_youtube_dubbing_*` |
| `cli` | `test_args`, `test_assets`, `test_context`, `test_pipeline_runner`, `test_user_commands` |
| `auth` | `test_auth_service`, `test_local_user_store`, `test_session_manager` |
| `library` | `test_library_service`, `test_indexer`, `test_library_sync`, `test_metadata` (library), `test_repository`, `test_subtitle_library`, `test_library_metadata_manager`, `test_library_source_and_isbn_metadata` |
| `render` | `test_output_writer`, `test_parallel`, `test_text_pipeline`, `test_polly*` |
| `media` | `test_command_runner` |
| `config` | `test_storage_config`, `test_pipeline_config_defaults`, `test_storage_settings`, `test_runtime_tmp_dir` |
| `ramdisk` | `test_runtime_tmp_dir` (can carry both `config` and `ramdisk`) |
| `integration` | `test_cjk_tokenization`, `test_piper_whisperx_pipeline`, `test_word_timing_validation`, `test_epub_job` |
| `slow` | `test_whisperx_alignment`, `test_piper_backend`, integration tests |

### 2.3 Usage examples

```bash
# Run only audio tests
pytest -m audio

# Run everything except slow/integration
pytest -m "not slow and not integration"

# Run translation + metadata (often change together)
pytest -m "translation or metadata"

# Run what matters after changing modules/webapi/
pytest -m webapi
```

---

## Part 3: Conftest Layering

Add domain-scoped `conftest.py` files so fixtures are discoverable and close to their tests.

### 3.1 Add `tests/modules/webapi/conftest.py`

Extract repeated `create_app` + `TestClient` + dependency override boilerplate shared across all 13 webapi test files.

### 3.2 Add `tests/modules/services/conftest.py`

Extract the `job_manager_factory` / `flat_book_metadata` fixtures used across 6+ service test files.

### 3.3 Add `tests/modules/audio/conftest.py`

Extract mock backend registration patterns shared across audio tests.

### 3.4 Keep root conftest minimal

Root conftest stays with: RAMDisk disable, CLI option parsing, session fixtures. Domain fixtures move to domain conftest files.

---

## Part 4: Test Consolidation

### 4.1 Merge module-level tests into `tests/`

Currently 139 tests live in `modules/tests/` and `modules/library/tests/`. This split is confusing — tests should live under `tests/` exclusively.

| Current location | Proposed location |
|--|--|
| `modules/tests/test_googletrans_provider.py` | `tests/modules/translation/test_googletrans_provider.py` |
| `modules/tests/test_translation_validation.py` | `tests/modules/translation/test_translation_validation.py` |
| `modules/tests/test_translation_logging.py` | `tests/modules/translation/test_translation_logging.py` |
| `modules/tests/test_translation_workers.py` | `tests/modules/translation/test_translation_workers.py` |
| `modules/library/tests/test_metadata.py` | `tests/modules/library/test_library_metadata.py` |
| `modules/library/tests/test_repository.py` | `tests/modules/library/test_library_repository.py` |
| `modules/library/tests/test_subtitle_library.py` | `tests/modules/library/test_subtitle_library.py` |

After moving, remove `"modules"` from `testpaths` in `pyproject.toml`.

### 4.2 Group translation tests under `tests/modules/translation/`

Translation tests are scattered:
- `tests/modules/test_translation_batch.py`
- `tests/modules/test_translation_integration.py`
- `tests/modules/test_translation_engine_quality.py`
- `tests/modules/test_token_alignment.py`
- `tests/integration/test_cjk_tokenization.py`

Move the unit tests into `tests/modules/translation/` for cohesion (CJK stays in `integration/`).

### 4.3 Move render tests under `tests/modules/render/`

Currently at `tests/render/` — move to `tests/modules/render/` for consistency.

---

## Part 5: Test Infrastructure

### 5.1 Add a `Makefile` / shell aliases for common test commands

```makefile
test:            pytest
test-fast:       pytest -m "not slow and not integration"
test-audio:      pytest -m audio
test-translation: pytest -m translation
test-webapi:     pytest -m webapi
test-services:   pytest -m services
test-pipeline:   pytest -m pipeline
test-changed:    pytest --co -q | ... (see 5.2)
```

### 5.2 Consider `pytest-incremental` or path-based selection

For development, a mapping from source module to test marker lets you run:
```bash
# After changing modules/audio/*, run:
pytest -m audio

# After changing modules/webapi/*, run:
pytest -m webapi
```

Document this mapping in a table so developers know which marker to use.

---

## Execution Order

| Phase | Items | Effort | Impact |
|-------|-------|--------|--------|
| **Part 1** | Dead code cleanup | ~20 min | Low (hygiene) |
| **Part 2** | Marker system | ~45 min | **High** (enables selective runs) |
| **Part 4** | Test consolidation + moves | ~30 min | Medium (single test root) |
| **Part 3** | Conftest layering | ~30 min | Medium (fixture discovery) |
| **Part 5** | Dev shortcuts | ~15 min | Medium (convenience) |

**Recommended order**: Part 1 → Part 2 → Part 4 → Part 3 → Part 5

Part 2 (markers) delivers the biggest value: fine-grained `pytest -m <domain>` selection with minimal effort.
