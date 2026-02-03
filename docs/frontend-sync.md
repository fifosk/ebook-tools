# Frontend Sync Checklist

Use the `frontend_sync.py` helper to compare the state of two local environments
when UI features appear on one machine but not another.

## 1. Capture snapshots

On each device, run:

```bash
python scripts/frontend_sync.py snapshot --output frontend-state.json
```

This writes a JSON snapshot with the git commit, environment variables from
`web/.env` and `web/.env.local`, the build manifest hash, and the API version
exposed by FastAPI.

## 2. Compare snapshots

Copy the snapshot files to a single machine and run:

```bash
python scripts/frontend_sync.py compare device-a.json device-b.json
```

The comparison reports:

- Git branch/commit alignment, tracked changes, and untracked files.
- Differences between `.env` files (highlighting API base URL mismatches).
- Whether the bundled Vite build manifests match.
- Backend API version discrepancies.
- Library metadata schema hash mismatches so the SQLite migrations remain in sync.

`dirty` in the JSON snapshot only flips to `true` when tracked files differ from
`HEAD`; untracked files are captured separately under `untracked_files` so you
can ignore generated artifacts without masking relevant source changes.

Follow the suggested remediations to restore parity:

1. Align git branches and commits between machines.
2. Fix any differing API URLs or missing env variables.
3. Rebuild the frontend (`npm install && npm run build`).
4. If the library schema hashes differ, run the latest migrations via `python scripts/db_migrate.py`.
5. Restart the FastAPI backend to reload `EBOOK_API_STATIC_ROOT`.
6. Clear `web/dist/` caches or browser caches if differences persist.

## 3. Audio/metadata/highlighting/images checklist

- Confirm both machines export the same audio/highlighting env vars:
  `EBOOK_AUDIO_BACKEND`, `EBOOK_AUDIO_EXECUTABLE`,
  `EBOOK_HIGHLIGHT_POLICY`, `EBOOK_CHAR_WEIGHTED_HIGHLIGHTING_DEFAULT`,
  `EBOOK_CHAR_WEIGHTED_PUNCTUATION_BOOST`, and `forced_alignment_enabled`.
- If sentence images are enabled for the job, confirm both machines export the
  same image-generation env vars: `EBOOK_IMAGE_API_BASE_URL`,
  `EBOOK_IMAGE_API_BASE_URLS`, `EBOOK_IMAGE_API_TIMEOUT_SECONDS`,
  `EBOOK_IMAGE_CONCURRENCY`, and `EBOOK_IMAGE_PROMPT_PIPELINE`.
- If prompts look inconsistent between environments, confirm both machines use
  the same `image_prompt_context_sentences` default/override when running the job.
- For image prompt consistency investigations:
  - `prompt_plan`: compare `storage/<job_id>/metadata/image_prompt_plan.json` (scene prompts + seeds).
  - `visual_canon`: compare `storage/<job_id>/metadata/visual_canon.json` and `metadata/scenes/*.json`.
- Inspect `storage/<job_id>/metadata/job.json` and `metadata/chunk_manifest.json`
  on each device; mismatched manifests or chunk counts indicate that audio
  regeneration or metadata compaction ran on only one machine.
- Spot-check a few chunk metadata files (`metadata/chunk_XXXX.json`) on each
  machine—especially their `timingTracks` entries—to ensure both environments
  are replaying the same highlight provenance. Legacy jobs may still include a
  `metadata/timing_index.json` if you prefer comparing single-file hashes.
- For image jobs, spot-check `metadata/chunk_XXXX.json` for `sentences[].image`
  / `image_path` fields and confirm the referenced files exist under
  `storage/<job_id>/media/images/`.
- If the interactive reel shows gaps, confirm the batch image files exist for the
  current window (7 slots: 3 previous, active, 3 next, with a 2-slot prefetch)
  and that the `/api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}`
  endpoint resolves the expected paths.
- When snapshots disagree, rerun the pipeline or `/api/media/generate` so the
  job manager rewrites chunk metadata and audio assets consistently before
  re-testing the frontend.

With matching snapshots both machines should render the same media search
experience.
