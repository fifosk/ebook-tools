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
- Inspect `storage/<job_id>/metadata/job.json` on each device; mismatched
  `generated_files.chunks[]` or chunk counts indicate that audio regeneration
  or metadata compaction ran on only one machine.
- Spot-check a few chunk metadata files (`metadata/chunk_XXXX.json`) on each
  machine—especially their `timingTracks` entries—to ensure both environments
  are replaying the same highlight provenance. Legacy jobs may still include a
  `metadata/timing_index.json` if you prefer comparing single-file hashes.
- For Apple playback, chunk-level `timingTracks.original` and
  `timingTracks.translation` use chunk-local `sentenceIdx` values first, then
  legacy/global sentence numbers as a fallback. If word highlights disappear on
  iPad/iPhone/Apple TV while Web still works, compare those local indices before
  regenerating audio.
- Apple interactive reader sentence sliders live in the shared footer and are
  draft-only while the user is dragging. Keyboard sentence skips,
  search/bookmark/chapter jumps, and word taps should clear the draft so the
  footer follows live playback again. When paused, a word tap rewinds to that
  word, stays paused, and opens lookup. Sequence word taps should cancel any
  older audio-ready transition and drift-check same-track seeks before
  restoring volume, otherwise a stale track load can undo the tapped-word
  rewind.
- Apple interactive reader skip controls should use a single explicit
  sentence-row jump path before falling back to clock-based seeking. In
  original-only or translation-only playback, sentence jumps should prefer
  `originalStartGate` or `startGate` over token-timeline starts so late-chapter
  translated tracks do not skip whole batches when token timing drifts. The
  gate choice belongs in `SentencePositionProvider.gateStartTime` and is covered
  by `bash scripts/check_apple_sentence_position_provider.sh`. Skip controls
  should resolve the current active sentence through
  `TextPlayerTimeline.resolveActiveIndex(sentences:activeTimingTrack:...)`
  before falling back to prebuilt timeline rows, so rendering and navigation
  share the same gate-aware active sentence on translation-only jobs.
- On iPad, paused lookup bubble word navigation must stay on the single
  `PlayerKeyboardShortcutBroker` path shared by app menu commands, UIKit key
  commands, hardware-press fallback, and GameController fallback. Do not
  reintroduce hidden SwiftUI arrow shortcut layers in the book or video bubble.
  Plain Left/Right should call the same `handleWordNavigation` path even when
  bubble controls have focus or lookup read-aloud starts, finishes, or cancels,
  cancel any pending delayed lookup, reset any broker/player debounce state
  created before pronunciation, then refresh the definition immediately from
  the new token. Ctrl+Left/Ctrl+Right also yield to an open bubble before
  sentence transport, and the UIKit event bridge prefers a live keyboard
  modifier snapshot over stale `UIPress` flags when deciding whether Control is
  down. The book reader also keeps a short physical-arrow latch across
  broker, GameController, and first-responder delivery, so one iPad key press
  cannot both move a word and skip a sentence batch.
- Apple playback language pills must resolve destination labels from
  `target_language`, `translation_language`, or `target_languages`; do not use
  `book_language` as a target fallback because it is source metadata for
  generated/narrated books.
- Apple Original/Translation text-track toggles should keep narration audio
  mode aligned with visible text. Hiding Original switches to translation-only
  audio when available, hiding Translation switches to original-only audio, and
  stale lookup selections pointing at hidden tracks should be cleared.
- Apple sentence jumps must wait for renderable chunk metadata before preparing
  audio. If the selected chunk only has placeholder ranges or a metadata fetch
  is already in flight, wait for the chunk load and verify the target sentence
  has tokens before seeking; otherwise iPad/iPhone can play audio while the
  transcript remains on the loading wheel.
- Apple Music reading-bed auto-resume must require `audioCoordinator.isPlaybackRequested`
  plus MusicKit auto-resume intent (`musicCoordinator.canAutoResumeReadingBed`).
  The guard intentionally does not require `audioCoordinator.isPlaying`, because first sentence starts and
  sequence track switches can publish the playback request before the AVPlayer
  playing state lands. Jump/Search/Bookmark navigation while paused should not
  restart Apple Music because paused navigation clears the playback request and
  manual MusicKit pauses clear the auto-resume intent. Apple Music should follow
  the same requested-playback lifecycle as the built-in bed: pause on definitive
  narration pauses, continue through short sentence transitions, resume when
  narration is requested, keep playing under active reader navigation handoffs
  while narration intent is still live, keep queued MusicKit entries eligible
  even before track metadata refreshes, and use `.mixWithOthers` without
  `.duckOthers` plus neutral `.default` audio-session mode while mixing.
  Apple Music is an optional background bed, not narration audio: the app
  should leave Music at system volume and use the mix slider to reduce
  sentence narration around it so the bed can usually sit louder without
  relying on system ducking or spoken-audio ownership.
- For Apple TV video lookup, cached lookup results with `cachedAudioRef` should
  expose the TV bubble's play-from-narration action and seek video playback to
  `cachedAudioRef.t0`. If lookup read-aloud disappears only on Apple TV, verify
  the video bubble path still forwards `onPlayFromNarration`, the bubble cycles
  left/right focus through `readAloud`, and `PronunciationSpeaker` retries tvOS
  audio-session setup after video playback.
- Web and Apple playback should expose the same 5, 15, 30, and 45 minute sleep
  timer presets. On Web, confirm the timer is present in interactive text
  navigation, shared video playback, and YouTube Dub playback, and that
  expiration pauses narration plus the active reading bed for books or pauses
  the video element for media jobs.
- For sequence playback drift, compare sentence gate fields
  (`originalStartGate`/`originalEndGate` and `startGate`/`endGate`) with each
  sentence's `phaseDurations`; Web and Apple fill only the missing per-sentence
  gates from phase durations, so mixed chunks should still plan every original
  and translation sentence.
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
