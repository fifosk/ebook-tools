# Sentence Images (Draw Things / Stable Diffusion)

This document describes how ebook-tools generates and serves sentence-timed images for the Interactive Reader.

## Overview

When `add_images` is enabled for a job, the backend generates images in parallel with translation and stores them as job media referenced from chunk metadata so the web player can show them while a job is still running.

Image prompting supports two pipelines:

- **prompt_plan (default):** prompts are generated in **sentence batches** (10 sentences per image), so a 100-sentence job typically produces ~10 images. Batch images persist while the player speaks the whole batch, then switch to the next batch image.
- **visual_canon:** a 4-stage visual-canon pipeline (book-level canon → chapter scenes → sentence deltas → prompt assembly) that renders **one image per sentence** and uses `img2img` mid-scene to keep continuity.

## Configuration

Sentence images are controlled by pipeline config values (and can be overridden per job via `pipeline_overrides`):

- `add_images`: Enables sentence images for the job.
- `image_api_base_url`: Base URL of the Draw Things instance (example: `http://192.168.1.9:7860`).
- `image_api_base_urls`: Optional list of Draw Things base URLs for clustered rendering.
  - When set, requests fan out to each node at startup (one in-flight per node), then the next request goes to whichever node is free, so faster nodes naturally take more work.
  - Set `image_concurrency` to at least the number of nodes if you want the first batch of images to fan out across the cluster immediately.
- `image_api_timeout_seconds`: Request timeout for `txt2img` (default: 600 seconds).
- `image_concurrency`: Number of parallel image workers (default: 4).
- `image_width`, `image_height`: Output resolution (defaults: 512×512).
- `image_prompt_batching_enabled`: Enables prompt/image batching (default: `true`; forced off for `visual_canon`).
- `image_prompt_batch_size`: Number of sentences per image (default: `10`, max: `50`; forced to `1` for `visual_canon`).
- `image_prompt_plan_batch_size`: LLM prompt-plan chunk size (default: `50`, max: `50`).
- `image_style_template`: Visual template used when appending the shared style suffix to scene prompts.
  - Supported: `photorealistic` (default), `comics`, `children_book`, `wireframe`.
  - The selected template also supplies default `image_steps` / `image_cfg_scale` values when not explicitly overridden.
- `image_steps`: Sampling steps (default: 24).
- `image_cfg_scale`: Guidance scale (default: 7).
- `image_sampler_name`: Optional sampler identifier accepted by the backend.
- `image_prompt_pipeline`: Prompting strategy for sentence images.
  - `prompt_plan` (default): legacy batched LLM prompt plan + style suffix.
  - `visual_canon`: 4-stage visual canon pipeline (forces per-sentence images and ignores `image_style_template`).
- `image_prompt_context_sentences`: Adds up to this many sentences before **and** after the selected start/end window when asking the LLM for a consistent prompt plan (default: 2, max: 50; used only by `prompt_plan`).
- `image_seed_with_previous_image`: When enabled, the pipeline uses `img2img` with the previous frame (or a baseline seed image) as an init image to keep the reel visually consistent (default: off).

Environment variables:

- `EBOOK_IMAGE_API_BASE_URL`
- `EBOOK_IMAGE_API_BASE_URLS` (comma-separated list for clustered rendering)
- `EBOOK_IMAGE_API_TIMEOUT_SECONDS`
- `EBOOK_IMAGE_CONCURRENCY`
- `EBOOK_IMAGE_PROMPT_PIPELINE`

## Storage layout & metadata wiring

Generated images are written under the job’s media folder:

- **Batched (default):** `storage/<job_id>/media/images/batches/batch_00001.png` (the filename is the batch start sentence number)
- **Per-sentence (legacy / when batching disabled):** `storage/<job_id>/media/images/<range_fragment>/sentence_00001.png`

Chunk metadata files (`storage/<job_id>/metadata/chunk_XXXX.json`) record the image so clients can resolve it via the storage routes:

- `sentences[].image`: `{ "path": "<relative path>", "prompt": "...", "negative_prompt": "..." }` (visual-canon jobs also include `scene_id`, `sentence_delta`, `generation_mode`, `init_image`, `denoise_strength`, `reuse_previous_image`)
- `sentences[].image_path` and `sentences[].imagePath`: convenience string fields mirroring `image.path`

When batching is enabled, multiple consecutive sentences share the same `image.path` and include batch metadata (`batch_start_sentence`, `batch_end_sentence`, `batch_size`) to help clients render batch-aware UI.

For transparency, jobs that precompute a prompt plan also write:

- `storage/<job_id>/metadata/image_prompt_plan.json` (one entry per prompt target: sentence when batching is off, batch when batching is on; includes `prompt_batching_enabled` / `prompt_batch_size`)
- `storage/<job_id>/metadata/image_prompt_plan_summary.json` (compact coverage/retry stats surfaced in the job details UI)

When `image_prompt_pipeline=visual_canon`, additional metadata is persisted:

- `storage/<job_id>/metadata/visual_canon.json` (immutable style + characters + locations)
- `storage/<job_id>/metadata/scenes/<scene_id>.json` (scene state + `base_image_path` once the first image is rendered)

The job media snapshot endpoints (`/api/pipelines/jobs/{job_id}/media` and `/api/pipelines/jobs/{job_id}/media/live`) expose these fields so the web client can update its image reel during running jobs.

When clustered rendering is enabled, `generated_files.image_cluster` includes per-node stats (active flag, processed count, and average seconds per image) so the job detail view can report node throughput.

## Prompting flow (LLM → Diffusion prompt)

Two prompting strategies are available:

### `prompt_plan` (legacy, default)

1. **Prompt plan (LLM):** `modules/images/prompting.py:sentences_to_diffusion_prompt_plan` generates a *consistent* set of scene descriptions for the selected job sentence window. When batching is enabled, the pipeline uses `sentence_batches_to_diffusion_prompt_plan` so each batch gets a single scene prompt that represents the batch narrative. Each entry is **scene only** (no style keywords). Prompt-plan requests are chunked in blocks of up to `image_prompt_plan_batch_size` targets (capped at 50); image generation starts as each chunk completes, so the first prompts can begin rendering before the full plan finishes.
2. **Style suffix:** `build_sentence_image_prompt(..., style_template=...)` appends the shared style prompt for the selected `image_style_template`. `build_sentence_image_negative_prompt(..., style_template=...)` always adds a negative prompt to suppress blur, artifacts, and accidental text.

For reproducibility, the pipeline derives a stable seed from the sentence text (`stable_diffusion_seed(...)`, MD5-based).

**Storyline consistency (baseline seed + chained frames)**

- The LLM prompt-plan response includes a `baseline` anchor frame (scene prompt + layout notes). The pipeline renders a baseline seed image at:
  - `storage/<job_id>/media/images/_seed/baseline_seed_<start>_<end>.png`
- When supported by the backend (`/sdapi/v1/img2img`), images can reuse the **previous frame’s** generated image as an `img2img` init image **only when the previous prompt came from the LLM** (`source` is `llm` or `llm_retry`). With batching enabled, “previous frame” refers to the previous batch image.
- If no previous LLM-seeded image is available, the baseline seed image is used instead. If `img2img` is unavailable, the pipeline falls back to `txt2img`.

This behavior is only enabled when `image_seed_with_previous_image=true` (default is off).

### `visual_canon` (4-stage visual canon pipeline)

1. **Book-level visual canon (LLM):** builds `metadata/visual_canon.json` (style + recurring characters + recurring locations). This file is immutable after creation.
2. **Chapter scenes (LLM):** detects visually coherent scenes per chapter and stores each scene under `metadata/scenes/<scene_id>.json` with an empty `base_image_path`. Scene detection is scoped to the selected sentence range, so image generation can begin once the current chapter's scene metadata is ready. Scene detection is constrained to visual-canon character/location IDs; unknown IDs are mapped when possible and otherwise omitted.
3. **Sentence deltas (LLM):** for each sentence, extracts *only* the immediate action/pose/expression change. Deltas containing forbidden traits are sanitized; if still invalid, the pipeline falls back to a neutral pose change.
4. **Prompt assembly (no LLM):** assembles the final prompt in a fixed order:
   `visual_canon.style` + `visual_canon.locations[scene.location_id]` + character tokens + `time_of_day/weather/mood` + sentence delta.

The negative prompt is fixed (`GLOBAL_NEGATIVE_CANON`), and images are rendered per-sentence. The first sentence in a scene uses `txt2img`; all following sentences in the same scene use `img2img` with `denoising_strength=0.3` and the previous sentence’s image as the init image. This pipeline assumes your Draw Things instance is configured with the **FLUX 1.x schnell** model.

## API endpoints (inspect + regenerate)

The media routes expose sentence-image inspection and regeneration endpoints (available both under `/api/pipelines/...` and the legacy `/jobs/...` prefix):

- `GET /api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}`
  - Returns stored prompt metadata and the computed image path (if the chunk range fragment is known).
- `POST /api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}/regenerate`
  - Regenerates the image and overwrites the stored PNG.
  - Supports reusing the stored prompt, supplying a new prompt, or asking the LLM to rebuild a prompt (`use_llm_prompt`).
  - For `prompt_plan`, ensures the stored/LLM prompt includes the style suffix for the job's `image_style_template`.
  - For `visual_canon`, rebuilds the sentence delta + assembled prompt when `use_llm_prompt` is requested.
  - Supports optional overrides for `context_sentences`, `negative_prompt`, `width`, `height`, `steps`, `cfg_scale`, `sampler_name`, and `seed`.
  - When batching is enabled, regenerating any sentence updates the shared batch image and refreshes prompt metadata for all sentences that reference it.

Schemas live in `modules/webapi/schemas/images.py`.

## Frontend integration

- **Interactive Reader reel:** `web/src/components/InteractiveTextViewer.tsx` renders a trailing “movie reel” strip above the text tracks showing up to 7 images (3 previous, active, 3 next). Future images are hidden until their batch is active, and the active frame is right-aligned + visually emphasized. When batching is enabled, the reel advances per batch rather than per sentence. The reel prefetches a couple of upcoming/previous frames but only renders the current window. Toggle visibility with `R`. Fullscreen uses `F` (the reel scales up in fullscreen).
- **MyPainter:** the web UI can load a sentence’s stored prompt/settings, regenerate the image via the API, and overwrite the original media asset.

## Debugging checklist

1. Confirm `image_api_base_url` or `image_api_base_urls` is set and reachable from the API host.
2. Verify the backend can call the Draw Things `txt2img` endpoint (`/sdapi/v1/txt2img`) and receives JSON with a base64-encoded image (`images[0]`).
3. Inspect `storage/<job_id>/media/images/` to confirm PNGs are being written.
4. Inspect `storage/<job_id>/metadata/chunk_XXXX.json` to confirm `sentences[].image` is present and paths are job-relative.
5. Use the `GET .../media/images/sentences/{sentence_number}` endpoint to confirm the stored prompt and expected path match what the UI is loading.
