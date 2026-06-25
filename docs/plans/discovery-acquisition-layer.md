# Discovery Acquisition Layer Plan

Last updated: 2026-06-25

## Goal

Add a backend discovery layer that can search for lawful source artifacts,
queue or perform acquisition, normalize local files, enrich metadata, and hand
the result to existing book, subtitle, and YouTube dubbing creation flows.

This layer should make Apple and Web Create feel like one pipeline:

1. Search for a book or video.
2. Review candidates with source, rights, language, subtitle, and metadata
   signals.
3. Acquire or locate the source file.
4. Extract/select subtitles when applicable.
5. Enrich metadata.
6. Start a translation/narration/dubbing job using the same payload shape Web
   and Apple already use.

## Policy Boundary

The backend must not automate access to piracy sites or copyrighted works that
the user is not authorized to download. Do not integrate Z-Library or similar
shadow-library download automation.

Allowed source classes:

- User-owned local/NAS files and user-provided URLs.
- Public-domain or open-license ebook catalogs.
- Metadata-only book/video catalogs.
- YouTube search and download workflows that respect the configured backend
  policy and the user's rights.
- Torrent/Usenet/NZB handoff only for lawful content, via explicit user review
  and configured indexer/downloader adapters.

## Existing Repo Capabilities

Video and subtitle foundations:

- `modules/services/youtube_subtitles.py` lists YouTube subtitles, video
  formats, downloads selected subtitle tracks, and downloads videos with yt-dlp.
- `modules/webapi/routers/subtitle_utils/youtube_routes.py` exposes
  `/api/subtitles/youtube/subtitles`, `/download`, `/video`, `/library`,
  `/subtitle-streams`, `/extract-subtitles`, cleanup routes, and
  `/youtube/dub`.
- `modules/services/youtube_dubbing/` already normalizes NAS video sources,
  parses/merges dialogues, generates dubbed audio/video, writes subtitle
  artifacts, and serializes job metadata.
- `modules/services/youtube_video_metadata_service.py` and
  `modules/services/metadata/clients/ytdlp.py` enrich YouTube metadata.

Book foundations:

- `modules/services/source_discovery.py` and
  `modules/webapi/routes/books_routes.py` already support NAS-backed EPUB
  discovery through `/api/pipelines/files`, plus upload, deletion,
  newest-first defaults, and content-index loading. Generated-book creation
  lives in `modules/webapi/routers/create_book.py`.
- `modules/services/media_metadata_service.py` plus
  `modules/services/metadata/clients/openlibrary.py` and
  `google_books.py` already enrich book metadata.
- `modules/library/` can persist book/video library entries and source
  diagnostics.

Sentence/reading foundations:

- `modules/epub_parser.py` owns regex/word-limit sentence splitting.
- `modules/core/ingestion.py` caches refined sentence lists and content indexes
  per EPUB/settings.
- `modules/core/rendering/timeline.py` validates timing continuity.
- `modules/webapi/routes/media/timing.py` smooths token edges for legacy timing
  responses.
- Tests currently cover word-limit splitting and multi-sentence timing
  continuity, but sentence splitting has limited losslessness coverage.

## Provider Adapters

Use a provider-neutral backend service under `modules/services/acquisition/` with
small adapters. Every adapter should return the same DTO shape and declare what
it can do: `search`, `metadata`, `acquire`, `poll`, `extract_subtitles`, or
`import_local`.

Suggested adapters:

- `youtube_search`: Use YouTube Data API search/list for search metadata when
  `YOUTUBE_API_KEY` is configured. Normalize to video id, title, channel,
  duration, published date, thumbnail, URL, and embeddability/availability
  hints. Acquisition still reuses existing yt-dlp routes, because YouTube
  captions.download requires owner/editor permission for the video.
- `youtube_url`: Existing direct URL inspection/download path, wrapped in the
  discovery DTO so Web and Apple can treat searched and pasted videos the same.
- `nas_video`: Existing `/api/subtitles/youtube/library` scanner exposed as a
  discovery provider.
- `download_station`: Synology Download Station handoff adapter for reviewed
  torrent/magnet/NZB/URL tasks. It should enqueue, poll status, and map
  completed files back into the NAS video picker root. Keep credentials in
  backend config only.
- `newznab_torznab`: Optional lawful indexer search adapter for configured
  Newznab/Torznab/Prowlarr-compatible endpoints. Return metadata and a
  download token/URL for review; do not auto-submit without user confirmation.
- `sabnzbd` / `nzbget`: Optional direct NZB downloader adapters if the NAS is
  not the queue owner.
- `openlibrary`: Metadata-first ebook discovery. Use for enrichment and
  candidate review; do not assume downloadable EPUB availability.
- `gutenberg` / `gutendex`: Public-domain ebook search/download adapter.
- `internet_archive`: Public/open item search and file-list adapter. Only offer
  downloadable EPUB/PDF/text files where access metadata permits ordinary
  download.
- `local_epub`: Existing NAS EPUB picker and upload path as a discovery
  provider.

## Backend API Shape

Initial routes:

- `GET /api/acquisition/providers`
  - Lists configured providers, media kinds, capabilities, auth/config status,
    and safe policy notes.
  - Status: implemented as a token-safe provider registry in
    `modules/services/acquisition/` and advertised through
    `creation.acquisitionProvidersPath` in `/api/system/runtime`.
- `GET /api/acquisition/discover`
  - Query params: `media_kind=book|video`, `q`, `provider`, `language`,
    `limit`, optional provider filters.
  - Returns normalized candidates with provider id, source id, title,
    contributors, language, year/date, thumbnail/cover, rights/source notes,
    available subtitle/file hints, and an opaque `candidate_token`.
  - Status: implemented for backend-visible `local_epub`, `nas_video`, and
    configured `youtube_search` metadata results, plus explicit
    `gutenberg` public catalog searches. Discovery requires editor/admin access
    because local candidates can expose backend-visible source paths. YouTube
    search returns metadata only; downloading remains a separate reviewed
    workflow through existing routes.
- `POST /api/acquisition/acquire`
  - Body: `candidate_token`, target root/category, selected format/subtitle,
    confirmation flags.
  - Returns an acquisition task id or completed artifact reference.
  - Status: implemented for reviewed Gutenberg EPUB candidates as a synchronous
    completed artifact reference under the configured books root. Download
    URLs are constrained to known Gutenberg hosts and EPUB paths.
- `GET /api/acquisition/jobs/{task_id}`
  - Polls queue/download/import status and surfaces completed local file paths
    only when they are under configured safe roots.
- `POST /api/acquisition/artifacts/{artifact_id}/prepare`
  - Normalizes completed artifact into one of the existing Create sources:
    EPUB source path, video path plus subtitle path, or metadata draft.

Future Apple/Web handoff:

- Apple Create and Web Create should consume the same discovery provider list,
  search results, acquisition status, and prepared artifact DTO.
- Save selected discovery candidates into creation templates/drafts using
  source metadata and opaque provider tokens rather than raw credentials.

## Data Model

Core DTO fields:

- `candidate_id`: stable provider-local id.
- `provider`: adapter id.
- `media_kind`: `book` or `video`.
- `title`, `subtitle`, `authors`/`channel`, `year`/`published_at`.
- `language`, `duration_seconds`, `source_url`, `thumbnail_url`/`cover_url`.
- `rights`: `public_domain`, `open_license`, `user_provided`, `unknown`, or
  `restricted`.
- `capabilities`: available actions for this candidate.
- `metadata`: normalized metadata draft compatible with existing
  `media_metadata`.
- `requires_confirmation`: true for every downloader/handoff provider.
- `policy_notes`: short user-facing source/legal caveats.

Acquisition task fields:

- `task_id`, `provider`, `status`, `progress`, `message`, `started_at`,
  `updated_at`.
- `download_client_task_id` for Download Station/SAB/NZBGet, stored server-side.
- `artifact_refs`: completed local files under safe roots.
- `next_actions`: `extract_subtitles`, `choose_subtitle`, `create_book_job`,
  `create_dub_job`, `open_in_library`.

## First Implementation Milestones

1. Backend contracts only:
   - Status: initial provider-list contract implemented.
   - Added acquisition schemas and a provider registry.
   - Registered token-safe provider metadata for `local_epub`, `nas_video`,
     `youtube_url`, `youtube_search`, `download_station`,
     `newznab_torznab`, `openlibrary`, `gutenberg`, and
     `internet_archive`.
   - Added route/service tests for provider listing, config status, runtime
     descriptor advertisement, token-safe payloads, and route telemetry.

2. YouTube search:
   - Status: first metadata-search adapter implemented behind
     `YOUTUBE_API_KEY` / `youtube_api_key`.
   - `discover_acquisition_candidates` calls YouTube Data API `search.list`
     plus `videos.list` to normalize title, channel, thumbnail, published date,
     duration, source URL, and opaque candidate token.
   - Return search results only; use existing subtitle/video download routes for
     acquisition.
   - Remaining: add quota-aware UI errors and provider-specific disabled-state
     rendering.

3. NAS/download queue handoff:
   - Add Download Station adapter with `enqueue`, `poll`, and completed-file
     mapping.
   - Add Newznab/Torznab/Prowlarr search adapters only behind explicit config.
   - Keep search results as review-only until the user confirms acquisition.
   - Treat the warmed Synology Download Station Safari session as an attended
     verification aid only. Backend integration should use configured API
     credentials/tokens, not scraped browser state.

4. Lawful ebook discovery:
   - Status: local EPUB source discovery is implemented through the normalized
     discovery contract, sorted newest-first like `/api/pipelines/files`.
   - Status: Project Gutenberg/Gutendex search is available as an explicit
     `gutenberg` discovery provider that returns public catalog metadata and
     EPUB links for reviewed acquisition.
   - Add OpenLibrary metadata search provider.
   - Add Internet Archive metadata/file-list provider with access filtering.
   - Reuse existing EPUB import/upload and metadata enrichment paths.

5. Web and Apple UI:
   - Status: Web Narrate Ebook and Apple Narrate EPUB can discover
     `local_epub` and explicit `gutenberg` candidates. Local selection fills
     the existing input path; Gutenberg selection calls the reviewed acquire
     route first, then fills the returned local EPUB path. Submit payloads,
     uploads, deletes, chapter loading, and templates are unchanged.
   - Add a Discovery tab in Web Create and Apple Create.
   - Start with source selection only: search, prepare artifact, then populate
     existing creation controls.
   - Save discovery state into creation templates/drafts.

## Sentence Splitting And Reading Fluidity

Current risks found during the first code audit:

- `extract_sections_from_epub` should be hardened to follow EPUB spine order
  and ignore nav/TOC-like documents so sentence numbering cannot start from
  out-of-order or non-content HTML.
- `split_text_into_sentences` is English-biased. Lowercase starts after
  punctuation, dialogue, abbreviations, ellipses, and CJK punctuation need
  regression fixtures before changing defaults.
- Backend chunk timing uses chunk-local `sentenceIdx` inside
  `timingTracks`, while top-level `/api/jobs/{job_id}/timing` uses global
  sentence numbers. Every client must normalize this boundary explicitly.
- Web and Apple sequence planners now have per-sentence fallback coverage for
  mixed chunks where one sentence has gates and another only has
  `phaseDurations`; keep those tests in place when changing planner behavior.

Near-term hardening before replacing the splitter:

- Add losslessness tests for `split_text_into_sentences`: normalized joined
  output should preserve normalized input text for quotes, parentheses,
  initials, honorifics, ellipses, em dashes, and chapter-heading boundaries.
  Status: initial regression coverage now preserves closing quotes after
  sentence punctuation and parenthetical words.
- Add tests for section boundary handling in `get_refined_sentences` so adjacent
  EPUB sections do not merge text or drop the first/last sentence.
- Add CJK and non-Latin segmentation fixtures. The current regex expects
  uppercase Latin starts after punctuation, which can miss boundaries for many
  languages.
- Add a content-index invariant: sentence numbers must be contiguous, unique,
  and match the refined sentence list length. Status: initial approximate and
  truncated range regression coverage added.
- Add timing invariant coverage that every rendered chunk has monotonically
  increasing sentence gates and non-overlapping token timings after smoothing.
- Wire `validate_cross_sentence_continuity` and
  `validate_chunk_timing_alignment` into export-time checks or a strict
  post-export test helper so new metadata cannot skip or overlap sentences
  silently.

Likely implementation path:

- Keep the current regex splitter as `regex` mode.
- Add optional `syntok` or spaCy-backed `modern` splitter behind config, with a
  deterministic fallback to regex.
- Store splitter mode/version in refined-list cache metadata so cache
  invalidates when splitter behavior changes.
- Add a dry-run comparison utility that reports sentence-count deltas,
  normalized text coverage, tiny-fragment rate, and max words per segment before
  switching defaults.

## Verification Gates

Discovery backend:

- `tests/modules/webapi/test_acquisition_routes.py`
- `tests/modules/services/test_acquisition_providers.py`
- `tests/modules/webapi/test_system_routes.py`
- Local target: `make test-backend-acquisition`
- Manifest target: `test-backend-acquisition`
- Added to `make apple-pipeline-backend-tests`.

Web/Apple:

- Web focused discovery tests under `web/src/components/__tests__/BookNarrationForm.test.tsx`.
- Apple Create contract tests for provider list, source handoff, and template
  preservation.
- No physical device deployment unless explicitly requested.

Sentence quality:

- Expand `tests/test_sentence_splitting.py`.
- Add content-index invariants to `tests/modules/core/test_ingestion_content_index_cache.py`.
- Keep `tests/modules/core/test_multi_sentence_chunks.py` as timing continuity
  coverage.
- Keep Web and Apple sequence-plan coverage for mixed gate/phase-duration
  chunks.

## External References

- YouTube Data API search/list:
  `https://developers.google.com/youtube/v3/docs/search/list`
- YouTube captions API:
  `https://developers.google.com/youtube/v3/docs/captions`
- Synology Download Station Web API:
  `https://global.download.synology.com/download/Document/Software/DeveloperGuide/Package/DownloadStation/All/enu/Synology_Download_Station_Web_API.pdf`
- SABnzbd API: `https://sabnzbd.org/wiki/advanced/api`
- NZBGet append API: `https://nzbget.com/documentation/api/append/`
- Prowlarr API: `https://prowlarr.com/docs/api/`
- Torznab/Newznab API specs:
  `https://torznab.github.io/spec-1.3-draft/torznab/Specification-v1.3.html`
  and `https://torznab.github.io/spec-1.3-draft/external/newznab/api.html`
- Open Library APIs: `https://openlibrary.org/developers/api`
- Internet Archive metadata API:
  `https://archive.org/developers/metadata.html`
- Project Gutenberg offline catalog and robot policy:
  `https://www.gutenberg.org/ebooks/offline_catalogs.html` and
  `https://www.gutenberg.org/policy/robot_access.html`
- Gutendex public-domain catalog API: `https://gutendex.com/`
