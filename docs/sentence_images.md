# Sentence Images (Draw Things / Stable Diffusion)

This document describes how ebook-tools generates and serves per-sentence images for the Interactive Reader.

## Overview

When `add_images` is enabled for a job, the backend generates **one image per sentence** in parallel with translation. Images are stored as job media and referenced from chunk metadata so the web player can show them while a job is still running.

## Configuration

Sentence images are controlled by pipeline config values (and can be overridden per job via `pipeline_overrides`):

- `add_images`: Enables sentence images for the job.
- `image_api_base_url`: Base URL of the Draw Things instance (example: `http://192.168.1.9:7860`).
- `image_api_timeout_seconds`: Request timeout for `txt2img` (default: 180 seconds).
- `image_concurrency`: Number of parallel image workers (default: 4).
- `image_width`, `image_height`: Output resolution (defaults: 512×512).
- `image_steps`: Sampling steps (default: 24).
- `image_cfg_scale`: Guidance scale (default: 7).
- `image_sampler_name`: Optional sampler identifier accepted by the backend.
- `image_prompt_context_sentences`: How many previous sentences are provided to the LLM to keep scene continuity (default: 2, max: 10).

Environment variables:

- `EBOOK_IMAGE_API_BASE_URL`
- `EBOOK_IMAGE_API_TIMEOUT_SECONDS`
- `EBOOK_IMAGE_CONCURRENCY`

## Storage layout & metadata wiring

Generated images are written under the job’s media folder:

- `storage/jobs/<job_id>/media/images/<range_fragment>/sentence_00001.png`

Chunk metadata files (`storage/jobs/<job_id>/metadata/chunk_XXXX.json`) record the image so clients can resolve it via the storage routes:

- `sentences[].image`: `{ "path": "<relative path>", "prompt": "...", "negative_prompt": "..." }`
- `sentences[].image_path` and `sentences[].imagePath`: convenience string fields mirroring `image.path`

The job media snapshot endpoints (`/api/pipelines/jobs/{job_id}/media` and `/api/pipelines/jobs/{job_id}/media/live`) expose these fields so the web client can update its image reel during running jobs.

## Prompting flow (LLM → Diffusion prompt)

Image prompts are built in two phases:

1. **Scene description (LLM):** `modules/images/prompting.py:sentence_to_diffusion_prompt` converts the current sentence (plus optional context sentences) into a short, concrete scene description. The output must be **scene only** (no style keywords).
2. **Style suffix:** `build_sentence_image_prompt(...)` appends a shared base prompt intended to render a simple “glyph/clipart essence” depiction. `build_sentence_image_negative_prompt(...)` always adds a negative prompt to suppress haze, clutter, and accidental text.

For reproducibility, the pipeline derives a stable seed from the sentence text (`stable_diffusion_seed(...)`, MD5-based).

## API endpoints (inspect + regenerate)

The media routes expose sentence-image inspection and regeneration endpoints (available both under `/api/pipelines/...` and the legacy `/jobs/...` prefix):

- `GET /api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}`
  - Returns stored prompt metadata and the computed image path (if the chunk range fragment is known).
- `POST /api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}/regenerate`
  - Regenerates the image and overwrites the stored PNG.
  - Supports reusing the stored prompt, supplying a new prompt, or asking the LLM to rebuild a prompt (`use_llm_prompt`).
  - Supports optional overrides for `context_sentences`, `negative_prompt`, `width`, `height`, `steps`, `cfg_scale`, `sampler_name`, and `seed`.

Schemas live in `modules/webapi/schemas/images.py`.

## Frontend integration

- **Interactive Reader reel:** `web/src/components/InteractiveTextViewer.tsx` renders a “movie reel” strip above the text tracks showing 7 images (3 previous, active, 3 next). Toggle visibility with `R`. Fullscreen uses `F` (the reel scales up in fullscreen).
- **MyPainter:** the web UI can load a sentence’s stored prompt/settings, regenerate the image via the API, and overwrite the original media asset.

## Debugging checklist

1. Confirm `image_api_base_url` is set and reachable from the API host.
2. Verify the backend can call the Draw Things `txt2img` endpoint (`/sdapi/v1/txt2img`) and receives JSON with a base64-encoded image (`images[0]`).
3. Inspect `storage/jobs/<job_id>/media/images/` to confirm PNGs are being written.
4. Inspect `storage/jobs/<job_id>/metadata/chunk_XXXX.json` to confirm `sentences[].image` is present and paths are job-relative.
5. Use the `GET .../media/images/sentences/{sentence_number}` endpoint to confirm the stored prompt and expected path match what the UI is loading.

