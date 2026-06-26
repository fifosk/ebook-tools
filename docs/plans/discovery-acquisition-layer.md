# Discovery Acquisition Layer Plan

Last updated: 2026-06-26

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
  continuity. Sentence splitter dry-runs now also report contiguous source-span
  coverage, unmatched sentence counts, and skipped-text character counts so
  regex and modern modes can be compared for no-skip/no-overlap behavior even
  for no-space scripts where joined-text normalization is too strict. The
  `/api/books/options` Create contract advertises supported splitter modes,
  cache versions, and comparison metric keys for Web and Apple clients, and
  Apple Create readiness validates that contract before simulator/device
  journeys.

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
    safe policy notes, discoverable media kinds, and backend-owned default
    discovery provider ids per media kind.
  - Web Narrate Ebook, Web Video Dubbing, and Apple Create adopt those
    backend-owned defaults for the initial book/video discovery picker while
    preserving user-chosen providers for the active session.
  - Status: implemented as a token-safe provider registry in
    `modules/services/acquisition/` and advertised through
    `creation.acquisitionProvidersPath` in `/api/system/runtime`.
- `GET /api/acquisition/discover`
  - Query params: `media_kind=book|video`, `q`, `provider`, `language`,
    `limit`, optional provider filters, and repeated `source_id` values for
    provider-specific focused lookups such as Internet Archive identifiers
    surfaced by Open Library metadata.
  - Returns normalized candidates with provider id, source id, title,
    contributors, language, year/date, thumbnail/cover, rights/source notes,
    available subtitle/file hints, and a client-opaque `candidate_token`.
    Candidate and artifact tokens are HMAC-signed by the backend and reject
    secret-bearing payload keys or URL query credentials before signing. Set
    `EBOOK_ACQUISITION_TOKEN_SECRET` or reuse `EBOOK_CONFIG_SECRET` for stable
    tokens across API restarts or multi-worker deployments; local dogfood runs
    fall back to a per-process secret. Tokens are not an encryption channel, so
    indexer API-key URLs must stay server-side or move through a server-side
    reference store before direct Download Station handoff is enabled.
  - Status: implemented for backend-visible `local_epub`, `nas_video`,
    configured `youtube_search` metadata results, metadata-applicable
    `openlibrary` book metadata, and explicit `gutenberg` / `internet_archive`
    public catalog searches. Discovery requires editor/admin access because
    local candidates can expose backend-visible source paths. YouTube search
    returns metadata only. Open Library search returns book metadata that Web
    and Apple can apply to the Create draft. When Open Library returns
    Internet Archive identifiers, Web and Apple can bridge those reviewed IDs
    into a focused `internet_archive` lookup that only surfaces downloadable
    public/open EPUB candidates. Other downloading remains a separate reviewed
    workflow through existing routes or manual downloads. Focused Internet
    Archive `source_id` values are now validated only when that provider is
    queried, so stale deep-link query params do not break local EPUB or
    metadata-only discovery after users switch providers.
- `POST /api/acquisition/acquire`
  - Body: `candidate_token`, target root/category, selected format/subtitle,
    confirmation flags.
  - Returns an acquisition task id or completed artifact reference.
  - Status: implemented for reviewed Gutenberg EPUB candidates as a synchronous
    completed artifact reference under the configured books root. Download
    URLs are constrained to known Gutenberg hosts and EPUB paths, and tampered
    or unsigned candidate tokens are rejected before acquisition.
- `POST /api/acquisition/jobs`
  - Body: `provider=download_station`, reviewed `source_uri` or signed
    `candidate_token`, `confirmed=true`, optional `destination`.
  - Status: implemented for Synology Download Station handoff using backend
    config/env credentials only. Newznab/Torznab discovery stores raw download
    URLs in a backend-side acquisition reference and returns only the signed
    candidate token, so Web/Apple can submit reviewed indexer candidates to
    Download Station without receiving API-key URLs. The response returns
    token-safe task status and next actions, never NAS credentials, session ids,
    raw indexer URLs, or browser state.
- `GET /api/acquisition/jobs/{task_id}`
  - Polls queue/download/import status and surfaces completed local file paths
    only when they are under configured safe roots.
  - Status: implemented for Download Station task polling. Completed files are
    surfaced both as top-level `completed_files` and as token-safe metadata
    hints (`completed_files`, `files`, and single-file `completed_file`) so Web
    and Apple Create can reconnect a finished task to manual/NAS discovery
    through the same fallback contract. Completed files are still imported
    through `manual_downloads` / NAS discovery after they land in configured
    backend-visible folders.
- `POST /api/acquisition/artifacts/{artifact_id}/prepare`
  - Normalizes completed artifact into one of the existing Create sources:
    EPUB source path, video path plus subtitle path, or metadata draft.
  - Status: implemented for token-safe local/acquired EPUB artifacts and local
    NAS/manual video artifacts. The response returns existing Create source
    fields (`input_file`, `video_path`, preferred `subtitle_path`, subtitle
    hints, metadata, and next actions) so Web and Apple clients can share the
    same handoff instead of trusting raw client-provided paths.

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
   - Status: editor/admin-only discovery, acquire, artifact prepare, and
     downloader handoff/poll routes now record token-safe `forbidden` duration
     metrics before provider calls run, so Web/Apple Create permission drift is
     visible without logging user IDs, query text, candidate tokens, task IDs,
     source URIs, credentials, auth headers, or raw provider payloads.
   - Status: acquire, artifact-prepare, and downloader-poll route inputs now
     trim encoded route/payload whitespace and reject empty normalized artifact,
     task, or acquisition candidate IDs before service/provider calls, while
     provider query/body IDs, candidate handoff tokens, source URIs, and
     destinations are normalized at the route boundary. Focused route tests
     keep Web and Apple discovery handoffs from reintroducing padded IDs or
     blank backend calls.
   - Status: Unexpected acquisition provider failures now return generic
     Web/Apple-safe errors and log only aggregate operation/result messages,
     suppressing exception text that may contain NAS paths, candidate tokens,
     task ids, source URIs, or provider credentials.
   - Status: Acquisition route serializers now recursively strip obvious
     secret-bearing metadata keys and sensitive URL query parameters from
     discovery candidates, prepared artifacts, acquisition artifacts, and
     downloader job status responses before Web or Apple clients receive them.

2. YouTube search:
   - Status: first metadata-search adapter implemented behind
     `YOUTUBE_API_KEY` / `youtube_api_key`.
   - `discover_acquisition_candidates` calls YouTube Data API `search.list`
     plus `videos.list` to normalize title, channel, thumbnail, published date,
     duration, source URL, and opaque candidate token.
   - Status: Web Video Dubbing and Apple YouTube Dub can switch discovery
     between `nas_video` and `youtube_search`; selected YouTube metadata
     candidates populate the existing YouTube metadata lookup/review flow.
   - Status: Web YouTube downloads can search `youtube_search` candidates,
     fill the existing URL field, then reuse the current subtitle inspection,
     subtitle selection, and video download flow.
   - Status: Web Video Dubbing, Web YouTube downloads, and Apple YouTube Dub
     read `/api/acquisition/providers` so YouTube search is visibly disabled
     with a not-configured message when the backend lacks YouTube Data API
     credentials.
   - Status: YouTube Data API quota, rate-limit, and authorization failures are
     mapped to token-safe public discovery errors so Web/Apple surfaces can show
     useful messages without exposing raw provider payloads or API keys.
   - Return search results only; use existing subtitle/video download routes for
     acquisition.

3. NAS/download queue handoff:
   - Status: Download Station adapter can enqueue reviewed URI/magnet handoffs
     and poll provider task state through `/api/acquisition/jobs`, with
     credentials resolved server-side from config/env and token-safe responses.
   - Status: Web Video Dubbing exposes a reviewed Download Station handoff
     panel for authorized URLs or magnet links, polls the shared task endpoint,
     and points completed tasks back through manual-download/NAS discovery for
     final file selection.
   - Status: Apple YouTube Dub exposes the same reviewed Download Station
     handoff, polls the shared task endpoint, then refreshes manual-download
     discovery and the NAS video list when the task completes.
  - Status: Apple Create preserves Download Station job metadata and uses
    safe completed-file metadata hints as a fallback when matching completed
    downloads back to manual-download discovery candidates; its completion
    message and handoff panel now name files through the same top-level and
    metadata fallback resolver.
  - Status: Web Video Dubbing also resolves completed Download Station files
    from the same acquisition job metadata hints when top-level
    `completed_files` are absent, keeping its visible completion message and
    handoff panel aligned with Apple Create.
  - Status: `manual_downloads` discovery is available for configured backend
     inbox roots (`manual_download_root`, `manual_download_roots`,
     `download_station_completed_root`, existing `youtube_video_root` /
     `video_download_root`, or the matching `EBOOK_*` environment variables),
     returning user-authorized EPUB/video files already downloaded
     through Safari, Synology Download Station, or another attended workflow.
   - Status: Manual-download video discovery now scans all configured inbox
     roots before applying the requested result limit, then sorts newest-first,
     so Web and Apple Create defaults do not miss a fresher completed download
     just because an older root appeared first.
   - Status: Apple YouTube Dub can search the same `manual_downloads` video
     candidates and fill the existing video/subtitle fields from local paths
     and discovered subtitle hints.
   - Status: Newznab/Torznab search is implemented behind explicit indexer
     config as metadata-only, review-only discovery. Results expose safe title,
     date, size, category, and swarm metadata while raw NZB/torrent URLs and
     API keys stay server-side.
   - Status: Newznab/Torznab candidates with a download URL now persist that
     URL in a backend-side acquisition reference. `/api/acquisition/jobs` can
     submit the signed candidate token to Download Station after user review,
     without exposing the raw URL to Web or Apple clients.
   - Status: Web Video Dubbing and Apple YouTube Dub expose configured
     `newznab_torznab` as an indexer search source, displaying review-only
     metadata without filling playable source paths or exposing raw download
     links.
   - Status: Web Video Dubbing and Apple YouTube Dub can pass the selected
     indexer candidate token into the reviewed Download Station handoff, so the
     backend resolves the stored URL only after the user confirms acquisition.
   - Keep search results as review-only until the user confirms acquisition.
   - Treat the warmed Synology Download Station Safari session as an attended
     verification aid only. Backend integration should use configured API
     credentials/tokens, not scraped browser state.

4. Lawful ebook discovery:
   - Status: local EPUB source discovery is implemented through the normalized
     discovery contract, sorted newest-first like `/api/pipelines/files`.
   - Status: Web and Apple Narrate Ebook discovery can explicitly search the
     `manual_downloads` provider and fill the standard input path from a
     backend-visible manual EPUB candidate.
   - Status: Project Gutenberg/Gutendex search is available as an explicit
     `gutenberg` discovery provider that returns public catalog metadata and
     EPUB links for reviewed acquisition.
   - Status: Internet Archive text-item search is available as an explicit
     `internet_archive` discovery provider. The backend inspects item metadata,
     skips restricted/encrypted/private files, and only offers ordinary EPUB
     download candidates through the reviewed acquire endpoint.
   - Status: Reviewed public-catalog acquisition responses preserve artifact
     metadata through the FastAPI route and Apple DTO boundary, including
     Gutenberg ids and Internet Archive identifiers for downstream traceability.
   - Status: Open Library metadata search is implemented as metadata-only
     discovery. Candidates include draft-friendly title, author, year,
     language, ISBN, cover URL, Open Library IDs, and available Internet
     Archive identifiers; Web Narrate Ebook and Apple Narrate EPUB can apply
     those metadata fields without choosing or acquiring an EPUB source, or use
     the identifiers to fetch reviewed public Archive EPUB candidates through
     the shared discovery contract.
   - Reuse existing EPUB import/upload and metadata enrichment paths.

5. Web and Apple UI:
   - Status: Web Narrate Ebook and Apple Narrate EPUB can discover
     `local_epub`, explicit `gutenberg`, and explicit `internet_archive`
     candidates. Local selection now calls the shared prepare endpoint before
     filling the existing input path; public catalog selection calls the
     reviewed acquire route first, prepares the returned artifact id, then
     fills the prepared local EPUB path. Submit payloads, uploads, deletes,
     chapter loading, and templates are unchanged.
   - Status: Web and Apple Narrate EPUB read the provider registry for ebook
     discovery readiness and disable unavailable local/manual source searches
     with a source-root configuration message instead of returning an
     unexplained empty candidate list.
   - Status: Apple Narrate EPUB book discovery options now carry availability
     like video discovery options; the attended Z-Library placeholder stays
     selectable only to show the explicit disabled-policy message, while its
     Search action remains disabled when the backend registry is missing.
   - Status: Web Narrate Ebook renders ebook discovery choices from a single
     provider descriptor list, and Apple Narrate EPUB uses a menu picker so the
     growing public-catalog provider set remains readable on compact surfaces.
   - Status: Web Narrate Ebook discovery provider ordering, availability
     messages, and backend-owned default selection now live in a focused helper
     with direct `test-web-create-intake-focused` coverage.
   - Status: Web Video Dubbing and Apple YouTube Dub can discover `nas_video`
     and `manual_downloads` local video candidates for existing video/subtitle
     selection, and `youtube_search` metadata candidates for reviewed YouTube
     metadata lookup before separate subtitle/video download handling.
   - Status: Web Video Dubbing and Apple YouTube Dub templates now persist
     token-free video `discovery_state` for reviewed NAS/manual/YouTube/indexer
     candidates, including provider, candidate id, selected video/subtitle
     paths, rights, source kind, and visible query/source metadata while
     excluding candidate tokens and credential-bearing fields.
   - Status: Web Video Dubbing can now queue authorized Download Station source
     URIs from the source panel and poll task state without leaving the creation
     flow.
   - Status: Apple YouTube Dub can now queue authorized Download Station source
     URIs from Create, poll task state, and return completed files through the
     existing manual-download/NAS selection path.
   - Status: Web Narrate Ebook and Apple Narrate EPUB now expose discovery as
     a first-class source panel/tab while preserving the existing source path,
     server picker, upload/import, and prepared artifact handoff behavior.
   - Status: Web Narrate Ebook and Apple Narrate EPUB source selection now
     searches, prepares local/acquired EPUB artifacts, then populates existing
     creation controls.
   - Status: Web Narrate Ebook and Apple Narrate EPUB templates now persist
     token-free `discovery_state` for selected book discovery candidates,
     including provider, candidate id, selected path, source URL, rights, and
     visible catalog metadata where available. Candidate tokens and credentials
     remain excluded by client/backend template sanitizers.

## Sentence Splitting And Reading Fluidity

Current risks found during the first code audit:

- `extract_sections_from_epub` should be hardened to follow EPUB spine order
  and ignore nav/TOC-like documents so sentence numbering cannot start from
  out-of-order or non-content HTML. Status: section extraction now skips
  ebooklib navigation documents / nav-property XHTML and orders spine-backed
  content before loose non-spine HTML.
- `split_text_into_sentences` is English-biased. Lowercase starts after
  punctuation, dialogue, abbreviations, ellipses, and CJK punctuation need
  regression fixtures before changing defaults. Status: smart closing quotes
  after sentence punctuation now split cleanly, single-letter initials such as
  `Dr. A. Stone` stay with the following name, lowercase sentence starts after
  terminal punctuation split into their own readable segments, ASCII quoted
  dialogue can start a new sentence after terminal punctuation, inline dialogue
  tags stay with their quote, ellipsis/lowercase continuations remain together,
  and `a.m.` / `p.m.` can end a sentence before a clear uppercase follow-up
  without splitting lowercase continuations such as `the 5 p.m. train`.
- Backend chunk timing uses chunk-local `sentenceIdx` inside
  `timingTracks`, while top-level `/api/jobs/{job_id}/timing` uses global
  sentence numbers. Every client must normalize this boundary explicitly.
- Web and Apple sequence planners now have per-sentence fallback coverage for
  mixed chunks where one sentence has gates and another only has
  `phaseDurations`; keep those tests in place when changing planner behavior.
- Web sentence-to-chunk lookup now tolerates overlapping chunk ranges and
  deterministically resolves duplicated boundaries to the earliest source chunk;
  Apple resume/jump lookup already uses first-match chunk selection.

Near-term hardening before replacing the splitter:

- Add losslessness tests for `split_text_into_sentences`: normalized joined
  output should preserve normalized input text for quotes, parentheses,
  initials, honorifics, ellipses, em dashes, and chapter-heading boundaries.
  Status: regression coverage now preserves normalized text for closing quotes
  after sentence punctuation, parenthetical punctuation, honorifics/initials,
  lowercase starts, ASCII quoted dialogue starts, inline dialogue tags,
  ellipses with lowercase continuation, ASCII/Arabic/fullwidth
  comma/semicolon split delimiters, and smart closing quote sentence
  boundaries.
- Add tests for section boundary handling in `get_refined_sentences` so adjacent
  EPUB sections do not merge text or drop the first/last sentence.
  Status: focused fake-section coverage now asserts refined sentence order and
  content-index chapter ranges remain contiguous across adjacent sections.
- Add CJK and non-Latin segmentation fixtures. The current regex expects
  uppercase Latin starts after punctuation, which can miss boundaries for many
  languages. Status: focused fixtures now cover Chinese/Japanese sentence
  punctuation without spaces plus Arabic/Urdu question/full-stop punctuation.
- Add a content-index invariant: sentence numbers must be contiguous, unique,
  and match the refined sentence list length. Status: initial approximate and
  truncated range regression coverage added, and content-index caches are
  salted with the splitter version plus a refined sentence-list hash so stale
  chapter ranges are invalidated after splitter behavior changes.
- Add timing invariant coverage that every rendered chunk has monotonically
  increasing sentence gates and non-overlapping token timings after smoothing.
  Status: `validate_export_timing_tracks` now derives per-sentence windows
  from exported original/translation timing tracks, persists the gate summary
  under `sentence_gates`, and fails post-export validation when sentence
  windows overlap after smoothing/scaling.
- Wire `validate_cross_sentence_continuity` and
  `validate_chunk_timing_alignment` into export-time checks or a strict
  post-export test helper so new metadata cannot skip or overlap sentences
  silently. Status: `validate_export_timing_tracks` now checks exported
  original/translation tracks for monotonicity, token overlaps, and duration
  alignment after scaling/clamping; `BatchExporter` persists the summary under
  `timing_validation.post_export`, and focused tests assert the helper against
  generated multi-sentence tracks.

Likely implementation path:

- Keep the current regex splitter as `regex` mode.
- Add optional `syntok` or spaCy-backed `modern` splitter behind config, with a
  deterministic fallback to regex. Status: `sentence_splitter_mode` now accepts
  `regex` (default) or opt-in `modern`; the modern path uses `syntok` only when
  available and returns to the existing regex splitter if import, segmentation,
  or normalized text coverage checks fail.
- Store splitter mode/version in refined-list cache metadata so cache
  invalidates when splitter behavior changes. Status: refined sentence and
  content-index caches now persist `sentence_splitter_mode` plus a mode-specific
  version, and cache reuse compares those fields with the active pipeline
  configuration. The current regex splitter salt is `regex-v8`, covering
  lossless leading-bullet preservation, Unicode/inverted-punctuation sentence
  starts after terminal punctuation, and time-abbreviation boundaries for
  `a.m.` / `p.m.` before clear new sentences.
- Add a dry-run comparison utility that reports sentence-count deltas,
  normalized text coverage, tiny-fragment rate, and max words per segment before
  switching defaults. Status: `compare_sentence_splitter_modes` and
  `scripts/compare_sentence_splitters.py` report regex-vs-modern counts,
  fallback status, normalized coverage, tiny-fragment rate, max segment word
  counts, and active splitter cache/version salts without changing job defaults.

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
- Web Video Dubbing discovery and Download Station handoff coverage under
  `web/src/pages/__tests__/VideoDubbingPage.test.tsx`.
- Apple Download Station job payload/status coverage under
  `scripts/tests/check_apple_creation_payloads.swift`, including review-only
  Newznab/Torznab discovery candidates; simulator compile gates should include
  iPad and tvOS builds after Apple Create source changes.
- Apple Create contract tests for provider list, source handoff, and template
  preservation.
- No physical device deployment unless explicitly requested.

Sentence quality:

- Expand `tests/test_sentence_splitting.py`. Status: focused coverage now pins
  normalized-text preservation for leading bullet markers and Unicode sentence
  starts so refined splitting cannot silently skip or duplicate source text.
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
