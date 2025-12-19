# Sentence Images (Draw Things / Stable Diffusion)

This document describes how ebook-tools generates and serves sentence-timed images for the Interactive Reader.

## Overview

When `add_images` is enabled for a job, the backend generates images in parallel with translation and stores them as job media referenced from chunk metadata so the web player can show them while a job is still running.

By default, prompts are generated in **sentence batches** (10 sentences per image), so a 100-sentence job typically produces ~10 images. Batch images persist while the player speaks the whole batch, then switch to the next batch image.

## Configuration

Sentence images are controlled by pipeline config values (and can be overridden per job via `pipeline_overrides`):

- `add_images`: Enables sentence images for the job.
- `image_api_base_url`: Base URL of the Draw Things instance (example: `http://192.168.1.9:7860`).
- `image_api_timeout_seconds`: Request timeout for `txt2img` (default: 600 seconds).
- `image_concurrency`: Number of parallel image workers (default: 4).
- `image_width`, `image_height`: Output resolution (defaults: 512×512).
- `image_prompt_batching_enabled`: Enables prompt/image batching (default: `true`).
- `image_prompt_batch_size`: Number of sentences per batch (default: `10`, max: `50`).
- `image_style_template`: Visual template used when appending the shared style suffix to scene prompts.
  - Supported: `photorealistic` (default), `comics`, `children_book`, `wireframe`.
  - The selected template also supplies default `image_steps` / `image_cfg_scale` values when not explicitly overridden.
- `image_steps`: Sampling steps (default: 24).
- `image_cfg_scale`: Guidance scale (default: 7).
- `image_sampler_name`: Optional sampler identifier accepted by the backend.
- `image_prompt_context_sentences`: Adds up to this many sentences before **and** after the selected start/end window when asking the LLM for a consistent prompt plan (default: 2, max: 50).
- `image_seed_with_previous_image`: When enabled, the pipeline uses `img2img` with the previous frame (or a baseline seed image) as an init image to keep the reel visually consistent (default: off).

Environment variables:

- `EBOOK_IMAGE_API_BASE_URL`
- `EBOOK_IMAGE_API_TIMEOUT_SECONDS`
- `EBOOK_IMAGE_CONCURRENCY`

## Storage layout & metadata wiring

Generated images are written under the job’s media folder:

- **Batched (default):** `storage/<job_id>/media/images/batches/batch_00001.png` (the filename is the batch start sentence number)
- **Per-sentence (legacy / when batching disabled):** `storage/<job_id>/media/images/<range_fragment>/sentence_00001.png`

Chunk metadata files (`storage/<job_id>/metadata/chunk_XXXX.json`) record the image so clients can resolve it via the storage routes:

- `sentences[].image`: `{ "path": "<relative path>", "prompt": "...", "negative_prompt": "..." }`
- `sentences[].image_path` and `sentences[].imagePath`: convenience string fields mirroring `image.path`

When batching is enabled, multiple consecutive sentences share the same `image.path` and include batch metadata (`batch_start_sentence`, `batch_end_sentence`, `batch_size`) to help clients render batch-aware UI.

For transparency, jobs that precompute a prompt plan also write:

- `storage/<job_id>/metadata/image_prompt_plan.json` (one entry per prompt target: sentence when batching is off, batch when batching is on; includes `prompt_batching_enabled` / `prompt_batch_size`)
- `storage/<job_id>/metadata/image_prompt_plan_summary.json` (compact coverage/retry stats surfaced in the job details UI)

The job media snapshot endpoints (`/api/pipelines/jobs/{job_id}/media` and `/api/pipelines/jobs/{job_id}/media/live`) expose these fields so the web client can update its image reel during running jobs.

## Prompting flow (LLM → Diffusion prompt)

Image prompts are built in two phases:

1. **Prompt plan (LLM):** `modules/images/prompting.py:sentences_to_diffusion_prompt_plan` generates a *consistent* set of scene descriptions for the selected job sentence window. When batching is enabled, the pipeline uses `sentence_batches_to_diffusion_prompt_plan` so each batch gets a single scene prompt that represents the batch narrative. Each entry is **scene only** (no style keywords).
2. **Style suffix:** `build_sentence_image_prompt(..., style_template=...)` appends the shared style prompt for the selected `image_style_template`. `build_sentence_image_negative_prompt(..., style_template=...)` always adds a negative prompt to suppress blur, artifacts, and accidental text.

For reproducibility, the pipeline derives a stable seed from the sentence text (`stable_diffusion_seed(...)`, MD5-based).

### Storyline consistency (baseline seed + chained frames)

To keep the reel visually consistent across frames:

- The LLM prompt-plan response includes a `baseline` anchor frame (scene prompt + layout notes). The pipeline renders a baseline seed image at:
  - `storage/<job_id>/media/images/_seed/baseline_seed_<start>_<end>.png`
- When supported by the backend (`/sdapi/v1/img2img`), images can reuse the **previous frame’s** generated image as an `img2img` init image **only when the previous prompt came from the LLM** (`source` is `llm` or `llm_retry`). With batching enabled, “previous frame” refers to the previous batch image.
- If no previous LLM-seeded image is available, the baseline seed image is used instead. If `img2img` is unavailable, the pipeline falls back to `txt2img`.

This behavior is only enabled when `image_seed_with_previous_image=true` (default is off).

## API endpoints (inspect + regenerate)

The media routes expose sentence-image inspection and regeneration endpoints (available both under `/api/pipelines/...` and the legacy `/jobs/...` prefix):

- `GET /api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}`
  - Returns stored prompt metadata and the computed image path (if the chunk range fragment is known).
- `POST /api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}/regenerate`
  - Regenerates the image and overwrites the stored PNG.
  - Supports reusing the stored prompt, supplying a new prompt, or asking the LLM to rebuild a prompt (`use_llm_prompt`).
  - Ensures the stored/LLM prompt includes the style suffix for the job's `image_style_template`.
  - Supports optional overrides for `context_sentences`, `negative_prompt`, `width`, `height`, `steps`, `cfg_scale`, `sampler_name`, and `seed`.
  - When batching is enabled, regenerating any sentence updates the shared batch image and refreshes prompt metadata for all sentences that reference it.

Schemas live in `modules/webapi/schemas/images.py`.

## Frontend integration

- **Interactive Reader reel:** `web/src/components/InteractiveTextViewer.tsx` renders a trailing “movie reel” strip above the text tracks showing up to 5 images (active + up to 4 previous). Future images are hidden until their batch is active, and the active frame is right-aligned + visually emphasized. When batching is enabled, the reel advances per batch rather than per sentence. The reel prefetches a couple of upcoming/previous frames but only renders the trailing window. Toggle visibility with `R`. Fullscreen uses `F` (the reel scales up in fullscreen).
- **MyPainter:** the web UI can load a sentence’s stored prompt/settings, regenerate the image via the API, and overwrite the original media asset.

## Debugging checklist

1. Confirm `image_api_base_url` is set and reachable from the API host.
2. Verify the backend can call the Draw Things `txt2img` endpoint (`/sdapi/v1/txt2img`) and receives JSON with a base64-encoded image (`images[0]`).
3. Inspect `storage/<job_id>/media/images/` to confirm PNGs are being written.
4. Inspect `storage/<job_id>/metadata/chunk_XXXX.json` to confirm `sentences[].image` is present and paths are job-relative.
5. Use the `GET .../media/images/sentences/{sentence_number}` endpoint to confirm the stored prompt and expected path match what the UI is loading.
