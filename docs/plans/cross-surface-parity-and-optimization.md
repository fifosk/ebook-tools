# Cross-Surface Parity And Optimization Plan

Last updated: 2026-07-02

## Goal

Bring ebook-tools toward one coherent experience across Web, iPhone, iPad, and Apple TV while preserving existing behavior:

- Web remains the richest creation and administration surface.
- iPad and iPhone gain attended, native creation flows for practical job types.
- Apple TV stays playback-first, with native creation limited to server/NAS-backed job setup.
- Backend APIs stay reusable, observable, and friendly to simulator/device pipelines.

## Current Surface Inventory

### Web UI

The Web app is a Vite + React + TypeScript app in `web/`.

Key state and shell files:

- `web/src/App.tsx`
- `web/src/components/Sidebar.tsx`
- `web/src/components/app/MainContent.tsx`
- `web/src/stores/jobsStore.ts`
- `web/src/stores/uiStore.ts`

Web-only or Web-primary creation flows:

- Narrate Ebook: `web/src/pages/NewImmersiveBookPage.tsx`, `web/src/components/book-narration/BookNarrationForm.tsx`, submits `/api/pipelines`.
- Generated book: `web/src/pages/CreateBookPage.tsx`, `web/src/api/createBook.ts`, submits `/api/books/jobs`.
- Subtitle job: `web/src/pages/SubtitleToolPage.tsx`, `web/src/api/client/subtitles.ts`, submits `/api/subtitles/jobs`.
- YouTube dubbing: `web/src/pages/VideoDubbingPage.tsx`, `web/src/api/client/subtitles.ts`, submits `/api/subtitles/youtube/dub`.
- Library source upload: `web/src/pages/LibraryPage.tsx`, calls `/api/library/items/{job_id}/upload-source`.

Large Web UI hotspots to split before redesign work:

- `web/src/hooks/useLiveMedia.ts` - 618 lines. Status: live media state
  types, empty-state creation, media bucket merging, generated-file extraction,
  chunk merging, audio-track detection, chunk-sentence detection, scalar
  coercion, media-category normalization, media signature building, relative
  path derivation, and live-media display-name derivation now live
  in `web/src/hooks/liveMediaState.ts`; modern and legacy timing normalization
  now lives in `web/src/hooks/liveMediaTiming.ts` with focused Vitest coverage.
- `web/src/pages/LibraryPage.tsx` - 813 lines. Status: TV/YouTube/library
  title, author, genre, thumbnail, upload-date, ISBN preview merge/cover, and
  tab bucketing and pagination helpers now live in
  `web/src/pages/library/libraryPageMetadata.ts` with focused Vitest coverage.
  Metadata edit submission now also delegates its trimmed payload and changed
  ISBN apply decision to the same tested helper, preserving source upload
  ordering and explicit ISBN clears. Search-result selected-item reconciliation,
  resume job-id extraction, updated-item replacement, remove-selection clearing,
  and row mutating-state cleanup now also live in the tested metadata helper
  module. The details metadata tab presentation now
  lives in `web/src/pages/library/LibraryMetadataTab.tsx`, keeping YouTube and
  timestamp formatting with the shared metadata helpers. The overview tab
  presentation, including cover/TV artwork, play/edit/enrichment actions, ISBN
  preview, and source replacement form, now lives in
  `web/src/pages/library/LibraryOverviewTab.tsx`. Detail tab switching and
  sharing/permission editing now live in `LibraryDetailTabs.tsx` and
  `LibraryPermissionsTab.tsx`.
- `web/src/pages/VideoDubbingPage.tsx` - 574 lines. Status: inline
  subtitle defaulting, playable subtitle filtering, metadata source-name
  resolution, embedded subtitle extractability, voice inventory option
  building, NAS refresh video/subtitle selection, YouTube Dub request payload
  building and clip-offset validation, TV/YouTube metadata draft update and
  preservation helpers, subtitle extraction/availability messages, and
  job-parameter prefill mapping now live in
  `web/src/pages/video-dubbing/videoDubbingUtils.ts` with focused Vitest
  coverage. Video Dubbing discovery provider buttons now derive video-capable
  providers from the backend acquisition registry while preserving the familiar
  NAS, manual download, YouTube search, and Indexers ordering. Video deletion selection fallback now lives there too, preserving
  the current selection when deleting a different video and choosing the next
  default subtitle/language when deleting the selected video. NAS base-dir,
  selected-video, and selected-subtitle persistence now lives in
  `web/src/pages/video-dubbing/useVideoDubbingSelectionState.ts`, restoring
  the last Web NAS source on page load, trimming/clearing local-storage
  values through the shared browser-storage helper, and keeping transient
  discovery-template provenance with the selected source state. Selected video/subtitle
  derivation, playable subtitle filtering, subtitle language metadata, metadata
  source-name fallback, embedded subtitle extractability, and source subtitle
  notice text now live in `web/src/pages/video-dubbing/useVideoDubbingResolvedSelection.ts`
  with focused hook coverage. Video discovery provider
  registry loading, interpretation, stable option ordering, availability
  messaging, and provider-specific candidate filtering now live in
  `web/src/pages/video-dubbing/useVideoDubbingAcquisitionProviders.ts` and
  `web/src/pages/video-dubbing/videoDubbingDiscovery.ts` with focused Vitest
  coverage, keeping the page aligned with the backend registry without inline
  derived-state drift. Discovery provider selection, query state, backend
  video-candidate search, unavailable-source validation, and filtered
  candidate exposure now live in
  `web/src/pages/video-dubbing/useVideoDubbingDiscoverySearch.ts`, while
  `web/src/pages/video-dubbing/useVideoDubbingDiscoveryController.ts` owns
  the page-level provider/default-source coordination so Video Dubbing and
  Apple YouTube Dub keep the same backend-owned default semantics. Both hooks
  have focused coverage. Download Station handoff source/candidate state,
  confirmation validation, submit, and poll lifecycle now live in
  `web/src/pages/video-dubbing/useVideoDubbingDownloadStation.ts` with focused
  hook coverage, and completed-task NAS refresh plus safe completed-file
  matching now lives in
  `web/src/pages/video-dubbing/useVideoDubbingDownloadStationCompletion.ts`.
  Download Station handoff detection, completed-file extraction, and refreshed
  NAS-video matching now live in
  `web/src/pages/video-dubbing/videoDubbingDownloadStationUtils.ts` with
  focused coverage, keeping downloader handoff behavior small enough to compare
  against Apple YouTube Dub.
  The Download Station handoff chrome now lives in
  `web/src/pages/video-dubbing/VideoDownloadStationPanel.tsx` with rendered
  Vitest coverage. Video source-panel discovery placeholders, source hints,
  filename fallbacks, and remote candidate summary labels now live in
  `web/src/pages/video-dubbing/videoSourcePanelUtils.ts` with focused coverage,
  making the Web source-picker behavior easier to compare with Apple YouTube Dub.
  Video Dubbing page feedback, template status/error, and shared intake callout
  rendering now live in `web/src/pages/video-dubbing/VideoDubbingFeedbackPanel.tsx`
  with rendered coverage and changed-test routing, trimming another repeated
  render stack out of the page coordinator.
  Video source discovery provider buttons, query input, status/error rendering,
  candidate selection, and embedded Download Station handoff chrome now live in
  `web/src/pages/video-dubbing/VideoDiscoveryPanel.tsx` with rendered coverage,
  keeping discovery behavior easier to compare with Apple YouTube Dub.
  YouTube Dub generate/save-template action state, intake
  capacity guard, shared payload construction, backend submission, template
  persistence, and discovery-state template preservation now live in
  `web/src/pages/video-dubbing/useVideoDubbingJobActions.ts` with focused hook
  coverage. Saved-template compatibility checks, template field hydration,
  rerun prefill selection/model hydration, pipeline-default application, and
  delayed template metadata draft replacement now live in
  `web/src/pages/video-dubbing/useVideoDubbingCreationTemplate.ts` with focused
  hook coverage. NAS video selection, default subtitle fallback, subtitle
  language synchronization, discovered-source application, YouTube metadata
  handoff, and indexer-to-Download-Station handoff now live in
  `web/src/pages/video-dubbing/useVideoDubbingSourceSelection.ts` with focused
  hook coverage. TVMaze/YouTube metadata
  lookup state, stale-response suppression, source-change resets, cache clear
  handlers, and editable metadata draft preservation now live in
  `web/src/pages/video-dubbing/useVideoDubbingMetadata.ts` with focused hook
  coverage. TVMaze metadata preview artwork, summary rows, editable job/show/episode
  fields, and raw payload rendering now live in
  `web/src/pages/video-dubbing/VideoTvMetadataPreview.tsx` with rendered
  coverage, trimming the metadata panel while preserving the same reviewed
  metadata draft shape that Apple Create consumes. Backend target-language loading, shared language preference
  updates, sorted option construction, subtitle-language fallback, and target
  language-code resolution now live in
  `web/src/pages/video-dubbing/useVideoDubbingLanguageState.ts` with focused
  hook coverage, including a guard against treating a raw subtitle language
  code as an arbitrary catalog label. Voice inventory loading, target-language
  sample synthesis, browser audio cleanup, and preview error handling now live in
  `web/src/pages/video-dubbing/useVideoDubbingVoiceState.ts`, while macOS,
  Piper, gTTS, and bundled target-language voice option construction shares the
  tested `web/src/utils/voiceOptions.ts` helper used by Web Narrate Ebook too,
  with Video Dubbing-specific wrapping in
  `web/src/pages/video-dubbing/videoDubbingVoiceOptions.ts`. Translation model
  inventory loading, model-load error handling, and
  selected translation/transliteration provider/model state now live in
  `web/src/pages/video-dubbing/useVideoDubbingModelState.ts` with focused hook
  coverage. Clip-window, mix, resolution, batch/flush, split/stitch,
  transliteration, lookup-cache, backend-default, and output-prefill state now
  live in `web/src/pages/video-dubbing/useVideoDubbingOutputState.ts` with
  focused hook coverage. Embedded subtitle stream inspection, extraction,
  stream selection, subtitle deletion, and related progress/error state now
  live in `web/src/pages/video-dubbing/useVideoDubbingSubtitleExtraction.ts`
  with focused hook coverage. NAS video library refresh, load errors, local
  video deletion, prefill/current-selection fallback, and post-delete fallback
  selection now live in
  `web/src/pages/video-dubbing/useVideoDubbingLibraryState.ts` with focused hook
  coverage. Refresh/delete target-language coordination now lives in
  `web/src/pages/video-dubbing/useVideoDubbingLibraryActions.ts` with focused
  hook coverage. The YouTube Dub template payload builder reuses the same generated
  request payload and strips sensitive metadata keys before saving through
  `/api/creation/templates`. The repo-owned `test-web-video-dubbing-focused`
  target now runs the full Video Dubbing utility/hook/page slice so the reusable
  Apple pipeline Web gate can keep this split work covered with one stable app
  command; it also covers the YouTube download page search-to-URL handoff.
  Video Dubbing language, voice, translation-provider, and transliteration
  model controls now live in
  `web/src/pages/video-dubbing/VideoDubbingLanguageModelSection.tsx`, keeping
  `VideoDubbingOptionsPanel.tsx` focused on render/output tuning controls.
- `web/src/pages/SubtitleToolPage.tsx` - 409 lines. Status: tab-panel
  rendering now lives in `web/src/pages/subtitle-tool/SubtitleToolTabContent.tsx`
  with focused coverage for tab routing and submit-form preservation. Source ordering,
  latest-source selection, submitted-job summary formatting, and rerun prefill
  snapshot mapping, submit validation/payload normalization, and Web-style
  timecode parsing, metadata source-name resolution, ASS selection detection,
  completed-result fetch selection, job sorting, and backend language-default
  normalization, multipart submit `FormData` construction, and metadata draft
  update helpers now live in `web/src/pages/subtitle-tool/subtitleToolUtils.ts`
  with focused Vitest coverage. TV metadata lookup state, stale response
  suppression, draft editing, and clear behavior now live in
  `web/src/pages/subtitle-tool/useSubtitleTvMetadata.ts` with focused hook
  coverage. Source listing, selected-source preservation, refresh, delete, and
  source message/error state now live in
  `web/src/pages/subtitle-tool/useSubtitleSources.ts` with focused hook coverage.
  Completed subtitle-job result fetching, dedupe, partial-failure tolerance, and
  late-response cancellation now live in
  `web/src/pages/subtitle-tool/useSubtitleJobResults.ts` with focused hook
  coverage. Model-option loading, empty responses, failed fetches, and
  late-response cancellation now live in
  `web/src/pages/subtitle-tool/useSubtitleModels.ts` with focused hook
  coverage. Backend language-default loading, default input-language application,
  failure logging, and stale-response protection now live in
  `web/src/pages/subtitle-tool/useSubtitleLanguageDefaults.ts` with focused
  hook coverage. Backend creation-default loading, skip-on-prefill/template
  behavior, failure logging, and late-response cancellation now live in
  `web/src/pages/subtitle-tool/useSubtitleCreationDefaults.ts` with focused
  hook coverage. Show-original subtitle preference loading and persistence now
  live in `web/src/pages/subtitle-tool/useSubtitleShowOriginalPreference.ts`
  with focused local-storage failure coverage. Rerun/prefill parameter
  application now lives in `web/src/pages/subtitle-tool/useSubtitlePrefill.ts`
  with focused hook coverage. Saved-template handoff application, incompatible
  template reporting, and delayed metadata-draft replacement now live in
  `web/src/pages/subtitle-tool/useSubtitleCreationTemplate.ts` with focused
  hook coverage. Subtitle template-save validation, sanitized payload
  submission, and save status/error state now live in
  `web/src/pages/subtitle-tool/useSubtitleTemplateActions.ts` with focused
  hook coverage. Shared language preferences, backend
  target-language options, sorted dropdown options, and input/target handlers
  now live in `web/src/pages/subtitle-tool/useSubtitleLanguageState.ts` with
  focused hook coverage.
  Source-list refresh selection also stays pinned in the utility module, clearing
  stale selections after deletes and choosing the latest usable subtitle source
  when needed. The subtitle template payload builder mirrors resolved submit
  field names and strips sensitive metadata keys before saving through
  `/api/creation/templates`. The repo-owned `test-web-subtitle-tool-focused`
  target now runs the full Subtitle Tool render utility/hook slice so the reusable
  Apple pipeline Web gate can keep this split work covered with one stable app
  command.
- `web/src/components/video-subtitles/SubtitleTrackOverlay.tsx` - 456 lines.
  Status: subtitle cue lookup, token navigation, selection shadowing, clamp
  math, track variant mapping, and TTS voice option helpers now live in
  `web/src/components/video-subtitles/subtitleTrackOverlayUtils.ts` with
  focused Vitest coverage. MyLinguist bubble rendering and docked/floating
  portal ownership now lives in
  `web/src/components/video-subtitles/SubtitleLinguistBubblePortal.tsx` with
  rendered coverage for disabled, floating, and docked portal states in the
  focused Web playback gate. Subtitle track row/token rendering now lives in
  `web/src/components/video-subtitles/SubtitleTrackRows.tsx` with rendered
  coverage for playback current/past state, paused selection, shadowed
  translation/transliteration tokens, and activation routing. ASS subtitle
  deferred loading, data-URL decoding, remote fetch parsing, disabled-state
  resets, and failure fallback now live in
  `web/src/components/video-subtitles/useAssSubtitleCues.ts` with focused hook
  coverage. Active cue index, playback state observation, seek/timeupdate
  handling, animation-frame cleanup, and explicit cue commits now live in
  `web/src/components/video-subtitles/useAssSubtitlePlaybackState.ts` with
  focused hook coverage. Visible track filtering, paused/playback token
  selection, selection clamping, and translation/transliteration shadow pairing
  now live in `web/src/components/video-subtitles/useSubtitleTrackSelection.ts`
  with focused hook coverage. Global Enter/Left/Right subtitle cue keyboard
  navigation now lives in
  `web/src/components/video-subtitles/useSubtitleCueKeyboardNavigation.ts` with
  focused hook coverage. Subtitle vertical drag offset, local-storage
  persistence, clamping, and post-drag click suppression now live in
  `web/src/components/video-subtitles/useSubtitleOverlayDrag.ts` with focused
  hook coverage. Subtitle token DOM line-map rebuilding, click activation,
  paused token arrow navigation, Enter lookup fallback, and resize-driven map
  refresh now live in `web/src/components/video-subtitles/useSubtitleTokenNavigation.ts`
  with focused hook coverage.
- `web/src/components/JobProgress.tsx` - 496 lines. Status: generated-file
  stat lookup, batch progress, sentence/playable stage progress,
  lookup-cache progress, parallelism overview entries, fallback display rows,
  unavailable-translation detection, metadata entry splitting, narrated
  subtitle detection, and progress label helpers now live in
  `web/src/components/job-progress/jobProgressUtils.ts` with focused Vitest
  coverage. OpenLibrary metadata lookup query state, success/error handling,
  backend cache clearing, and reload side effects now live in
  `web/src/components/job-progress/useJobProgressMetadataLookup.ts` with
  focused hook coverage. Job detail tabs and permission editing chrome now live
  in `JobProgressTabs.tsx` and `JobProgressPermissionsSection.tsx`. Header
  status/action chrome now lives in `JobProgressHeader.tsx`, and stage-progress
  presentation now lives in `JobProgressStageSection.tsx`. Latest progress
  metrics now live in `JobProgressLatestSection.tsx`. Metadata tab cover,
  lookup, display rows, technical rows, and reload action now live in
  `JobProgressMetadataSection.tsx`. Overview tab parameters, image-cluster
  status, notices, batch stats, parallelism, tuning, and fallback sections now
  live in `JobProgressOverviewSection.tsx`. Job lifecycle timing summary now
  lives in `JobProgressTimingSummary.tsx`, and the compact active-stage health
  row lives in `JobProgressHealthSummary.tsx`. The repo-owned
  `test-web-job-progress-focused` target covers the JobProgress component,
  job settings summary rows, stage label formatting, and shared job-progress
  utilities.
- `web/src/components/LibraryList.tsx` - 624 lines. Status: layout type
  detection, title/author/genre fallback labels, and author/genre/language
  grouping now live in `web/src/components/library-list/libraryListUtils.ts`
  with focused Vitest coverage. Book summary, TV/episode metadata, subtitle
  genre/summary/image, YouTube metadata, source-badge, and media asset URL
  resolvers now live in `web/src/components/library-list/libraryListMediaUtils.ts`
  with focused Vitest coverage. Permission defaults, export readiness, and
  disabled action-state rules now live in
  `web/src/components/library-list/libraryListActions.ts` with focused Vitest
  coverage. Reusable row/card action buttons now live in
  `web/src/components/library-list/LibraryItemActions.tsx` with focused
  rendered coverage. Library item status badges now live in
  `web/src/components/library-list/LibraryStatusBadge.tsx` with focused
  rendered coverage.
- `web/src/components/PlayerPanel.tsx` - 858 lines. Status: selected text
  item, selected chunk, and active text chunk resolution now live in
  `web/src/components/player-panel/utils.ts` with focused Vitest coverage.
  Browser storage reads/writes used by PlayerPanel, interactive text, reading
  bed, media memory, and bookmarks now route through
  `web/src/utils/browserStorage.ts` with focused Vitest coverage. Media-session
  seek/track skip handling, keyboard navigation, and registered sentence
  sequence skipping now live in
  `web/src/components/player-panel/usePlayerPanelMediaNavigation.ts` with
  focused hook coverage; its diagnostic breadcrumbs are opt-in during
  development so normal dogfood playback and automation stay quiet. Panel/fullscreen
  navigation control variants now live in
  `web/src/components/player-panel/PlayerPanelNavigationGroups.tsx` with
  focused prop-routing coverage. Navigation controls shell state now lives in
  `web/src/components/player-panel/navigationControlsState.ts` with focused
  coverage for class names, search placement, export labels, advanced toggle
  state, and compact controls. Player content empty/stage wrapper now lives
  in `web/src/components/player-panel/PlayerPanelContent.tsx` with focused
  rendered coverage. Boundary states for load errors, initial loading, and no
  selected job now live in `web/src/components/player-panel/PlayerPanelBoundaryState.tsx`
  with focused rendered coverage. Sentence-jump datalist rendering now lives in
  `web/src/components/player-panel/PlayerPanelSentenceJumpDatalist.tsx` with
  focused rendered coverage. Compact search panel visibility now lives in
  `web/src/components/player-panel/PlayerPanelSearchSlot.tsx` with focused
  rendered coverage for panel and fullscreen placement. Chapter active-id and
  jump-target resolution now live in
  `web/src/components/player-panel/chapterNavigation.ts` with focused utility
  coverage, and the React bridge for active chapter state
  plus chapter jump dispatch now lives in
  `web/src/components/player-panel/usePlayerPanelChapterNavigation.ts` with
  focused hook coverage. Navigation base prop shaping, including the shared
  sleep-timer slot, now lives in
  `web/src/components/player-panel/playerPanelProps.ts` with focused prop
  coverage. Generated sentence-jump IDs, panel advanced-controls state, and
  panel/fullscreen navigation assembly now live in
  `web/src/components/player-panel/usePlayerPanelNavigationChrome.tsx` with
  focused hook coverage. The repo-owned `test-web-playback-focused`
  target now covers live-media state/timing, PlayerPanel helper/rendering
  splits, shared video and YouTube Dub sleep-timer behavior, subtitle overlay
  utilities, audio URL/chunk indexing, sequence planning, and browser-storage
  persistence so the reusable Apple pipeline Web gate can catch playback
  regressions alongside Create and Library work.
- `web/src/components/Sidebar.tsx` - 100 lines. Status: pipeline-view
  detection, sidebar language/label/status/stage/glyph/progress resolution,
  and image-wait status now live in
  `web/src/components/sidebar/sidebarUtils.ts` with focused Vitest coverage.
  Reusable job overview row rendering now lives in
  `web/src/components/sidebar/SidebarJobRow.tsx` with focused rendered coverage.
  Active-player entry rendering now lives in
  `web/src/components/sidebar/SidebarPlayerButton.tsx` with focused rendered
  coverage. Creation navigation for Narrate Ebook, generated books, subtitles,
  YouTube source review, and video dubbing now lives in
  `web/src/components/sidebar/SidebarCreationLinks.tsx` with focused rendered
  coverage. Admin navigation and observability links now live in
  `web/src/components/sidebar/SidebarAdminLinks.tsx` with focused rendered
  coverage. The repo-owned `test-web-admin-focused` target now covers
  user-management, system status/restart controls, and admin/observability
  navigation so the shared Apple Web manifest catches admin shell regressions
  before full Vitest. Job overview bucketing and section rendering now live in
  `web/src/components/sidebar/SidebarJobOverview.tsx` with focused rendered
  coverage. The repo-owned `test-web-sidebar-focused` target now runs the root
  Sidebar, player entry, creation links, job overview/row, and sidebar utility
  tests so the reusable Web pipeline covers the split navigation shell directly.
- `web/src/components/book-narration/BookNarrationForm.tsx` - 540 lines.
  Status: server EPUB discovery, generated-source skips, latest-book default
  selection, upload validation, and history-derived start defaults now have
  focused hook coverage through `useBookNarrationFiles.ts`, and the repo-owned
  `test-web-create-intake-focused` target runs that slice with the broader
  Create intake form coverage. Backend voice inventory matching, region/base
  language-code normalization, per-language preview overrides, and inventory
  load failures now have focused hook coverage through `useBookNarrationVoices.ts`.
  Backend content-index chapter loading, generated-source skips, consecutive
  chapter selection, backend error surfacing, and estimated range/duration
  labels now have focused hook coverage through `useBookNarrationChapters.ts`.
  Narrate Ebook discovery-provider fallback ordering, backend discovery-media
  kind filtering, availability messaging, and backend-owned default selection
  now live in `bookNarrationDiscoveryProviders.ts` with direct Vitest coverage
  registered in `test-web-create-intake-focused`. Discovery-backed template
  extras, including selected provenance and sparse provider/query drafts before
  candidate selection, plus saved-template payload creation and save
  success/error mapping, and template clear/skip/incompatible/apply decisions
  now resolve in `bookNarrationTemplates.ts` with focused coverage so Web/Apple
  template handoffs keep matching.
  Apple Create source-pane and wide job-settings-pane chapter controls now share
  `AppleBookCreateNarrateChapterRangeControls`, and both resolve selected server
  EPUB details through `AppleBookCreatePresentation.selectedPipelineEbook`, so
  Load Chapters, picker state, selected-book context, range summaries, and
  sentence-window updates stay consistent across iPad, iPhone, Apple TV, and
  local Mac Designed for iPad layouts.
  Recent-job path normalization, resume-window
  inference, latest
  input/base selection, latest language/lookup-cache defaults, prefilled
  input-file state mapping, and rerun prefill state mapping, initial shared
  language/lookup-cache form defaults,
  shared language/lookup-cache preference update resolution, section metadata
  merging, edited-field preservation,
  submit-requirement resolution, backend image-default merging, and edited
  image-default restoration, generated-source sentence-bound resets, forced
  output-name application, generic field update identity preservation,
  field-change side-effect classification,
  saved-template form-state normalization/application, plus default-settings
  compaction, manual/selected target-language resolution, and target-language
  normalization now live in
  `web/src/components/book-narration/bookNarrationFormUtils.ts` with focused
  Vitest coverage. Narration voice override language derivation and voice
  override edit mutation now also live in that utility module, keeping source/
  target language trimming, catalog-code dedupe, uncataloged-label preservation,
  and add/update/delete/no-op override behavior pinned outside the form
  coordinator. Normalized input metadata-cache keys and merged target-language
  state now live in `useBookNarrationNormalizedState.ts` with focused hook
  coverage. Mutable workflow refs for prefill/template/default sentinels plus
  user-edited-field preservation now live in `useBookNarrationWorkflowRefs.ts`
  with focused hook coverage. Static audio/written/voice option lists now pass from their
  module-level constants instead of being re-memoized inside the coordinator.
  Submit/header presentation state, including missing requirements, capacity
  disabled state, and fallback labels, now resolves through the same tested
  helper instead of inline form render code. Pipeline step tabs and submit action rendering now live in
  `web/src/components/book-narration/BookNarrationStepBar.tsx` with focused
  rendered coverage. Intake, missing-requirement, and submit-error messaging now
  live in `web/src/components/book-narration/BookNarrationSubmitStatus.tsx`
  with focused rendered coverage. Ebook/output file selection dialog routing now
  lives in `web/src/components/book-narration/BookNarrationFileDialog.tsx` with
  focused rendered coverage. Book discovery template state construction now
  lives in `web/src/components/book-narration/bookNarrationTemplates.ts`, keeping
  candidate-to-template payload shape and selected-path retention/clearing
  behavior covered outside the form coordinator. The
  repo-owned `test-web-create-intake-focused`
  target now runs those rendered component tests with the narration form and
  intake utility slices, so the shared Web pipeline covers the split Create
  shell before full Vitest. File and discovery dialog wiring now lives in
  `web/src/components/book-narration/BookNarrationFormDialogs.tsx`, keeping
  modal selection, deletion, and search routing covered outside the form
  coordinator. Discovery candidate selection now routes through a
  named form callback rather than inline JSX, keeping the local/acquire/archive
  bridge and metadata-only handoff easier to compare with the Apple Create
  picker flow. Discovery response candidate filtering, including backend-default
  source filtering, now lives in `useBookNarrationDiscovery.ts` with focused
  hook coverage. Active Create tab initialization, external active-section sync,
  parent callback forwarding, default tab sections, and section metadata
  override merging now live in
  `web/src/components/book-narration/useBookNarrationSectionState.ts` with
  focused hook coverage, matching the rest of the form's delegated state
  ownership. Saved-template application lifecycle now lives in
  `web/src/components/book-narration/useBookNarrationTemplateApply.ts`, keeping
  compatibility errors, applied status, discovery panel selection, edited-field
  markers, and shared language preference sync covered outside the large form
  coordinator. Form editing callbacks now live in
  `web/src/components/book-narration/useBookNarrationFormEditing.ts`, keeping
  ordinary field-change side effects, shared language preference sync,
  image-default edit markers, voice override edits, and override-language
  derivation under focused hook coverage. Prefilled input-file and rerun
  parameter application now live in
  `web/src/components/book-narration/useBookNarrationPrefill.ts`, keeping cached
  metadata hydration, history-derived starts, duplicate prefill suppression,
  and edited-field preservation covered outside the coordinator. Generated-source
  sentence-bound resets and forced output-name enforcement now live in
  `web/src/components/book-narration/useBookNarrationSourceDefaults.ts`, keeping
  source/output defaulting under focused hook coverage while trimming the
  coordinator smaller. Discovery candidate selection and its token-safe
  template provenance now live in
  `web/src/components/book-narration/useBookNarrationDiscoverySelection.ts`,
  keeping local/acquire/archive bridge and metadata-only handoff behavior under
  focused hook coverage. Recent-job history callbacks now live in
  `web/src/components/book-narration/useBookNarrationHistory.ts`, keeping path
  normalization, previous-start lookup, and latest-job defaults under focused
  hook coverage. Backend image-default application now lives in
  `web/src/components/book-narration/useBookNarrationImageDefaults.ts`, keeping
  edited image fields and rerun `add_images` preservation under focused hook
  coverage. Draw Things node availability polling, fallback-node labeling, and
  selected-node ordering now live in
  `web/src/components/book-narration/useBookNarrationImageNodeAvailability.ts`
  with focused hook coverage, keeping the image generation controls lighter for
  Apple Create parity comparisons. Image style and prompt-pipeline option
  catalogs, quality-to-step mapping, duration formatting, and image throughput
  estimates now live in
  `web/src/components/book-narration/bookNarrationImageSettings.ts` with
  focused utility coverage, giving Apple Create a smaller settings contract to
  mirror. Submit orchestration now lives in
  `web/src/components/book-narration/useBookNarrationSubmitFlow.ts`, keeping
  pipeline submit, intake refresh, and submit-button presentation under focused
  hook coverage while trimming the coordinator to 540 lines.

### Apple Apps

Apple currently focuses on auth, browse, playback, offline sync, bookmarks, and settings.

Key Apple files:

- Shell/browse: `ios/InteractiveReader/InteractiveReader/Features/Library/LibraryShellView.swift`
- Jobs list: `ios/InteractiveReader/InteractiveReader/Features/Jobs/JobsView.swift`
- API transport: `ios/InteractiveReader/InteractiveReader/Services/APIClient.swift`
- Job/library API methods: `ios/InteractiveReader/InteractiveReader/Services/APIClient+LibraryJobs.swift`
- Media API methods: `ios/InteractiveReader/InteractiveReader/Services/APIClient+PipelineMedia.swift`

Current Apple API client supports:

- Fetch library items via `/api/library/items`.
- Fetch jobs via `/api/pipelines/jobs`.
- Fetch job status via `/api/pipelines/{job_id}`.
- Delete jobs, delete library items, move jobs to Library.
- Fetch media/timing for jobs and library entries.
- Fetch book creation options via `/api/books/options`.
- Submit pipeline jobs via `/api/pipelines`.
- Upload EPUB files via `/api/pipelines/files/upload`.
- Submit generated book jobs via `/api/books/jobs`.
- Submit subtitle jobs via `/api/subtitles/jobs`.
- Submit YouTube dubbing jobs via `/api/subtitles/youtube/dub`.

Current Apple UI partially exposes:

- Native Create flow. Status: `AppleBookCreateView.swift` now delegates create
  mode availability, submit-button presentation, base-output derivation,
  subtitle model labels, subtitle model option-list construction, ASS/subtitle/
  YouTube clamp and formatting helpers, YouTube offset normalization, draft
  construction, backend default resolution, backend language/voice option
  building, source selection, and routing to focused `AppleBookCreate*`
  presentation/helper files. Create draft value types, shared language models,
  and history/default structs now live in `AppleBookCreateModels.swift`, while
  mode, submit-state, tuning, format, and provider options live in
  `AppleBookCreateOptions.swift`, and job-history payload parsing
  lives in `AppleBookCreateHistoryParsing.swift`; subtitle and YouTube request
  body builders live in `AppleBookCreateMediaPayloads.swift`, keeping the
  support file as a thin namespace and the view model focused on submission
  work. Subtitle and YouTube output control subviews live in
  `AppleBookCreateOutputControls.swift`; generated-book output controls live
  in `AppleBookCreateGeneratedOutputControls.swift`, while generated-book
  image controls live in `AppleBookCreateGeneratedImageControls.swift`.
  Reusable Create value controls live in `AppleBookCreateValueControls.swift`,
  while clamped output values and reusable state adapters live in
  `AppleBookCreateControlBindings.swift`, letting
  `AppleBookCreateOutputSection.swift` own only section-level routing,
  while shared source action rows in `AppleBookCreateSourceControls.swift`
  keep EPUB, subtitle, and NAS video refresh/extract controls consistent through
  the shared busy action button in `AppleBookCreateMetadataViews.swift`.
  Media metadata controls live in `AppleBookCreateMediaMetadataControls.swift`,
  while `AppleBookCreateMediaMetadataSections.swift` owns the metadata section
  routing, and YouTube/subtitle metadata JSON binding adapters now live in
  `AppleBookCreateMetadataBindings.swift`. Advanced metadata JSON editing, artwork preview, status, and action
  subviews now live in `AppleBookCreateMetadataViews.swift`, trimming repeated metadata UI while
  preserving the tvOS-safe JSON editor fallback. Submit and template-save now
  share the same current draft builders so video discovery metadata remains
  aligned between direct YouTube Dub jobs and saved templates. Metadata JSON parsing/formatting
  helpers now live in `AppleBookCreateMetadataJSON.swift`, and subtitle/YouTube
  metadata lookup, cache clearing, and draft-editing actions now live in
  `AppleBookCreateViewModel+Metadata.swift`. The Create view's metadata, voice
  preview, image-node check, and retry action wrappers now live in
  `AppleBookCreateMetadataActions.swift`. Derived Create picker inventories,
  model lists, formatted tuning labels, and audio-duration estimates now live in
  `AppleBookCreateDerivedState.swift`. Source inventory, acquisition,
  Download Station, server EPUB/subtitle mutation, NAS video subtitle extraction,
  and chapter-loading view-model actions now live in
  `AppleBookCreateViewModel+Sources.swift`. Saved-template load/save/delete
  view-model actions now live in `AppleBookCreateViewModel+Templates.swift`.
  EPUB/subtitle file
  import normalization and local import selection plans now live in
  `AppleBookCreateFileImport.swift`, metadata lookup
  source-name derivation now lives in `AppleBookCreateMetadataSources.swift`,
  and Create persistence key construction now lives in
  `AppleBookCreateStorageKeys.swift`, keeping API/user-scoped local file, lookup, and
  UserDefaults formats contract-pinned outside the main view. YouTube NAS
  base-dir/selection and subtitle show-original preference reads/writes now
  live in `AppleBookCreatePreferences.swift`, as do shared language and
  lookup-cache preference JSON reads/writes, while the view's scoped load-key
  bridge lives with `AppleBookCreateLifecycle.swift`; scoped trimming, removal,
  and codec behavior stay contract-pinned outside the main view. Create lifecycle
  loading, field-change, and section callback side effects are now named
  handlers in the view instead of inline modifier/section bodies, and
  source-section construction now lives in `AppleBookCreateSourceSectionFactory.swift`
  so the main Create screen only chooses the setup pane entry while the factory
  wires source picker state and callbacks.
  successful job submission completion shares one intake-refresh/notify handler
  while the view model shares one submit-state/error wrapper in
  `AppleBookCreateViewModel+Submission.swift`.
  iOS document importer modifier wiring for local EPUB/subtitle selection now
  lives in `AppleBookCreateFileImporterModifier.swift`, keeping platform
  document-picker modifiers out of the main Create view while preserving the
  same iPad/iPhone import handlers. Local EPUB/subtitle import result handling
  and server EPUB upload handoff now live in
  `AppleBookCreateFileImportActions.swift`, while pure import normalization
  remains in `AppleBookCreateFileImport.swift`. Saved-template refresh, save,
  apply, and delete orchestration now lives in
  `AppleBookCreateTemplateActions.swift`, while detailed Web-template
  application across generated-book, Narrate EPUB, subtitle, and YouTube Dub
  settings now lives in `AppleBookCreateTemplateApplicationActions.swift`.
  Narration language/voice routing now lives in
  `AppleBookCreateNarrationSection.swift`, and the
  iOS/iPad searchable full-language selector lives in
  `AppleBookCreateLanguageSelector.swift`. Source section routing lives in
  `AppleBookCreateSourceSection.swift`, while Narrate EPUB server-source,
  subtitle source, local-import, and chapter-range controls live in
  `AppleBookCreateSourceControls.swift`, and NAS YouTube video/subtitle plus
  embedded subtitle extraction controls live in
  `AppleBookCreateYoutubeSourceControls.swift`. Reusable default source selection
  decisions, including NAS YouTube scope refreshes, live in
  `AppleBookCreateSourceSelection.swift`, while source refresh, delete,
  discovery-application, Download Station, and chapter-load side effects now
  live in `AppleBookCreateSourceActions.swift`. Shared/default and book
  acquisition discovery metadata shaping now lives in
  `AppleBookCreateDiscoveryPresentation.swift`, while video discovery
  availability, provider options, candidate filtering, YouTube/NAS labels, and
  template discovery-state shaping live in
  `AppleBookCreateVideoDiscoveryPresentation.swift`; source-selection actions
  stay focused on applying paths and reviewed metadata. Subtitle time-range and YouTube
  offset-range validation now use pure support helpers that preserve the
  existing visible error messages. Backend default resolution and edited-field
  preservation now live in support too, so backend-driven Apple Create defaults
  stay pinned outside the SwiftUI state assignment code. Saved-template payload
  parsing now lives in `AppleBookCreateTemplateSettings.swift`, keeping Web
  form-state extraction, stringified metadata JSON, voice overrides, loose
  booleans/numbers, open end-sentence handling, native mode filtering, and
  discovery-state application out of the main SwiftUI Create view; template
  book metadata key precedence, generated-book source context parsing, book
  language resolution, saved voice/voice-override parsing, narration audio,
  book translation/lookup-cache, output format, generated image settings, and
  worker-count parsing live there too. Subtitle and YouTube Dub template
  source/language/timing/output/model/tuning parsing also lives there, and
  source-path fallbacks stay alongside the YouTube path helpers, leaving the
  view to apply resolved state.
  Web handoff template-id compatibility checks, picker display filtering, and
  refresh/delete fallback selection now live there too.
  Apple-saved Web-compatible template
  serialization lives separately in
  `AppleBookCreateTemplateSavePayloadFactory.swift`, so read/apply and
  save/write contracts can evolve without crowding one helper. Backend language and voice inventory option
  building is also centralized in support, including per-target-language voice
  override option maps, preserving selected voices that are absent from backend
  inventory. The Apple journey runner can now
  select Create picker options and assert non-empty field values, with opt-in
  iPhone/iPad Create-readiness Make targets that verify Narrate EPUB, subtitle,
  and YouTube/NAS default source loading against a populated API. The shared
  Create-readiness journey now also scrolls through generated-book output,
  subtitle processing, and YouTube dubbing settings controls after those
  defaults load, so unattended simulator checks prove the practical default
  settings are reachable across the native Create modes.
  The journey runner now has a reusable `tap` action with optional
  `unless_visible` guarding, allowing the native Create readiness journey to
  reveal generated-book illustration settings and assert the image-node
  availability action without depending on a particular backend default.
  Apple Narrate EPUB source selection now shares one tolerant server-EPUB
  candidate helper between picker display and newest-book defaults, preserving
  backend-visible `.epub` entries even when a source response has older or
  incomplete file-type metadata. Explicit Apple Narrate EPUB source changes now
  also refresh the auto-derived output/job name when the previous name still
  matches the earlier selected EPUB, while preserving manually edited output
  names.
  Create lifecycle side-effect wiring now lives in
  `AppleBookCreateLifecycle.swift`, keeping task/on-change handlers and EPUB/
  subtitle delete confirmations target-wired outside the main Create view.
  API/user-scoped Create preference wiring now flows through
  `AppleBookCreatePreferenceScope`, so YouTube base-dir/selection, subtitle
  show-original, shared language preferences, and YouTube library cache keys use
  one reusable scoped wrapper instead of raw preference calls in the main view.
  Create presentation-state wiring, including submit eligibility, compatible
  template picker state, Web Create handoff URLs, derived output names, metadata
  source labels, and tvOS mode availability, now lives in
  `AppleBookCreatePresentationState.swift` so the main view stays closer to
  section composition and named side-effect handlers. Create submit actions for
  generated-book, Narrate EPUB, subtitle, and YouTube Dub jobs now live in
  `AppleBookCreateSubmissionActions.swift`, while generated-book, Narrate EPUB,
  subtitle, and YouTube Dub state-to-draft builders now live in
  `AppleBookCreateDraftActions.swift`; the main view keeps the shared section
  state and view-model submission wrapper. Recent-job
  history default application for generated-book, Narrate EPUB, subtitle, and
  YouTube Dub modes now lives in `AppleBookCreateHistoryDefaultActions.swift`,
  preserving edited-field guards while keeping the main view closer to section
  composition. Backend creation-option loading, stored language preference
  application, backend default assignment, sentence bounds, and sentence-count
  clamping now live in `AppleBookCreateCreationOptionsActions.swift`, keeping
  runtime defaults and state mutation outside the main Create layout file.
  Apple Create language controls are now contract-pinned to the shared
  backend/Web language catalog, so iPhone/iPad searchable selectors and tvOS
  pickers keep the full Web-supported language list even when runtime defaults
  or older option responses are sparse. Apple YouTube Dub discovery provider
  choices now also come from the shared acquisition registry with the same
  NAS/manual/YouTube/indexer fallback ordering as Web Video Dubbing. Web and
  Apple Create also adopt backend-owned default book/video discovery providers
  for their initial picker choices while preserving manual provider changes,
  and both surfaces now skip unavailable backend-default providers when another
  advertised default is available. Web and Apple book discovery also honor
  `default_eligible_media_kinds` before offering the synthetic Default sources
  provider, so video-only or explicit-only defaults cannot bleed into Narrate
  EPUB picker behavior. Default-source video discovery now keeps local
  NAS/manual candidates when optional remote providers fail, carrying a
  token-safe provider note through the shared response instead of emptying the
  picker; Web Video Dubbing and Apple Create now render those response policy
  notes beside the remaining discovery candidates so partial remote-provider
  failures are visible without blocking local/manual selection. Apple Create also reapplies the current backend default if the
  provider inventory changes before a user manually chooses a source, preventing
  stale picker ids from surviving readiness reloads.
  Video discovery availability, unavailable-provider messaging, book/video provider
  fallback ordering, capability filtering, display labels, candidate filtering,
  detail/action labels, YouTube/NAS subtitle labels, and video discovery empty/
  search copy now live in `AppleBookCreateDiscoveryPresentation.swift`,
  keeping provider-id/status formatting and Web-aligned source ordering out of
  the main Create view and source-control SwiftUI views while preserving the
  same Apple TV, iPad, and iPhone controls. The `check_apple_creation_payloads`
  Swift contract now also asserts provider ordering/defaults, availability copy,
  and book/video discovery candidate filtering/actions so acquisition changes
  fail before simulator or device runs drift. Download Station completed-file
  matching now lives in `AppleBookCreateDownloadStationPresentation.swift`, so
  the main Create view only polls and applies the selected manual-download
  candidate while the focused helper handles top-level `completed_files`, older
  metadata fallback hints, handoff detection, and refreshed discovery candidate
  matching. Backend Open Library discovery path/book-key/URL normalization plus
  metadata-only candidate construction and media-metadata lookup payload shaping
  now live in `modules/services/acquisition/openlibrary_discovery.py` with focused
  coverage, keeping book handoff helpers small for Web Narrate Ebook and Apple
  Create. Backend Internet Archive discovery query construction, search/source-id
  provider calls, EPUB candidate construction, download URL shaping, metadata
  fetch, and rights helpers now live in
  `modules/services/acquisition/internet_archive_discovery.py` with focused
  coverage, keeping public-catalog EPUB acquisition rules small and reusable for
  Web/Apple book discovery. Backend Project Gutenberg discovery search-parameter,
  EPUB/HTML URL, and contributor helpers now live in
  `modules/services/acquisition/gutenberg_discovery.py` with focused coverage,
  and the same helper now owns Gutendex API calls plus public-domain candidate
  construction, keeping Gutenberg behavior reusable for Web/Apple book
  discovery without reopening the shared provider fanout. Backend acquisition
  provider discoverability now lives in
  `modules/services/acquisition/provider_catalog.py`, so discovery routing and
  the provider registry share provider/media-kind support without making
  handlers depend on provider payload assembly. Backend acquisition
  discovery now dispatches provider calls through a registry-aligned routing
  table with direct coverage, keeping Web/Apple-visible provider metadata in
  lockstep with backend handlers. Default sources readiness now lives in
  `modules/services/acquisition/provider_defaults.py` with focused coverage,
  keeping default book/video fanout policy reusable outside the provider
  registry payload builder. Provider readiness also resolves manual-download
  roots through one helper that keeps NAS video roots available for explicit
  manual discovery compatibility while excluding them from explicit
  manual-download default fallback policy, preserving Web/Apple default-source
  semantics. Provider source-root resolution now lives in
  `modules/services/acquisition/provider_roots.py`, keeping books root, NAS
  video root, manual-download config/env splitting, source labels, and
  tolerant safe-stat readability checks reusable outside the provider registry
  payload builder. File-backed discovery, reviewed artifact preparation, and
  Download Station handoff now import those root helpers directly instead of
  depending on provider payload assembly. Backend local/manual/NAS source candidate helpers now live in
  `modules/services/acquisition/source_candidates.py` with focused coverage,
  keeping source-relative paths, display-title derivation, zero-byte EPUB
  filtering, and bounded newest-first manual source ordering shared for
  Web/Apple book and video pickers. Backend acquisition value coercion and
  identifier sanitization now live in
  `modules/services/acquisition/discovery_values.py` with focused coverage,
  keeping string/sequence/int parsing and token-safe ids shared across public
  catalog and video providers. Backend acquisition request normalization now
  lives in `modules/services/acquisition/discovery_normalization.py`, and
  Internet Archive source-id validation/deduping lives with the Internet Archive
  helper, keeping media kind, provider, query, limit, language, and archive
  source filters out of the large shared discovery fanout. Backend discovery
  result models now live in `modules/services/acquisition/models.py` and remain
  re-exported from the package root plus the discovery module, so follow-up
  provider helpers can construct shared Web/Apple candidate contracts without
  importing the orchestration fanout. File-backed local EPUB, manual download,
  and NAS video discovery now lives in
  `modules/services/acquisition/file_sources.py`, keeping filesystem scanning,
  subtitle-hint candidate shaping, and newest-first candidate trimming reusable
  outside the large discovery orchestrator. Apple YouTube Dub candidate selection now also
  passes the active discovery provider and query into saved `discovery_state`,
  and applying a saved template restores that provider/query in the native
  source picker, keeping Apple-saved video templates aligned with Web Video
  Dubbing handoffs.
  `scripts/generate_language_catalogs.py`
  now regenerates the shared assets language list plus the Web and Apple catalog blocks from
  `modules/language_constants.py`, and the Apple contract gate runs the
  generator in `--check` mode so future language additions fail fast if a
  surface drifts. The iPad regular-width Create layout now
  keeps the left setup pane source-only and moves Book, Metadata, Job Settings,
  Narration, Output, status, and submit controls into the right-side settings
  pane so creation settings use the detail area instead of reading like sidebar
  content; the reusable Create container shell, list/form chrome, and
  regular-width split layout now live in `AppleBookCreateLayout.swift`. Create status and submit sections now live in
  `AppleBookCreateStatusViews.swift`, keeping loading, intake, success, Web
  handoff, and submit-button UI target-wired outside the main Create view.
- Interactive playback chunk metadata retry. Status: Apple transcript playback
  now records retryable selected-chunk metadata failures, clears them on
  success or job reload, and shows a native transcript Retry action that
  reloads metadata and prepares audio again on iPhone, iPad, Apple TV, and the
  local Mac Designed for iPad surface. The repo-owned Apple contract lane
  includes `tests/test_apple_chunk_metadata_retry_contract.py` so future
  playback refactors keep the retry path wired.
- Interactive playback timing-token sanitization. Status: Apple context
  building now validates global and chunk-level word timing tokens before they
  reach transcript highlighting, dropping non-finite or zero-length windows and
  clamping overlaps within each sentence/file group while preserving the
  existing whitespace token fallback for sparse metadata. The repo-owned Apple
  contract lane includes `tests/test_apple_timing_token_sanitization_contract.py`.
- Interactive playback stream recovery. Status: Apple primary narration now
  retries one failed AVPlayer stream at the current file/time position, keeps
  multi-file timeline state intact when rebuilding a queue, and removes stall
  observers during player teardown so repeated rebuilds do not duplicate
  recovery callbacks. The repo-owned Apple contract lane includes
  `tests/test_apple_audio_stream_recovery_contract.py`.
- Apple Music reading-bed play intent. Status: Apple Music used as the reading
  bed now treats external pauses as manual pause intent and gates every
  app-driven auto-resume path, including sentence switches, source switching,
  and the Background Music toggle, on narration playback still being requested
  plus a dedicated MusicKit auto-resume intent that user-facing MusicKit pauses
  clear. The guard intentionally no longer waits for `audioCoordinator.isPlaying`
  because first sentence starts and sequence track switches can publish the
  playback request before AVPlayer reports active playback. Sentence switches
  still cannot revive a paused Apple Music track just because a queue entry
  exists, but queued MusicKit entries remain eligible before metadata refreshes
  and narration keeps a neutral playback session while mixing so Apple Music
  behaves like the built-in bed without taking Control Center ownership.
  Exclusive narration keeps spoken-audio mode.
  Low Apple Music mix values request
  `.duckOthers`, because MusicKit volume is system-owned and not directly set
  by the app, while higher mix values keep the bed-forward behavior by lowering
  sentence narration around Music. Active reader navigation handoffs also keep
  Apple Music alive while narration playback intent is still live, but stop it
  when narration intent is gone or Background Music is disabled. Apple Music
  reading-bed mode now uses `.appleMusicBed` so sentence playback keeps Now
  Playing / Control Center metadata and remote commands while the Music track
  stays in the background; Job and Library playback attach the active sentence
  `AVPlayer` to `MPNowPlayingSession`, publish through that session's info and
  command centers, reassert the narration mixing session before forced
  reader snapshots, and reassert reader metadata after MusicKit playback/title
  changes, MusicKit playback-surface revisions, and narration playback-state
  changes because iPad Control Center can otherwise fall back to the Music track
  when autoplay starts. Delayed MusicKit surface reassertions are cancellable
  and are cancelled on reader pause, stop, and bed deactivation, so stale
  post-resume tasks cannot refresh the Music surface after the user has paused.
  Job and Library playback also own the foreground tvOS Play/Pause command at
  the top-level scene, routing physical Apple TV remote presses to the same
  reader transport as Now Playing while debouncing duplicate command delivery
  across play, pause, and toggle routes. On tvOS, direct Now Playing play/pause
  callbacks also resolve through the current reader state while Apple Music is
  only the bed, so a hardware Play/Pause delivery that arrives as an explicit
  play command still enters the reader-owned pause path. Reader-owned
  pauses also hold a short MusicKit suppression window: if Apple Music reports
  playback or a still-playing track change again during that window, the app
  repeatedly re-pauses Music instead of mirroring that stray or delayed resume
  back into narration or letting Music promote
  fullscreen artwork. Observed Music pauses during bed auto-resume intent also
  adopt the same reader-owned pause guard as explicit reader pauses, including
  stale resume cancellation, tvOS surface suppression, and pause confirmation,
  even if MusicKit missed the earlier playing transition; auto-resume intent
  must not block immediate tvOS adoption, because normal Apple Music bed playback
  keeps that intent set and would make the first remote press pause only Music.
  The adopted pause increments a dedicated revision so Job and Library playback
  pause sentence narration from the same event even if generic Music surface
  booleans arrive in an unlucky order; the active playback view also registers
  an owner-scoped direct adoption handler so state-preserving Living Room
  captures must show the Job/Library narration-side acceptance breadcrumb, not
  only the MusicKit pause adoption. Active tvOS narration now adopts an
  observed Apple Music non-playing signal before the transient bed-recovery
  path, so a first Siri Remote pause cannot be treated as a recoverable Music
  wobble while sentence audio keeps playing. Reader pauses now pause Music immediately, then release the tvOS
  Music surface after a short held pause; reader resumes cancel that delayed
  release and clear stale MusicKit pause-ignore state so the next external pause
  cannot be discarded as if it were still app-owned. The tvOS duplicate command
  window now filters only same-action echoes; opposite Play/Pause actions inside
  the window still reach the reader transport so a quick real pause after resume
  cannot leave only the Apple Music bed stopped while narration continues.
  Reattaching the same sentence `AVPlayer` republishes stored reader metadata
  instead of only asking the existing session to become active. That reassertion
  remains live while narration or the Music bed is active, and active view
  handoffs no longer clear reader Now Playing until narration intent and the
  Music bed are gone. Device launch evidence should show the reader session attached and
  `active=true canBecomeActive=true` while Apple Music is in `appleMusicBed`.
  The last selected Apple Music song/album/artist/playlist/station is persisted
  by MusicKit item identity so relaunch can rebuild the queue before narration
  resumes. The repo-owned Apple contract lane includes
  `tests/test_apple_playback_state_helpers_contract.py`.
- Active job live-media fallback. Status: Apple Job playback still prefers
  `/api/pipelines/jobs/{job_id}/media/live` and starts live refreshes for active
  jobs, but the initial load now falls back to the regular media snapshot if
  the live endpoint is temporarily unavailable. The repo-owned Apple contract
  lane includes `tests/test_apple_live_media_fallback_contract.py`.
- Library media file route helpers. Status: Apple online playback and offline
  sync now build and parse `/api/library/media/{job_id}/file/{file_path}` URLs
  through `ApplePipelineMediaRuntimeContract`, so encoded Library asset paths
  share the same route helper as the rest of the playback media client. The
  repo-owned Apple contract lane includes
  `tests/test_apple_runtime_descriptor_contract.py`.
- Library metadata route helpers. Status: Apple Library item metadata edits,
  source uploads, ISBN apply, and metadata enrichment now substitute the same
  runtime route templates that Settings validates, keeping Library management
  actions aligned with the public descriptor before simulator or device use.
  The repo-owned Apple contract lane includes
  `tests/test_apple_runtime_descriptor_contract.py`.
- Create route template helpers. Status: Apple saved-template detail/delete
  routes and acquisition job polling now substitute the same runtime route
  templates that Settings validates, keeping native Create template reuse and
  discovery/download status polling aligned with the public descriptor before
  simulator or device journeys run. Apple Create readiness also polls the
  non-mutating Download Station sentinel job id and validates the async
  acquisition job status payload shape, so Web/Apple downloader handoffs fail
  preflight before simulator or device journeys drift. The repo-owned Apple contract lane includes
  `tests/test_apple_runtime_descriptor_contract.py`.
- Playback search/bookmark jumps. Status: Apple text search and bookmark pills
  use the shared sentence jump path with active playback state, video pills keep
  seek/play state across search results and segment bookmark jumps, and text
  time-bookmark jumps now defer until the target chunk audio is ready. Apple
  media search now trims the playback job id before backend lookup and stops
  blank ids in the client, matching the backend route guard that prevents
  accidental unscoped searches. iPad lookup word navigation and tvOS remote
  Play/Pause are kept on the single `PlayerKeyboardShortcutBroker` path across
  app menu commands, UIKit key commands, hardware-press fallback, GameController
  fallback, and app-level tvOS remote press interception; duplicate hidden
  SwiftUI arrow shortcut layers stay removed from both book and video lookup
  bubbles. Lookup Read Aloud also reclaims or reactivates that shared
  broker path after backend pronunciation audio or platform speech starts,
  finishes, or cancels, so left/right arrows keep moving the highlighted word
  and refreshing the definition while the bubble is open. The book reader also
  keeps a short physical-arrow latch across broker, GameController, and
  first-responder delivery, so a single iPad key press cannot be handled once
  as word navigation and again as a sentence skip. Apple Now Playing
  next/previous commands now pass the last rendered sentence number into the
  view-model skip path, so translation-only reader skips stay sentence-based
  even if the audio clock is still settling after a seek. Pending
  slider/search/bookmark render locks now live in a small pure Swift helper
  with executable coverage for stale chunk audio, local-row sentence ids, lock
  expiry, and next-window rejection before the view releases frozen rendering
  back to live translated-word highlights. Single-track playback time is now
  also contract-checked to stay local to the active file before combined audio
  option offsets are considered, guarding the translation-only slider/skip drift where
  hidden original-track duration was added back into rendering. The repo-owned Apple contract lane includes
  `tests/test_apple_playback_search_bookmark_contract.py` and
  `tests/test_apple_playback_state_helpers_contract.py`.
- Browse now-playing return. Status: Apple browse surfaces keep a remembered
  playback target and expose a Return to Now Playing strip after leaving
  playback on compact iPhone/iPad, Apple TV, and iPad/Mac-style split surfaces.
  Apple TV now keeps that control as a focused browse-list row after pressing
  Back/Menu out of playback, giving the menu a direct route back to the active
  job or library item instead of relying on a floating-only affordance. The TV
  row uses the stable `nowPlayingReturnButton` automation target, so unattended
  playback journeys can verify the Back/Menu return path. Search remains
  covered so finding another item does not strand the active job or library
  entry. The repo-owned Apple contract lane includes
  `tests/test_apple_now_playing_contract.py`.
- Playback identity headers. Status: Apple interactive and video playback now
  present the banner, cover art, title, author, and info pills as one modern
  media identity area with stronger material styling, fallback cover tiles, and
  fit-aware metadata rows across iPhone, iPad, Apple TV, and local Mac Designed
  for iPad. Interactive Reader keeps title, author, and category/type on one
  compact baseline where possible. Sentence scrubbing lives in a thin
  Interactive Reader footer, while video playback keeps the native player
  scrubber instead of adding a duplicate footer timeline.
- Playback helper state coverage. Status: Apple playback now has repo-owned
  contract coverage for `AudioModeManager` track/mode transitions, timing-track
  routing, and `SentencePositionProvider` strategy priority so iPhone, iPad,
  Apple TV, and local Mac Designed for iPad refactors keep the same shared
  playback semantics. Original/Translation text-track toggles now align
  narration audio mode to visible/effective tracks, combined-track
  translation-only playback uses translation timing and active roles, paused
  iPad lookup arrows refresh the definition from the moved selection, and
  chunk handoffs now synchronize the selected audio option from the active
  single-track mode before next-batch playback can load, so the transcript and
  narration do not drift back to combined audio at batch boundaries. Unhydrated
  next-batch setup now also preserves original-only/translation-only mode from
  playable chunk audio options even when visible text tracks temporarily fall
  back to Original before metadata finishes loading, preventing batch-end
  render/audio drift, and audio prepare now reasserts the active single-track
  option just before resolving playback URLs so stale selected ids cannot reset
  a post-handoff batch. The view model now also remembers the explicit
  original-only or translation-only lane separately from transient chunk audio
  IDs, so metadata refreshes and stale sequence-mode bridges cannot reset the
  next batch back to the hidden track, and timing/duration/role/sequence helpers
  now treat that remembered single-track lane as authoritative even if a SwiftUI
  manager briefly reports sequence mode during a batch handoff. Manager-backed
  single-track resolution now refreshes that durable lane immediately too, so an
  end-of-batch callback cannot prepare combined audio before SwiftUI rendering
  catches up. The requested single-track resolver now lets the single lane that
  was actually loaded beat stale preferred state before sentence-batch EOF
  handoffs, preventing the next chunk from resetting rendering away from the
  selected track, and passive lifecycle observation no longer clears the remembered
  lane when it sees a sequence-mode/default refresh during selected-chunk or
  track-availability setup. The selected timing lane is now consulted by the
  requested single-track resolver before transient manager or picker state, so
  no-URL EOF/stall recovery or a hydrated-batch refresh cannot make rendering
  follow combined audio while narration remains on the selected stream, and a
  stale enabled sequence controller no longer suppresses that stored timing lane
  during batch handoff because sequence-mode setup clears the timing lane when
  sequence mode is intentional. Passive
  hydrated-batch text/audio synchronization
  now also refuses to broaden a remembered original-only/translation-only lane
  back to combined merely because the freshly loaded batch exposes both text
  tracks; only explicit text-track toggles may expand back to sequence. Stale
  audio-ended URL checks now live in the shared `PlaybackEndedURLPolicy` covered
  by the executable mode-switch harness, including combined-only batches where
  the selected lane must reject hidden original-stream EOF callbacks. Batch-end
  handoffs also infer the completed single-track lane from the just-ended audio
  URL when transient manager or selected-track state has reset to combined, so
  the next sentence batch stays on the selected original/translation lane. Single-track
  audio preparation also reasserts the active lane and timing URL before same-URL
  reuse or URL reload paths can seek/play, keeping end-of-batch rendering on the
  narration lane even if the selected chunk was rebuilt around an already-loaded
  player item. Single-track playback time now also uses the durable requested
  original/translation lane before considering multi-file queue offsets, so a
  transient sequence-mode bridge at a batch boundary cannot add the hidden track
  duration back into rendering; header active-role pills now use the same
  durable lane before transient manager state so the visible selection does not
  flash back to both tracks during the handoff. Adjacent-batch prefetch now
  also treats that durable lane as authoritative and warms the requested stream
  inside combined-only chunks instead of the hidden first/original stream. The
  audio coordinator now keeps reader playback intent alive
  through URL-aware EOF handoff callbacks until the view model loads the next
  sentence batch or pauses at end-of-book, and the playback mode-switch harness
  plus source-shape contract pin the EOF and same-URL reuse state transitions. The
  lifecycle bridge also restores an explicit one-track visible selection back
  into `AudioModeManager` and the selected chunk audio option before default
  setup can expand to All, with the source-shape contract guarding that order.
  Resume and visible-track restore paths now route through the same
  `applySingleTrackSelection` helper as chunk handoff instead of only assigning a
  matching option id, so the durable loaded lane survives the next batch
  boundary.
  Destination language pills prefer authoritative target-language request/config
  fields instead of broad nested metadata scans. The repo-owned Apple contract lane includes
  `tests/test_apple_playback_state_helpers_contract.py`.
- Playback token normalization cache. Status: Apple interactive playback keeps a
  bounded per-player token normalization cache across live media refreshes and
  chunk metadata rebuilds, keyed by sentence text plus explicit token arrays
  and reset on each new job load so chunk revisits avoid repeated token parsing
  without retaining stale metadata. The repo-owned Apple contract lane includes
  `tests/test_apple_token_normalization_cache_contract.py`.
- Playback sentence-image prefetch. Status: Apple interactive playback now
  extends the adjacent-sentence prefetch pass to warm a bounded batch of nearby
  sentence image URLs around the active/visible sentence after chunk metadata
  refresh, using the same view-model image path resolver consumed by the header
  image reel. The repo-owned Apple contract lane includes
  `tests/test_apple_sentence_image_prefetch_contract.py`.
- Interactive playback sleep timer. Status: Apple interactive playback now
  exposes a compact sleep timer pill with 5, 15, 30, and 45 minute presets
  across iPhone, iPad, Apple TV, and the local Mac Designed for iPad surface.
  Expiration pauses narration plus the active built-in or Apple Music reading
  bed, and player teardown cancels any pending countdown. The repo-owned Apple
  contract lane includes `tests/test_apple_sleep_timer_contract.py`.
- Video playback sleep timer. Status: Apple video playback now reuses the same
  sleep timer pill across iPhone, iPad, Apple TV, and the local Mac Designed
  for iPad surface. Web shared video playback and YouTube Dub playback expose
  the same 5, 15, 30, and 45 minute timer through the shared VideoPlayer path.
  Expiration pauses the video coordinator or Web video element, video URL
  changes and teardown cancel pending countdowns, and tvOS header focus can
  move through Search, Bookmarks, Sleep Timer, and timeline controls. The
  repo-owned Apple contract lane includes `tests/test_apple_sleep_timer_contract.py`;
  the repo-owned Web lane includes `VideoPlayer.test.tsx` and
  `YoutubeDubPlayer.test.tsx`.
- Upload/reupload library source files. Status: iPhone/iPad Library rows can
  replace an existing library item's source through the same
  `/api/library/items/{job_id}/upload-source` backend route used by Web. The
  native flow now reviews the selected replacement file before upload and
  accepts common book/video source extensions (`.epub`, `.pdf`, `.mp4`,
  `.mkv`, `.mov`, `.webm`) to match the Web edit form.
- ISBN metadata preview/apply. Status: iPhone/iPad Library rows can fetch
  `/api/library/isbn/lookup` previews and then apply the ISBN through
  `/api/library/items/{job_id}/isbn`, matching the Web lookup/apply contract.
  ISBN preview lookup failures now return a generic error with token-safe
  library-route telemetry, keeping ISBNs, provider messages, local paths, and
  tokens out of Web/Apple Library sheets and logs.
- TV-safe source diagnostics. Status: iPhone, iPad, and Apple TV Library rows
  expose read-only Source Details with stored-source, file, type, relative path,
  status, and media completion diagnostics without upload/edit controls.

## Backend Optimization Targets

Initial backend hotspots to inspect before changing behavior:

- Job listing/count path: `modules/webapi/routes/jobs_routes.py`, `modules/services/pipeline_service.py`, `modules/services/job_manager/manager.py`, and `modules/services/job_manager/stores.py`.
- Metadata loading and chunk traversal: `modules/metadata_manager.py`, `modules/services/job_manager/persistence.py`, and `modules/webapi/routes/media/media_list.py`.
- Search across jobs/library: `modules/search/service.py` and `modules/webapi/routes/library_routes.py`.
- YouTube NAS inventory and linked-job indexing: `modules/webapi/routers/subtitle_utils/youtube_routes.py`.
- Library media payload building: `modules/library/library_service.py`, `modules/library/library_sync.py`, and `modules/webapi/routers/library.py`.

Optimization candidates:

- Guard paginated `/api/pipelines/jobs` response shape before changing list internals. Status:
  backend tests now pin `total`, `offset`, `limit`, newest-first route ordering,
  access payload normalization, generated files, job labels, and parameter
  snapshots; service tests pin active admin pagination, persisted-only
  store pagination, and metadata-only non-admin counts/lists that hydrate only
  the requested visible page. The shared cross-surface checkpoint now exposes
  those route/service guards as `test-backend-pipeline-jobs`, and changed-test
  selection runs that slice for job-route, pipeline-job schema, pipeline-service,
  and job-manager edits before the broader Web API/service fallbacks.
- Audit repeated filesystem metadata reads during job list/library list rendering.
  Status: `/api/pipelines/jobs` now skips filesystem image prompt summary reads
  while preserving those rich summaries for single-job status responses.
- Add lightweight timing/log counters around job list, library list, media manifest, and search endpoints.
  Status: Library item listing now records a Prometheus duration histogram and
  token-safe aggregate logs for success/error paths without recording raw
  search queries, user identifiers, auth headers, or tokens. Unified metadata
  lookup now uses the shared metric-plus-log wrapper for success, invalid-type,
  not-found, and error outcomes while logging only media type, force/raw flags,
  and aggregate source counts instead of titles, ISBNs, filenames, provider IDs,
  YouTube URLs, or raw metadata payloads, and the shared backend target now
  includes the route tests. Book OpenLibrary preview/cache failure handlers now
  also return/log generic errors without source filenames, NAS paths, ISBNs,
  job ids, titles, authors, or raw exception strings, matching the TV/YouTube
  metadata preview contract used by Web and Apple Create. Pipeline media
  search now records the same token-safe duration and aggregate hit-count
  telemetry for blank, forbidden, not-found, and success outcomes. Pipeline job
  listing now records token-safe duration and pagination/result-count telemetry
  for success/error outcomes without logging user ids or job ids. Pipeline media
  manifests now record token-safe duration and aggregate category/file/chunk
  counts for completed and live manifest routes without logging job ids, user
  ids, auth headers, tokens, or file names. Sentence-image single and batch
  metadata lookups now record the same token-safe media-route duration
  telemetry and aggregate count/missing logs without logging job ids, user ids,
  auth headers, tokens, paths, filenames, or raw sentence content. Sentence
  image regeneration also returns generic DrawThings failure details, keeping
  image node URLs, prompts, sampler names, paths, and raw exception strings out
  of Web/Apple-facing responses. Library
  media manifests now use the same token-safe aggregate route telemetry for
  success, missing-item, and error paths, without logging job ids, user ids,
  auth headers, tokens, NAS paths, or filenames. Offline export create/download
  routes now record token-safe duration telemetry and aggregate logs without
  logging source ids, export ids, user ids, file paths, filenames, auth headers,
  or tokens.
  Library, search, job-list, media-manifest, sentence-image,
  offline-export, and YouTube NAS library routes now delegate duration
  observation and token-safe aggregate logging through the shared route
  telemetry helper. Auth route duration/logging, pipeline EPUB/source content-index
  pickers, subtitle source pickers, and local media streaming setup metrics
  also share the route telemetry helper, including the stream-specific
  media-kind label. Local media file streaming now records
  token-safe setup duration telemetry and aggregate logs for full, partial,
  unsatisfiable-range, and not-found results across storage and library media
  file downloads without logging paths, filenames, job ids, user ids, auth
  headers, tokens, or raw range values, and now uses the shared labeled route
  logger so the `media_kind` metric label and token-safe human log stay on the
  same sanitized path. Library list, ISBN lookup, and media manifest routes now
  use the same shared Library route telemetry wrapper for token-safe aggregate
  counts and duration logging, while Library action routes for source uploads, metadata
  edits/enrichment/refresh, ISBN apply, access changes, entry moves/removals,
  media removals, reindexing, and media-file resolution now route their
  token-safe aggregate logs through the shared route telemetry helper too,
  reducing drift between Web/Apple Library actions and other backend surfaces.
  Acquisition provider/discovery/acquire routes are now also pinned in the
  global observability contract, so the shared Web/Apple Create discovery layer
  cannot lose its route-duration histogram while still keeping provider tokens,
  source paths, raw queries, and artifact ids out of metric labels.
- Prefer precomputed or cached job summary fields for list rows while keeping
  full metadata available on detail/media routes. Status:
  `/api/pipelines/jobs` now uses compact row result summaries so list rendering
  preserves titles, book/media metadata, generated files, parameter snapshots,
  and Apple/Web recent-default fields without materializing heavy full pipeline
  results; single-job status/detail routes still return rich result payloads.
- Avoid avoidable library repository reads in shared search paths. Status:
  `/api/pipelines/search` now defers the library item lookup until the pipeline
  job is missing, so normal active-job media searches avoid a library sync
  lookup while preserving library fallback behavior for archived items and
  unknown-job 404s. The route also trims `job_id` once at the boundary and
  rejects blank normalized ids before touching pipeline or library services, so
  malformed Web/Apple playback search state does not trigger avoidable storage
  or repository work.
- Avoid avoidable public runtime descriptor work in Apple preflight paths.
  Status: `/api/system/runtime` now serves from a static prevalidated descriptor
  template, only copying caller-mutable section dictionaries/lists and filling
  the current app version per request. Apple Create pipeline intake readiness
  now also snapshots queue pressure through the route threadpool hook, keeping
  the async readiness endpoint responsive if job-manager pressure state reads
  contend with backend worker activity.
- Avoid avoidable chunk metadata reads in shared search paths. Status:
  generated media search now skips per-chunk metadata JSON reads when the
  generated chunk already carries id/range/sentence fields and a searchable
  text file, while preserving metadata fallbacks for sparse chunk entries and
  metadata-only sentence text; search also resolves the friendly job label
  once per job and reuses it across multiple chunk hits. Generated-files search
  also continues when a job root exists but its metadata manifest is absent,
  using the chunk data already present on the job and skipping eager manifest
  iteration in that case.
- Avoid full job hydration when tagging YouTube NAS inventory with linked jobs.
  Status: `/api/subtitles/youtube/library` now asks `PipelineJobManager` for
  visible `youtube_dub` metadata only, preserving role-based access checks while
  avoiding reconstruction of every visible stored job before Apple/Web Create
  default video pickers render. The route also records token-safe duration
  telemetry and aggregate video/subtitle/linked-job counts without logging NAS
  paths, filenames, job ids, user ids, auth headers, or tokens. The NAS scanner
  also reuses each `os.walk` folder file list for subtitle matching instead of
  re-reading the same directory once per video, keeping large default video
  pickers lighter on NAS-backed folders. Linked-job indexing is now filtered to
  the discovered video tokens, prefilters unrelated stored jobs by filename
  before path normalization, reuses each discovered video token while building
  response rows, reuses each walked folder stat while ranking videos by effective
  recency, and empty NAS listings skip job metadata reads entirely.
  YouTube NAS subtitle deletion now validates the selected video through the
  shared tolerant stat helper before deleting sidecars, and changed-test
  selection routes YouTube/NAS route or service edits through the focused
  backend YouTube dubbing gate instead of relying only on the broad WebAPI
  suite.
- Keep backend source pickers resilient on NAS-backed folders. Status:
  `/api/pipelines/files` now stats each visible ebook/output candidate once and
  skips entries that disappear or become unreadable during listing; EPUB
  discovery now recurses into visible books-root subfolders while pruning hidden
  folders, so Web and Apple Create defaults can pick the latest NAS book even
  when ebooks are grouped by author or series. It also treats transient
  source/output directory scan failures as an empty picker response, preserving
  Web and Apple Create usability during NAS remounts or concurrent cleanup.
  The same EPUB picker now accepts an optional bounded `limit` query and keeps
  only the newest matching entries while scanning, preserving the default full
  listing while Web and Apple Create request the shared bounded default for a
  tested low-payload path on very large NAS roots. The bounded EPUB picker now
  consumes the shared NAS-safe source iterator directly instead of materializing
  the full discovered file list before trimming, so latest-book defaults stay
  lighter on large books roots. The route and local EPUB acquisition discovery
  now share the same cached-stat bounded newest helper, so Web and Apple Create
  default/source discovery keep one ordering and trimming rule without rebuilding
  discarded response objects. Manual-download EPUB discovery reuses that same
  cached-stat sort key for newest/title tie-breaks across configured roots, so
  Default sources keep consistent ordering when local and download-station inboxes
  are both available. Apple Create readiness now probes that bounded
  picker URL as its inventory check, so reusable pipeline preflights exercise
  the path the native clients actually load.
  Output-root readiness and route-level source/output presence flags now use
  the same tolerant stat path instead of direct `Path.exists()` checks, so
  completed output folders stay visible during transient NAS existence races.
  EPUB and subtitle source pickers now share
  `modules/services/source_discovery.py` for hidden-folder pruning, suffix
  filtering, stale-file skipping, transient root-scan tolerance, and cached
  stat payloads, so future Web/Apple source pickers do not need to duplicate
  NAS-race handling. Subtitle source picker rows now also consume those cached
  discovery stats instead of restatting every source after the shared walk,
  keeping Web/Apple subtitle defaults lighter on large NAS folders. Acquisition
  provider readiness now uses the same tolerant stat helper before advertising
  backend default book/video discovery sources, so Web and Apple Create source
  pickers do not lose defaults just because a NAS root races with remount or
  cleanup.
  Prepared acquisition artifacts for local EPUBs, manual-download EPUBs, NAS
  videos, and manual-download videos now validate reviewed source files through
  the same tolerant stat helper, so Web/Apple Create handoffs fail as ordinary
  missing artifacts when a file vanishes after discovery instead of racing on
  direct `Path.exists()` / `Path.is_file()` checks.
  Reviewed public-catalog EPUB acquisition now also reserves destination
  filenames with the same tolerant stat helper instead of `Path.exists()`, so
  Web/Apple Create acquisition can choose a collision-safe `-N` filename even
  when NAS existence checks are flaky.
  Pipeline defaults now validate a configured default `input_file` with the
  same tolerant stat helper before preserving it for Web/Apple Create, avoiding
  direct existence checks on NAS-backed book roots.
  Reading-bed catalog sync now also checks its manifest through the tolerant
  stat helper, keeping Web and Apple background-music route initialization
  aligned with the NAS-safe playback/media route pattern.
  Media search path resolution now uses the same tolerant stat helper for
  generated text, media, subtitle, job-root, and metadata-manifest checks, so
  Web and Apple reader search pills skip vanished NAS files without failing the
  whole search route.
  Resume and bookmark filesystem playback-state files now use the same tolerant
  stat helper for load/list/delete checks, so Web and Apple Continue/bookmark
  sync treats transient shared-storage races as ordinary missing state instead
  of leaking backend filesystem errors.
  Job status image-generation summaries now probe prompt-plan metadata through
  the same tolerant stat helper, keeping Web and Apple job rows resilient when
  image metadata files race with NAS-backed job-root cleanup or remounts.
  Lookup-cache builds now probe job roots and chunk metadata through the same
  tolerant stat helper, so Web and Apple precomputed word lookups can skip
  transiently missing NAS-backed chunks without failing the phase.
  Metadata enrichment caches now load and delete cached lookup files through
  the tolerant stat helper, so Web and Apple Create metadata review can treat
  transient cache-file races as misses instead of filesystem failures.
  Library sync now loads job metadata manifests through the same tolerant stat
  helper, so Web and Apple Library item refreshes treat transient NAS-backed
  metadata races as ordinary missing metadata instead of direct `Path.exists()`
  failures.
  Library source-material resolution and collision handling now use tolerant
  stat checks for source EPUB/PDF paths, data-root scans, and staged-copy
  destination candidates, reducing Web/Apple Library refresh races around
  NAS-backed job data folders.
  Library cover-source resolution and normalized cover-path scans now use
  tolerant stat checks too, keeping Web/Apple Library artwork refreshes
  resilient when metadata folders race with cleanup or remounts.
  Library generated-file compaction, chunk metadata loader gating, and media
  file stat collection now also use tolerant stat checks, reducing Web/Apple
  playback-manifest races around NAS-backed job roots.
  Library media-presence, media cleanup, and stored-cover probes now use
  tolerant stat checks, keeping Web/Apple paused-item playability and artwork
  badges stable when NAS folders remount or vanish during refresh.
  Library import/export service gates now use tolerant stat checks for source
  directories, metadata manifests, target conflicts, and export sources, keeping
  shared Web/Apple Library actions resilient around NAS-backed library roots.
  Library metadata refresh now checks source EPUB availability through tolerant
  stat probes before local metadata extraction, reducing Web/Apple
  refresh/enrichment races when source files vanish during NAS remounts.
  Library cover mirroring now checks source artwork through tolerant stat
  probes before copying into item media, keeping Web/Apple artwork refreshes
  resilient when NAS-backed cover files vanish mid-refresh.
  Library YouTube-dub bundling now checks source videos, subtitle companions,
  staging roots, and copied metadata through tolerant stat probes, reducing
  Web/Apple video Library move races around NAS-backed media folders.
  Library move-to-Library promotion now checks queue roots, target conflicts,
  YouTube stitched-media detection, cleanup staging roots, and lock waits
  through tolerant stat probes, reducing shared Web/Apple NAS races during
  book/video promotion.
  Library media-removal and entry-delete actions now check item roots and
  ancestor-pruning directories through tolerant stat probes, reducing
  Web/Apple cleanup races around shared library storage.
  Library metadata edits, access edits, and refresh relocations now check item
  roots and rename targets through tolerant stat probes, reducing Web/Apple
  item-maintenance races around NAS-backed library folders.
  Library enrichment, source reupload, and ISBN metadata actions now check item
  roots, uploaded source files, and obsolete source cleanup through tolerant
  stat probes, reducing Web/Apple maintenance races around source replacement.
  Library item recovery, media-file serving, cover lookup, and filesystem
  recovery scans now check metadata manifests, directory candidates, and media
  files through tolerant stat probes, reducing Web/Apple read-path NAS races.
  Library repository startup now discovers SQLite migration files through
  tolerant stat and directory probes, keeping Web/Apple preflight startup
  resilient when migration paths are unavailable or racing.
  Runtime directory resolution now cleans broken configured roots and reuses
  existing roots after transient mkdir failures through tolerant stat probes,
  reducing Web/Apple Create/source-root startup races.
  Default SMB books/output root validation now uses tolerant stat probes for
  existing roots, creatable children, and missing-parent rejection, keeping
  Apple/Web Create defaults steadier around NAS mount races.
  YouTube dubbing batch stitching now resolves stitched-output collisions,
  batch inputs, and adjacent subtitle files through tolerant stat probes,
  reducing Web/Apple video Create races around NAS-backed batch artifacts.
  Default discovery now queries every advertised local/manual source provider before
  applying the candidate limit, then orders local files newest-first, so a fresh
  manual-download or Download Station EPUB can win over older books already in
  the library root on both Web and Apple Create pickers. Remote/default catalog
  providers are still probed for participation evidence, but after local/manual
  providers fill the visible result budget they receive only the remaining
  visible slots plus a one-result probe, reducing YouTube/Gutenberg/indexer
  over-fetch without hiding available source types from Web or Apple Create.
  The provider fan-out ordering and per-provider query-limit rules now live in
  `modules/services/acquisition/discovery_planning.py` with focused acquisition
  coverage, keeping Web and Apple Default sources picker behavior easier to
  evolve without reopening the full discovery service.
  Download Station job polling now resolves completed file hints only under
  configured manual/download roots and drops URL-like, escaped, or outside-root
  entries, so Web/Apple Create reconnects to backend-visible local artifacts
  instead of arbitrary downloader payloads.
  Public-catalog acquisition artifact tokens now carry token-safe Gutenberg or
  Internet Archive provenance into the prepare step, keeping Web/Apple Create
  template and draft metadata stable after acquire-then-prepare handoffs.
  Newest-first EPUB defaults are preserved, and EPUB matching is
  case-insensitive so NAS files ending in `.EPUB` are eligible for the same
  default-source flow. `/api/pipelines/files` deletion now treats
  already-vanished, in-scope EPUB sources as an idempotent cleanup success
  while still rejecting paths outside the books root. `/api/subtitles/sources`
  now applies the same tolerant root/file stat path, transient directory-scan
  tolerance, and stale-entry skip when building Web/Apple subtitle source
  pickers, and recursively discovers visible nested subtitle files while
  preserving SRT/VTT-first newest-default ordering, so NAS remounts, vanished
  subtitle paths, or series-organized subtitle folders do not become broken
  default selections. Subtitle job submission validates selected server
  subtitle files through the same tolerant stat helper before enqueueing, so
  direct source handoffs fail as ordinary missing sources when a NAS file
  vanishes between picker refresh and Create submission.
  `/api/subtitles/delete-source` now treats already-vanished, in-scope subtitle
  sources as idempotent cleanup results while still rejecting paths outside the
  allowed base directory. EPUB and subtitle source picker routes now share
  token-safe duration telemetry through the shared route telemetry helper, with
  aggregate source/output counts, bounded EPUB limit state, and no NAS path,
  filename, job id, user id, auth header, or token logging. The
  manifest-registered `test-backend-pipeline-sources` target now covers EPUB
  source listing, bounded newest-first picker limits, selected-source
  content-index loading, vanished-source deletion, outside-root rejection, and
  local EPUB upload persistence through `/api/pipelines/files/upload`, so the
  shared backend pipeline protects the picker/import paths used by Web and
  Apple Create. Apple Create source-selection
  contracts also pin the native default picker rules to the readiness preflight:
  newest backend-visible EPUB, SRT/VTT before ASS for subtitle jobs, newest
  playable NAS video, and English sidecar preference when available. The
  NAS YouTube/video scanner also skips video and subtitle sidecar candidates
  that vanish after `os.walk()` and prunes hidden folders/files, keeping Web
  Video Dubbing and Apple Create source pickers usable during concurrent
  downloads, cleanup, or temporary NAS staging folders. It now validates the
  scan root plus walked video/subtitle entries through the shared tolerant stat
  helper instead of direct `Path.exists()`/`is_dir()` checks, so transient NAS
  existence failures do not hide otherwise readable video sources; video
  candidates that vanish during response path resolution are skipped without
  breaking the remaining picker results. YouTube
  download finalization now applies the same stale-entry tolerance when sorting
  downloaded subtitle files, partial recovery files, and muxed output files, so
  a transient NAS directory race can still fall back to a usable downloaded
  artifact instead of losing a completed download. Downloaded-video cleanup
  uses the same stale-entry tolerance while discovering adjacent subtitle
  artifacts before folder removal. Already-vanished NAS video and subtitle
  sidecar selections with valid suffixes now return structured `missing`
  results instead of picker-breaking 404s. The shared source-discovery walker
  now also rejects hidden descendant path components even when a filesystem
  walk unexpectedly yields them, keeping Web and Apple source pickers from
  surfacing hidden NAS staging folders if `os.walk` output is stale or unusual.
  The same walker normalizes suffix filters so future callers can pass
  `epub`/`srt` or `.epub`/`.srt` without drifting from the shared Web/Apple
  picker behavior. It also validates the root directory through the same
  tolerant stat path instead of `Path.exists()`, so transient NAS `exists`
  failures do not bypass otherwise readable source roots.
  Unexpected YouTube/NAS source-action failures for subtitle-stream probing,
  embedded-subtitle extraction, subtitle deletion, and video deletion now return
  generic internal-error details and log only token-safe action labels, so Web
  and Apple Create paths do not leak NAS folders, filenames, users, or exception
  payloads when a backend tool fails. YouTube URL discovery and download actions
  now follow the same rule for subtitle listing, subtitle download, video format
  inspection, video download, and output-folder creation failures, avoiding raw
  URLs, query parameters, output paths, users, or backend exception text in
  shared Web/Apple error logs and responses. These YouTube discovery, download,
  cleanup, linked-job tagging, and Dub submission failure paths also avoid
  traceback attachments in token-safe logs so raw URLs, NAS paths, titles,
  languages, voices, and tokens do not leak through exception frames. YouTube
  URL/search discovery candidate construction, metadata normalization, duration
  parsing, API-key lookup, detail fetches, and token-safe API error mapping now live in
  `modules/services/acquisition/youtube_discovery.py` with focused acquisition
  coverage, keeping Web and Apple video discovery behavior easier to evolve
  without reopening the full acquisition service. Newznab/Torznab search,
  review-only metadata candidate construction, source-reference storage, endpoint,
  key, category, sanitized API URL, XML feed, and published-date helpers now
  live in `modules/services/acquisition/indexer_discovery.py` with the same
  focused acquisition coverage, keeping reviewed indexer source pickers aligned
  across Web and Apple Create.
  Acquisition provider defaults keep
  local EPUB and NAS video as the primary choices when those roots are readable,
  include readable explicit manual/download-station inboxes in the backend-owned
  default list, and fall back to `manual_downloads` when a primary source root is
  unavailable, keeping warmed browser/Download Station imports discoverable for
  Web and Apple Create during NAS root outages.
- Keep all auth/session headers and token handling out of logs and docs.
  Status: the repo-owned `test-backend-auth-session` target now covers the
  password login, compact session restore payload, logout invalidation, missing
  or invalid token rejection, and auth route duration metric used by Web and
  Apple clients, and the shared Apple backend manifest runs it as an
  auth/session regression gate. The repo-owned `test-web-auth-focused` target
  now runs the Web authentication flow coverage for token persistence,
  authenticated API headers, logout cleanup, password-change calls, and
  cross-tab/session restore behavior, and the shared Apple Web manifest runs it
  as the matching Web auth regression gate.
- Preserve authorization semantics on optional playback helpers. Status:
  lookup-cache routes still treat missing jobs or absent cache files as
  graceful MyLinguist cache misses for Web/Apple playback, but shared job-root
  authorization failures now propagate as `403` instead of being flattened into
  cache-miss responses. Assistant lookup backend failures now return a generic
  bad-gateway response with token-safe duration telemetry, avoiding selected
  words, prompts, language labels, model names, provider details, and local
  paths in Web/Apple lookup bubble errors or logs. Bookmark routes trim route IDs at the boundary, reject
  blank normalized job IDs before storage access, and treat blank bookmark
  deletes as idempotent `deleted=false` responses so malformed Web/Apple
  playback state does not create stray fallback bookmark files.

## Parity Roadmap

### Milestone 1: Shared Creation Contract

Define stable client DTOs for creation:

- `PipelineRequestPayload`
- EPUB upload response
- generated book request/response
- subtitle job request
- YouTube dubbing request

Expected Apple work:

- Add focused API client extensions for creation/upload.
- Add unit tests for encoding and path selection without printing tokens.
- Keep physical device deployment attended and on-request only.

Status: API plumbing and generated-book payload coverage are in place. Continue
expanding contract checks whenever a new Web-only creation flow becomes native.
Repo-owned physical-device helpers now expose attended preflight,
shared-pipeline signed-build-only, shared-pipeline deploy dry-run wrappers, and
a full-entitlement signing planner for cached-profile iPhone/iPad fallbacks; the
unattended deploy helper can now install a current signed full-entitlement app
artifact directly through `make apple-device-full-entitlement-stable-install`,
verifying signature plus current bundle id/version/build before touching the
device, or fall back from a failed Xcode CLI build to that verified artifact via
`make apple-device-full-entitlement-fallback-install`; the golden recipe
preserves iCloud/Push/Sign in with Apple without hand-editing `--skip-build`
paths; the
legacy entitlement-stripping fallback requires
`APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES` so iCloud/Push/Sign in with Apple
validation keeps the full entitlement set by default. The shared-pipeline
runtime contract now advertises the native subtitle source cleanup endpoint
alongside source listing and submission endpoints, and the repo-owned deploy
readiness hook validates the Create, Library action, offline export,
playback-state, and notification sections from `/api/system/runtime`, so Apple Settings,
Create-readiness preflights, and attended device-update preflights catch
backend/app drift before a simulator journey or device install tries to use
stale NAS cleanup, Library, export, bookmark, resume, or notification controls.
Notification device-removal now uses the same `{device_id}` template in the
runtime descriptor and FastAPI route table, with backend coverage comparing
those public paths directly. The same backend coverage now walks every
advertised runtime descriptor `/api/...Path` and `/api/...PathTemplate`, normalizes
FastAPI path converters, and verifies each public path exists in the actual
route table; library media file streaming therefore stays aligned on the shared
`{file_path}` template used by Web and Apple clients. That route-table parity
test now runs inside `make test-backend-runtime-descriptor`, so the reusable
Apple pipeline backend slice catches runtime path drift without requiring the
full Web API suite. Changed-test selection now sends runtime descriptor source,
backend route-contract, and Apple runtime contract edits through that focused
gate automatically, while still keeping the broader Web API or Apple contract
targets for files that need them. The same selector coverage now includes the
shared deploy readiness hook and Apple Create readiness validator, so unattended
device-preflight changes exercise both runtime descriptor and Apple contract
gates instead of falling back to generic tests only. The shared-pipeline
office-iPad Create-readiness lane now has repo-owned
`apple-pipeline-ipad-create-readiness` and dry-run shortcuts that delegate to
the registered `ipados-create` app-owned journey without depending on an
available iPhone. Apple Create readiness now also prepares an opaque
acquisition artifact token from the default book discovery candidate and checks
the `input_file` / `create_book_job` handoff contract before simulator/device
journeys trust discovery-selected sources. When default video discovery
advertises a tokenized candidate, the same gate prepares it and checks the
`video_path` / subtitle / `create_dub_job` handoff contract while keeping empty
video roots non-fatal. Local office-iPad iteration now also
has repo-owned office-iPad local build gate and office-iPad local verification
gate targets, preserving the documented office-iPad local verification gate:
`build-apple-office-ipad-surfaces` and `verify-apple-office-ipad-surfaces`
compile the iPad simulator and local Mac Designed for iPad/iPhone
surfaces, plus the iPad-destination UITest build in the verification lane,
without invoking iPhone simulator or physical-device deployment helpers. The
shared pipeline also has a focused `make test-apple-local-surface-contract`
gate for simulator/local Mac surface wiring without compiling apps. Apple TV now has matching repo-owned
`test-e2e-tvos-create-readiness` and shared-pipeline
`apple-pipeline-tvos-create-readiness`/dry-run shortcuts through the registered
`tvos-create` journey, keeping native tvOS Create checks simulator-only unless
a physical Apple TV deploy is explicitly requested. Create submission routes
now also record token-safe duration telemetry for subtitle jobs and YouTube Dub
jobs across success, validation, forbidden, not-found, and error outcomes
without logging source paths, file names, job ids, user ids, language or voice
values, metadata payloads, auth headers, or tokens; unexpected YouTube Dub
enqueue failures also return generic client details instead of raw exception
strings. The shared
`modules/webapi/route_telemetry.py` helper owns the common Create submission
metric/log formatting so future creation endpoints can adopt the same contract
without duplicating route-local metric plumbing. Acquisition provider,
discovery, artifact prepare, reviewed acquire, and Download Station
handoff/poll routes now share the same token-safe route telemetry helper,
including forbidden metrics when non-editor users hit the editor/admin-only
Create discovery surface before any provider search or downloader call can run.

### Milestone 2: iPad/iPhone Native New Job

Apple started with generated audiobook creation because it does not require
attended document import and can safely reuse `/api/books/options`. iPhone/iPad
now also expose a Narrate EPUB mode for server-side EPUB paths and local EPUB
document import/upload through the same backend file endpoint used by Web.

Target Apple UX:

- Add a `New Job` entry to the iPad/iPhone browse shell.
- Use SwiftUI `Form`/`NavigationStack` with sections for source, languages, audio, output, and advanced settings.
- Support simple existing-file submission first. Status: iPhone/iPad support
  server-side EPUB path submission through the Apple Create form.
- Add EPUB file import/upload using document picker on iPad/iPhone. Status:
  implemented in Apple Create Narrate EPUB by picking a local `.epub`,
  immediately uploading it to `/api/pipelines/files/upload`, refreshing the
  server EPUB picker, selecting the returned backend path, and submitting that
  server path to `/api/pipelines`. Narrate EPUB history defaults now reuse prior
  audio, output, translation, transliteration, lookup-cache, voice overrides,
  chunking, and sentence-splitter settings while preserving any fields edited in
  the current form; generated-book history also restores source-book continuation
  context, voice overrides, and sentence-splitter mode. Web Narrate Ebook and
  Apple Create now expose the same stable/modern splitter override and submit it
  through the shared pipeline payload. Create history no longer replaces newer
  backend-selected NAS EPUB/subtitle/video sources.
- Route success to the new job in Jobs and start auto-refresh. Status: Apple
  Create now switches to Jobs after successful submission, selects the created
  job, aligns the Jobs filter with the created job's category, and starts the
  Jobs auto-refresh loop so fresh generated-book, Narrate EPUB, subtitle, and
  YouTube jobs are immediately visible.

Keep Apple TV creation constrained to remote-friendly server/NAS workflows.
Status: the tvOS browse picker exposes Create, the native routing helper uses
the shared Create mode list, and local document import remains iOS/iPadOS-only
so Apple TV can submit generated-book, Narrate EPUB, subtitle, and YouTube jobs
from backend-visible sources without becoming the richest editing surface. The
strict Create-readiness journey can now run on tvOS via
`make test-e2e-tvos-create-readiness` and through the reusable pipeline
`tvos-create` profile. The tvOS Create view now runs the same server-backed
EPUB, subtitle, and YouTube NAS source refreshes as iPhone/iPad while keeping
local file import behind the iOS/iPadOS-only document picker.

### Milestone 3: Web UI Redesign

Redesign around the same information architecture as Apple:

- Jobs
- Library
- Search
- Create
- Settings/Admin

Refactor before restyling:

- Split large route files into page shell, toolbar, filters, list/detail, and action modules.
- Move repeated status/glyph/metadata row logic into shared components.
  Status: Web job status glyph rendering now uses the shared
  `JobStatusBadge` presentational component across the job list, job detail
  header, subtitle jobs, sidebar job rows, and sidebar player entry while
  preserving existing `job-status` CSS/data-state semantics and sidebar
  image-wait labels. Job Progress overview and metadata sections now also reuse
  the shared `MetadataGrid` definition-list renderer instead of hand-building
  repeated metadata rows, and the live media diagnostics strip now renders
  through the same helper while preserving its compact warning/ready styling.
- Isolate Library metadata helpers before visual redesign. Status:
  `LibraryPage.tsx` now imports tested helpers for item type, fallback labels,
  nested TV/YouTube metadata, image URLs, counts, and upload dates from
  `web/src/pages/library/libraryPageMetadata.ts`.
- Isolate YouTube dubbing helpers before visual redesign. Status:
  `VideoDubbingPage.tsx` now imports tested helpers for inline subtitle
  extraction defaults, target-language voice option building, and rerun-prefill
  mapping from
  `web/src/pages/video-dubbing/videoDubbingUtils.ts`.
- Isolate job progress math before visual redesign. Status:
  `JobProgress.tsx` now imports tested helpers for generated-file stat lookup,
  LLM batch progress, lookup-cache progress, and progress labels from
  `web/src/components/job-progress/jobProgressUtils.ts`.
- Isolate subtitle overlay helpers before visual redesign. Status:
  `SubtitleTrackOverlay.tsx` now imports tested helpers for ASS cue lookup,
  token navigation, selection shadowing, clamping, variant mapping, and
  subtitle TTS voice options from
  `web/src/components/video-subtitles/subtitleTrackOverlayUtils.ts`, and the
  subtitle MyLinguist bubble/portal renderer now lives in
  `web/src/components/video-subtitles/SubtitleLinguistBubblePortal.tsx`.
  Track rows, ASS cue loading, playback state observation, subtitle
  track-selection state, cue keyboard navigation, subtitle drag offset, and
  token navigation now live in focused components/hooks with Web playback gate
  coverage.
- Isolate live media state helpers before visual redesign. Status:
  `useLiveMedia.ts` now imports tested helpers for live media state shape,
  generated-file extraction, media bucket merging, chunk merging, audio-track
  detection, and chunk-sentence detection from `web/src/hooks/liveMediaState.ts`,
  plus modern and legacy timing normalization from
  `web/src/hooks/liveMediaTiming.ts`.
- Isolate Library list grouping before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for row layout type detection,
  title/author/genre fallback labels, timestamp formatting, flat
  book/subtitle/video layout detection, and author/genre/language grouping from
  `web/src/components/library-list/libraryListUtils.ts`.
- Isolate Library list media metadata resolvers before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for book summaries, TV/episode
  metadata, subtitle genre/summary/image values, YouTube metadata, source
  badges, and media asset URLs from
  `web/src/components/library-list/libraryListMediaUtils.ts`. Library row
  book/subtitle/video media cells, job-type glyphs, status stacks, and resume
  badges now live in focused `library-list` components with direct rendering
  coverage, leaving the main list responsible for grouping and routing. The
  repo-owned `test-web-library-focused` target now runs the Library page
  metadata, LibraryList helper, media cell, action, status badge, and resume
  badge slices so the shared Web pipeline covers the split Library list surface
  before full Vitest.
- Isolate Library list action gating before visual redesign. Status:
  `LibraryList.tsx` now imports tested helpers for permission defaults, export
  readiness, and disabled action states from
  `web/src/components/library-list/libraryListActions.ts`.
- Isolate Player panel active selection before visual redesign. Status:
  `PlayerPanel.tsx` now imports tested helpers for selected text item,
  selected chunk, and active text chunk resolution from
  `web/src/components/player-panel/activeTextSelection.ts`, while
  `web/src/components/player-panel/utils.ts` remains focused on general
  media/chunk formatting helpers. Focused coverage lives in
  `web/src/components/__tests__/playerPanelActiveTextSelection.test.ts` and is
  included in `test-web-playback-focused`. Player preference storage now uses
  the shared safe browser storage wrapper. Original/translation audio
  visibility persistence now lives in a focused tested hook so Web playback
  defaults can evolve alongside Apple playback settings without growing the
  panel coordinator. Active chapter state and chapter jump dispatch now live in
  a focused hook that reuses the shared chapter resolver utilities. Active text
  selection, selected chunk lookup, interactive audio cataloging, and
  audio-driven active chunk fallback now live in a focused tested hook rather
  than inline in the panel coordinator. Pending chunk-selection handoff now
  lives in a focused tested hook, so stale-index cleanup and chunk activation
  no longer sit in the main panel effect list. Interactive document
  preview/fallback content and placeholder visibility now resolve through a
  tested pure helper so the panel coordinator no longer owns those display-state branches inline.
  Panel chrome decisions for initial loading, media presence,
  playback/fullscreen disabled states, wake-lock intent, back-to-library
  visibility, and advanced-control gating now also live in a tested pure helper.
  Legacy stacked advanced playback controls now live in a focused
  `StackedAdvancedControls` component with direct tests, keeping
  `NavigationControls` centered on control grouping while preserving the
  existing non-compact Web reader controls. Text item activation, chunk
  fallback, scroll-ratio clamping, and autoplay handoff now live in
  `web/src/components/player-panel/usePlayerPanelTextActivation.ts` with focused
  hook coverage.
- Keep generated-audiobook defaults consistent across Web and Apple. Status:
  Web Create now applies backend topic, title, genre, author, sentence,
  generated-source image, and pipeline defaults from `/api/books/options`
  through tested helper functions, preserving explicit prompt edits, including
  cleared fields, that happen before defaults arrive. Apple Create now also
  accepts multi-target backend defaults, using the first target for the native
  picker and preserving remaining de-duplicated targets in the visible
  Additional target languages field. Web Create now also passes
  `/api/books/options` supported input/output language lists into the reusable
  Narrate Ebook form, and focused component/page tests prove backend-advertised
  languages appear in the pickers even when they are not selected defaults.
  `/api/books/options` now reads and normalizes generated-source image defaults
  from backend config so Web and Apple start from the same image
  pipeline/style/context/size values. Apple Create voice inventory matching and
  preview keys now normalize language selections through the same full Apple
  language catalog used by the pickers, instead of a narrow local name map, and
  native voice previews now carry localized sample sentences across the same
  backend/Web language catalog instead of only the original six languages. The
  shared `/api/pipelines/defaults` route now records token-safe duration
  telemetry and aggregate logs for success, forbidden, and error outcomes
  without logging user ids, auth headers, tokens, job ids, or configured input
  paths. The `/api/pipelines/image-nodes/availability` route now records the
  same token-safe availability telemetry with aggregate requested, available,
  and unavailable counts, without logging image node URLs or caller identifiers.
  The shared `/api/pipelines/llm-models` route now records token-safe model
  inventory telemetry with aggregate model counts for Web and Apple picker
  loads, without logging model names or caller identifiers. The shared
  route telemetry helper owns the common duration observation and aggregate log
  formatting used by the pipeline defaults, intake, image-node, and LLM model
  routes, keeping Apple Create readiness metrics consistent while each route
  preserves its own token-safe log message. Book-options route metrics now also
  delegate duration observation through the same helper, and audio,
  saved-template, bookmark, reading-bed, and offline-export routes use the
  shared metric-plus-log wrapper while keeping token-safe
  aggregate fields such as voice inventory counts, match engines,
  template/bookmark/bed counts, export source/player types, and delete outcomes local to each route. The shared
  `/api/audio/voices` and `/api/audio/match` picker routes now record
  token-safe audio telemetry with aggregate inventory counts and match engine
  outcomes, without logging voice names, language parameters, or caller
  identifiers; inventory and match failures return generic unavailable
  responses so local voice paths, language parameters, and model names do not
  leak into Apple/Web Create errors. The shared `/api/audio` preview synthesis
  route now records the same token-safe telemetry for preview success/error
  outcomes and converts setup failures into a generic unavailable response, so
  local config paths, sample text, language parameters, and selected voice
  identifiers do not leak before synthesis fallback handling begins. The shared `/api/pipelines/llm-models` route now runs provider
  inventory discovery through FastAPI's threadpool so Web and Apple Create model
  pickers do not block the async server while configured providers are queried.
  The shared `/api/books/options` defaults route now records
  token-safe duration telemetry and aggregate logs through the shared route
  telemetry wrapper, with language/voice/default target counts for Web and
  Apple Create readiness loads and without logging configured defaults,
  language names, voice names, user ids, auth headers, tokens, or paths.
  Generated-book prepare and background-job optional metadata/cover failure
  paths now return or persist generic warnings/details, so Web and Apple Create
  job surfaces do not echo prompts, draft titles, NAS paths, image endpoints,
  job ids, or raw exception strings. The
  manifest-registered `test-backend-audio-routes` target now exercises
  `/api/audio`, `/api/audio/voices`, and `/api/audio/match` with stubbed
  synthesis, so the shared pipeline catches voice inventory and preview drift
  before Apple Create or Web creation surfaces rely on it. The
  native preview sample catalog now lives in its own Create helper file and is
  wired into the Xcode project plus creation-payload compile contract so future
  catalog changes are verified across Apple targets. Focused parity tests now
  compare Web and Apple preview samples exactly, catching subtle punctuation or
  diacritic drift as well as missing language codes. The reusable Apple
  pipeline also has a focused `make test-apple-language-catalogs` contract so
  language picker regressions can be run directly without the full Apple suite.
  Apple Create readiness preflight now verifies the live subtitle model and
  audio voice inventory response shapes with aggregate counts, catching picker
  endpoint drift before Xcode launches without logging model or voice names.
  It also validates the shared `/api/pipelines/defaults` response shape
  separately from `/api/books/options`, reporting only an aggregate config-key
  count so Web/Apple default-loading regressions fail before simulator/device
  journeys without exposing configured values. The defaults route now also
  converts config-resolution failures into a generic unavailable response with
  token-safe error telemetry, avoiding local config path leaks in Apple/Web
  Create surfaces.
  The same preflight now also checks `/api/pipelines/llm-models` separately
  from the subtitle-specific model route, again by aggregate count/shape only,
  so Web and Apple Linguist model picker drift is caught without logging model
  identifiers.
  It also validates `/api/acquisition/providers` for the book/video discovery
  provider ids, media kinds, capabilities, backend-owned default book/video
  provider ids, default-provider availability, and attended Z-Library policy
  expected by Web, iPhone/iPad, and tvOS Create pickers before simulator
  journeys start. The acquisition provider registry route now also converts
  setup/config failures into a generic unavailable response with token-safe
  telemetry, keeping local config paths and provider secrets out of Web/Apple
  Create setup errors. Apple Narrate EPUB now keeps the attended-import fallback
  selectable for policy visibility while marking it unavailable, so missing
  provider-registry responses cannot enable a direct search. The repo-owned backend manifest also pins
  `make test-backend-acquisition` to the acquisition provider and Web route
  suites so the reusable Apple pipeline backend gate keeps discovery/download
  contract coverage attached. Available local EPUB, manual-download, and NAS
  video providers now also carry token-safe `source_label` values that Web and
  Apple Create use in unavailable-source guidance, and readiness counts those
  labels so future provider-registry drift fails before simulator journeys. The
  same Apple preflight now follows the first
  available backend-owned default book/video provider id with bounded `limit=1`
  discovery calls and validates the normalized response shape plus
  queried-provider echo before simulator or device Create journeys begin. It
  also probes the no-provider Default sources fan-out for book/video discovery,
  verifying queried providers and returned candidates stay inside the
  backend-owned defaults while explicit-only providers such as `youtube_url`
  remain out of default fan-out. The
  acquisition discover route now trims, drops blanks, and case-de-duplicates
  repeated `source_id` filters before provider lookup so Web, Apple, and
  readiness callers share the same Internet Archive identifier handoff behavior.
  It also posts an empty `/api/pipelines/image-nodes/availability` request and
  validates only the aggregate response shape, catching Draw Things
  availability contract drift without probing or logging configured node URLs;
  URL-normalization and probe failures now return a generic unavailable
  response with token-safe telemetry instead of exposing configured node URLs.
  The public runtime descriptor and Apple Settings Create Contract row now
  advertise the same shared defaults, LLM-model, image-node availability, and
  voice inventory routes, so older backends fail the contract check before
  simulator or device creation flows reach picker loading.
  Apple Create generated-book image settings now use the same image-node
  availability route for configured image API URLs and show only aggregate
  available/unavailable counts before illustrated jobs are submitted.
- Keep Zustand selectors granular to avoid wide re-renders. Status:
  App shell Zustand subscriptions now use field/action selectors in `App`,
  `useAppAuth`, `useAppJobs`, and `useAppNavigation`, avoiding whole-store
  subscriptions while preserving existing job, auth, prefill, and player
  routing behavior. Job copy/move and player-open handlers now also read the
  current job entry through the store's `getJob` selector at click time instead
  of capturing the derived jobs record only for callback lookups. The Jobs
  store now uses Zustand's `createWithEqualityFn` entry point so the equality
  selectors remain explicit without deprecated runtime warnings. The repo-owned
  Web pipeline contract pins this pattern so future shell refactors keep
  subscription scope explicit.
- Use visual redesign work only after the core component ownership is smaller.

### Milestone 4: Expand Native Creation

After Narrate Ebook:

- Subtitle job creation on iPad/iPhone. Status: Apple Create submits existing
  server-side subtitle paths or local SRT/VTT/ASS uploads with languages,
  output format, timing, output toggles, provider/model selection, ASS
  typography, transliteration mode/model, LLM batch-size tuning, and
  worker/render batch-size tuning, mirror-to-source control, and pre-submit TV
  metadata lookup plus job label/show/season/episode/title/airdate edits
  through `/api/subtitles/jobs`; the native metadata section now also exposes
  an editable lookup filename before lookup/refresh plus TV metadata cache
  clearing, editable TVMaze poster/episode-still artwork URL previews, and
  TMDB/IMDb ID edits. Server-side ASS sources now stay visible in Apple Create
  too, while SRT/VTT remain preferred defaults when available to match Web
  source selection, and Apple Create can delete selected backend subtitle
  sources through the same cleanup endpoint Web uses. Native time fields validate and normalize Web-style
  `MM:SS`, `HH:MM:SS`, and `+offset` values before submit. Subtitle TV
  metadata lookup now ignores stale responses after the lookup source changes
  or metadata is cleared, so slow previews cannot overwrite the current
  reviewed metadata draft.
- Generated book job creation on iPad. Status: Apple Create submits
  generated-book jobs through `/api/books/jobs`; generated-book mode now also
  exposes source-book title, author, genre, and summary context on iPhone/iPad
  and sends those fields through the shared generator contract so
  continuation-style jobs can start with explicit source metadata. The Create
  Book backend now normalizes that source context once per request and reuses it
  for sentence prompts, metadata, config, and pipeline snapshots so Web previews
  and Apple job submissions stay aligned; Narrate EPUB can delete selected
  backend EPUB sources through the same `/api/pipelines/files` cleanup endpoint
  Web uses; `/api/books/jobs` enqueue tests now pin the trimmed source-context
  snapshot before the background worker starts. Apple Create readiness preflight
  now also requires sane generated-book sentence bounds, language, voice, and
  pipeline defaults from `/api/books/options`, and the native Create readiness
  journey opens Generate before the media modes, scrolls as needed, and types a
  source-book continuation context so unattended iPhone/iPad simulator checks
  prove the generated-book controls are drivable. The shared pipeline also has
  a focused `make test-apple-create-readiness-contract` gate for the preflight
  parser/default-source/default-settings contract; the preflight now also calls
  the content-index endpoint for the preferred newest EPUB so the Apple Load
  Chapters path is checked before Xcode launches. Apple Create also infers
  missing chapter end sentences from the next chapter start or total sentence
  count so content-index payloads with start-only chapters still produce useful
  chapter-range selections, accepts zero-based first-chapter indexes as
  sentence-1 selections, and benefits from the shared picker walker following
  visible symlinked NAS collection folders so EPUB choices stay visible on
  Apple devices when the backend books root is organized through Finder-style
  links. Apple Create now also trusts the backend-scoped `ebooks` list when
  rendering server EPUB choices, rejecting only explicit directories and empty
  paths, so valid picker rows remain visible even if older or partial source
  metadata omits the `.epub` suffix or display name. Apple Create now also
  ignores stale chapter-index responses after the selected EPUB changes or the
  chapter state is cleared, so slow Load Chapters results cannot replace the
  current source's chapter picker. Acquisition-provider and server EPUB picker
  refreshes now use newest-request-wins guards, and EPUB delete/upload actions
  invalidate older list refreshes so stale NAS scans cannot reintroduce removed
  or superseded picker rows.
- YouTube dubbing as iPad-first review/submit flow. Status: Apple Create now
  exposes an iPhone/iPad YouTube Dub mode for backend/NAS video and subtitle
  files, including NAS library video/subtitle pickers, remembered base
  directories, embedded subtitle stream inspection/extraction through
  `/api/subtitles/youtube/subtitle-streams` and
  `/api/subtitles/youtube/extract-subtitles`, and
  `/api/subtitles/youtube/dub` submission with language, voice, clip-window,
  batching, provider/model, output, lookup-cache options, voice preview, and
  pre-submit TV/YouTube metadata lookup, TV/YouTube metadata cache clearing,
  editable TVMaze poster/episode-still and YouTube thumbnail URL previews,
  plus key title/channel/series/episode/TMDB/IMDb edits that are sent with the
  job. Backend TV/YouTube metadata preview and cache-clear failure paths now
  return/log generic errors without source filenames, NAS paths, video ids, or
  raw exception strings, while successful responses keep the reviewed metadata
  fields Apple and Web need for draft editing. Apple YouTube dubbing now
  resolves target languages through the shared Apple catalog code map before
  submission, matching Web's `target_language` code payloads, and keeps video
  transliteration/lookup-cache toggles separate from book job settings so
  defaults do not leak across modes. Apple Create now
  also exposes advanced metadata JSON editors for
  subtitle and YouTube jobs, so iPad/iPhone can review and apply full nested
  metadata payloads beyond the high-value native fields before submission.
  YouTube TV and YouTube video metadata lookups now ignore stale responses
  after the source changes or metadata is reset, keeping the reviewed draft
  aligned with the selected video/subtitle. The
  Download Station handoff now matches completed downloader filenames against
  refreshed manual-download discovery candidates and applies the matching
  local video/subtitle selection, reducing the post-download Apple setup loop
  without auto-selecting unrelated manual downloads. Apple Create now ignores
  stale book and video discovery responses when a newer provider/query search
  is in flight, so slow NAS/manual/YouTube/indexer scans cannot replace the
  visible candidate list after the user switches discovery sources. Embedded
  subtitle inspection now uses the same selected-source freshness guard, so
  slow stream probes cannot refill the inline subtitle list after the selected
  NAS video changes or the extraction state is reset. Subtitle-source and NAS
  video library list refreshes also ignore stale responses, and subtitle
  deletion invalidates older source-list refreshes so pickers stay aligned with
  the current backend-visible files. The
  subtitle and YouTube Dub enqueue endpoints now emit aggregate submission
  timing metrics for Apple/Web Create diagnostics without leaking NAS paths,
  language/voice choices, metadata content, user ids, tokens, or created job
  ids.
- Library source reupload on iPhone/iPad. Status: Library row context menus now
  expose Replace Source File, open a document picker for common book/video
  source files, review the selected file before upload, post it to
  `/api/library/items/{job_id}/upload-source`, and replace the refreshed row
  returned by the backend. Apple TV remains playback-first. The public runtime
  descriptor now advertises the shared Library action paths for listing,
  metadata edits, source upload, ISBN lookup/apply, and metadata enrichment, and
  the Apple client builds these paths through matching local constants.
- Library source diagnostics on Apple TV. Status: Library row context menus now
  expose read-only Source Details on Apple TV as well as iPhone/iPad, keeping
  remote navigation simple and avoiding mutation controls.
- Library ISBN metadata preview/apply on iPhone/iPad. Status: Library row
  context menus now expose Preview ISBN Metadata, fetch
  `/api/library/isbn/lookup` results in a sheet, and can then apply the ISBN
  through `/api/library/items/{job_id}/isbn` before replacing the refreshed row
  returned by the backend.
- Apple TV gets read-only job templates or retry controls only if remote navigation stays simple.
  Status: Apple Jobs on iPhone, iPad, and Apple TV now expose a Restart Job
  context-menu action for failed/cancelled pipeline and book jobs, posting to
  the existing `/api/pipelines/jobs/{job_id}/restart` backend action and
  replacing the visible row with the restarted pending job after confirmation.
  The backend job-action route helper now returns a clean 400 for unsupported
  restart requests, such as non-restartable job types or missing request
  payloads, so Web and Apple callers see an actionable client error rather
  than an internal server failure.
  Apple Narrate EPUB source controls now distinguish an empty backend EPUB
  inventory from a hidden picker, and the shared content-index route returns a
  stable 422 when an EPUB cannot be read instead of allowing parser failures to
  escape the web request.
  Apple Create saved-template pickers now show compact read-only details for
  the selected template, including job type, last update, saved-field count,
  and token-safe discovery provider/source kind, so Apple TV can browse
  templates without a separate remote-heavy detail flow or exposing paths,
  URLs, candidate ids, or filenames.

## Feature Backlog

Suggested features to evaluate after parity scaffolding:

- Discovery acquisition layer: search lawful video/book sources, acquire or
  locate artifacts, enrich metadata, and hand prepared sources to Web/Apple
  Create. Status: in progress in
  `docs/plans/discovery-acquisition-layer.md`, with Z-Library/shadow-library
  automation explicitly out of scope; current provider work covers YouTube
  search, explicit pasted YouTube URL/video-id metadata handoffs, existing
  NAS/yt-dlp flows, Download Station/Prowlarr-style lawful handoff,
  public-domain/open ebook sources, token-safe response serialization, and
  sentence-splitting quality gates.
- Cross-surface job templates: save a Web configuration and reuse it from Apple. Status:
  backend now exposes authenticated `/api/creation/templates` list/save/delete
  storage with recursive secret-key stripping, and the public runtime descriptor
  advertises the template endpoints for Web/Apple clients. The shared template
  routes now record token-safe duration telemetry for list/save/delete success,
  unauthorized, and error paths with aggregate counts/delete outcomes only,
  without logging template ids, names, payload content, mode filters, user ids,
  auth headers, or tokens. Unknown template mode filters now return an empty
  list without loading stored templates instead of silently falling back to
  generated-book templates; the route also resolves known aliases to canonical
  modes before calling the service, keeping Apple/Web mode pickers from showing
  the wrong saved configuration or doing avoidable storage reads. Corrupt
  per-user template storage now recovers malformed JSON and structurally
  invalid payloads as an empty list with a generic service warning that omits
  storage paths, user fragments, filenames, and raw JSON content. Web Narrate Ebook and
  generated-book forms can now save sanitized creation templates from their
  current settings. Native Apple Create on iPhone/iPad can list those saved
  generated-book and Narrate EPUB templates, apply the Web form state into its
  source, language, narration, output, image, metadata, and worker controls, and
  delete stale saved templates after review. Applied fields are marked as edited
  so later backend/history defaults do not overwrite them. Applied book
  templates now also restore token-free `discovery_state` into Apple acquisition
  metadata extras, so selected source provenance survives save/apply/save,
  submit, and Web handoff loops without persisting acquisition tokens. Web
  Narrate Ebook also restores sanitized `discovery_state` when applying saved
  discovery-backed templates, so Web apply/save loops keep source provenance
  instead of dropping it after the first re-save; those templates also reopen
  the Web Discovery source tab so the visible source mode matches the preserved
  provenance. Saved Create templates now pass nested string values through the
  shared acquisition URL-safety helper too, so discovery-state URLs keep public
  catalog/indexer context while dropping user-info credentials, private tracker
  query keys, and token fragments before Web or Apple reuse. Web and Apple
  Create now also scrub those URL parts client-side while building saved
  book/video discovery template drafts, keeping transient template state aligned
  with the backend guard. Apple subtitle and YouTube metadata drafts now also
  use the same recursive template-safety normalization before apply/save paths,
  matching Web's metadata-template sanitizer. The Apple contract gate now reads
  the backend, Web, and Apple sanitizer sources directly and compares their
  sensitive-key markers plus public URL schemes, so template/offline-export URL
  scrubbing policy cannot drift silently between surfaces. Web
  Video Dubbing and Apple YouTube Dub templates now also persist token-free
  video `discovery_state` for reviewed NAS/manual/YouTube/indexer candidates,
  preserving provider, candidate id, selected paths, rights, and source kind
  without saving candidate tokens. Web Video Dubbing and Apple YouTube Dub also
  restore that token-free video discovery provenance when applying saved
  templates, so apply/save loops keep reviewed source context instead of
  dropping it after the first save. Web and Apple Create now also merge prepared
  artifact metadata into book/video discovery state after local handoffs, so
  normalized source provider, acquisition provider, acquisition candidate id,
  and source kind survive template save/apply loops without storing acquisition
  tokens; prepared manual/download handoffs preserve upstream provider values
  from signed artifact tokens instead of replacing them with the local inbox
  provider. Apple Create also applies saved subtitle and
  YouTube dubbing templates into source, language, model, timing, output,
  metadata JSON, and tuning controls. Web Subtitle Tool and Video Dubbing can
  now save sanitized subtitle and YouTube templates from their current settings
  for Apple reuse. The Apple Create
  readiness preflight now calls `/api/creation/templates` and validates the
  shared list response shape, catching endpoint/auth regressions without
  requiring existing saved templates or mutating user data. It also probes the
  authenticated single-template route with a synthetic missing id and treats a
  clean 404 as route-ready, so template detail, Web handoff, and delete-route
  drift is caught before simulator or device runs without reading real drafts.
  Creation-template detail lookups now scan raw stored ids and normalize only
  the matching payload, avoiding unnecessary sanitization work for unrelated
  saved drafts during Web and Apple handoffs. Missing creation-template deletes
  now use the same raw-id scan before normalizing payloads, so stale Web/Apple
  cleanup requests can return without touching unrelated saved drafts. Apple
  Create now treats a missing saved-template delete as stale local state,
  pruning the row and resolving selection instead of leaving a dead template
  with a generic error. Filtered creation-template lists now scan raw stored
  modes before normalizing payloads, so mode-specific Web/Apple template
  pickers avoid touching unrelated saved drafts. Apple Create now requests
  saved templates with the current canonical job mode and refreshes on mode
  changes, dogfooding the lighter backend template filter from iPhone, iPad,
  and TV. Apple Create readiness now probes all canonical mode-filtered
  saved-template lists, catching regressions in every lighter template picker
  route before simulator or device deployment. Apple contract tests now compare
  backend creation-template modes, Apple Create mode mapping, and readiness
  mode probes so future template modes cannot drift silently between surfaces.
  Changed-test selection now routes creation-template backend schema/service/route
  edits through backend template tests plus Apple contracts, so the cross-surface
  template-mode guard runs on the changes that can break it. The same contract
  now includes Web's creation-template DTO mode union, and shared Web DTO edits
  route through the focused Web template gate plus Apple contracts. Runtime
  descriptor contracts also verify Web's creation-template client path against
  the canonical backend Create template route, so Web template-client edits run
  Apple contracts before deploy preflight. The runtime descriptor contract now
  also compares Web's generated-book options/jobs client paths with the
  canonical backend Create routes, so those shared API edits run focused Create
  plus Apple contract gates. The same runtime descriptor contract now compares
  Web's acquisition discovery/download handoff client paths with the canonical
  backend Create routes, so Web jobs API edits run Apple contracts. It also
  compares Web's subtitle and YouTube Create client paths with the canonical
  backend/Apple routes, so Web subtitle API edits run both focused subtitle/video
  gates plus Apple contracts. Runtime descriptor contracts also compare Web
  media and resume client paths with the canonical Apple playback/export routes,
  so Web media/resume API edits run focused Web gates plus Apple contracts. The
  same runtime descriptor coverage now compares Web Library action/media client
  paths with the canonical Apple Library routes, so Web Library API edits run
  focused Library plus Apple contracts. Runtime descriptor contracts now also
  compare Web auth login/OAuth/session client paths with the canonical Apple
  auth routes, so Web auth API edits run focused auth plus Apple contracts.
  Changed-test selector tests now derive Web clients from the runtime descriptor
  contract and require Apple contracts for each, keeping future Web/Apple parity
  additions wired into the pipeline. The standalone Apple runtime payload
  checker is now guarded from the backend descriptor constants across every
  public section, including exact array values, so simulator/device preflights
  catch non-Create contract drift too. The Apple runtime descriptor model guard
  also parses Swift contract fields and checks each section's required/optional
  fields against backend descriptor constants, catching partial decode-model
  updates before simulator or device preflights. Apple runtime contract constants
  now expose auth token transport, pipeline cache-buster query names, and offline
  export player-type arrays as Swift constants, with tests comparing every
  advertised backend descriptor value against the Apple clients. Web auth and
  resume clients now use a shared runtime-contract route module mirrored from
  `/api/system/runtime`, and changed-test selection treats that module as both
  Web and Apple contract-sensitive. Web media, live-media, bookmark,
  bookmark-delete, and offline-export create calls now use that same shared
  runtime-contract route module, extending backend/Web/Apple path parity into
  playback-focused Web tests. Web Library item, move/remove, upload-source,
  ISBN, enrichment, and Library-media calls now use the shared runtime-contract
  route module too, keeping Web Library routes aligned with backend and Apple
  clients. Web generated-book options/jobs and creation-template list/detail
  calls now use that same module, bringing another Create handoff slice under
  backend/Web/Apple path parity. Web acquisition provider, discovery, acquire,
  prepare, and downloader job calls now share those runtime-contract routes
  with Apple Create too, with focused Web jobs tests covering encoded
  artifact/task ids. Web subtitle source, YouTube dubbing, subtitle job, and
  assistant lookup calls now use shared runtime-contract constants too, with a
  direct API-client test covering encoded source/video queries. Web pipeline
  file/default/intake/content-index/upload/LLM/image-node helpers and voice
  inventory now use the shared Create runtime contract too, with focused Web API
  tests covering encoded source paths. Web voice preview synthesis and media
  search now use shared Linguist/Create runtime-contract routes, with focused
  media API tests covering encoded search queries. Web pipeline submit/list/
  status/restart/delete/event, timing, and lookup-cache helpers now use the
  shared Create/PipelineJobs/PipelineMedia/Linguist runtime contracts too, with
  focused Web tests covering encoded job and lookup terms. Web subtitle model,
  metadata fetch, and TV/YouTube metadata cache-clear helpers now use shared
  Create/PipelineMedia runtime-contract routes too, with focused Web tests
  covering encoded subtitle job ids.
- Draft jobs: start on iPad, finish advanced settings on Web. Status:
  the shared creation-template contract now supports authenticated single-template
  reads at `/api/creation/templates/{template_id}` with the same sanitized,
  user-scoped payload shape as list/save; Web and Apple clients both expose the
  single-template fetch primitive, and Apple encodes template path components
  without letting `/`, `?`, or `#` split the route. Web `?view=...&template_id=...`
  handoffs now fetch the saved template after login and apply compatible
  Narrate Ebook or generated-book form state into the selected creation surface;
  generated-book templates also carry sanitized prompt fields (topic, book name,
  genre, author, sentence count) so "continue this book" drafts restore both
  the source prompt and narration settings. Web Subtitle Tool and Video Dubbing
  also apply deep-linked saved templates into source, language, timing, output,
  metadata, model, and tuning controls. Native Apple Create appends the selected
  compatible template id when opening Web Create for all creation modes, letting
  iPad/iPhone hand saved drafts into the advanced Web forms. Native Apple
  Create can now save the current generated-book, Narrate EPUB, subtitle, or
  YouTube dubbing settings as the same Web-compatible template payload shape,
  selects the saved template immediately, and preserves generated-book source
  context for continuation-style drafts before Web handoff. The shared delete
  route now returns the same canonical template id shape that save/list/get
  expose, Apple decodes that response before pruning local template state, and
  shared get/delete routes both skip service storage calls for empty normalized
  ids, keeping Web and Apple draft cleanup predictable even when a handoff URL
  carries an encoded display-style id.
- Creation handoff: Apple app opens the corresponding Web creation URL for unsupported advanced options. Status:
  iPhone/iPad Apple Create now exposes Open Web Create, derives a token-free Web URL from the configured API base,
  and maps native creation modes to validated Web `?view=` deep links. The
  shared Create-readiness journey now also verifies the native Web handoff
  button is reachable after driving generated-book, subtitle, and YouTube
  default settings.
- Job health timeline: show backend stage durations and slow phases in Web and iPad. Status:
  Apple Jobs rows now surface the latest backend stage with elapsed runtime
  and ETA from progress events, giving iPad/iPhone a compact health signal
  while jobs are running. Web job details now show the same compact active-job
  health row near the lifecycle timing summary, formatting backend stage names
  with the shared acronym set and elapsed/ETA durations before users scroll
  into the detailed progress grid.
- Backend queue pressure indicator: expose accepting/backpressure state in Settings before users submit long jobs. Status:
  Web admin System status now shows job intake state, pending queue depth,
  active running jobs, and soft-limit warnings from the backend
  `/api/admin/system/status` response; `/api/pipelines/intake/status` now
  exposes a narrower authenticated editor/admin-safe queue snapshot for
  creation surfaces; Web book creation and Apple Create display that status
  before submit, show a loading state while the snapshot is checked, include
  delayed-job and soft/hard-limit details, warn under pressure, block
  submission when the backend hard queue limit is reached, and refresh the
  snapshot after successful enqueue. Web Subtitle Tool and Video Dubbing now
  reuse the same intake callout and capacity gate before enqueueing their own
  long-running jobs. The intake status route now records token-safe duration
  telemetry and aggregate logs for success, forbidden, and error outcomes
  without logging user ids, auth headers, tokens, job ids, or backend exception
  details; route-level queue-inspection failures return a generic unavailable
  response so Apple/Web Create surfaces do not expose local queue internals. The shared
  pipeline backend gate now includes the focused system-route pytest, and Apple
  Create readiness preflight validates the intake response shape before Xcode
  launches without failing solely because a shared backend is under queue
  pressure. Web creation surfaces and Apple Create now also ignore stale
  queue-pressure refresh responses when a newer request is in flight, so a slow
  initial snapshot cannot overwrite the post-submit intake state shared by
  Narrate Ebook, Subtitle Tool, Video Dubbing, and native Create. Apple Create
  saved-template refreshes now use the same newest-request-wins guard, so slow
  mode-filtered responses cannot replace the visible Generated Book, Narrate
  EPUB, Subtitle, or YouTube Dub template list after the user switches modes.
- Smart resume cards: show "continue listening", "newly completed", and "needs attention" across all surfaces. Status:
  Apple browse rows now surface local-only, iCloud-only, and synced resume
  evidence in the shared Library/Jobs/search row badge instead of hiding valid
  local fallback resume points; synced badges display the freshest stored
  resume point so iPhone, iPad, and tvOS list surfaces agree with the playback
  resume decision. Web Library rows now also read the existing per-job
  `media-memory:<job_id>` session resume cache and display a compact Continue
  badge next to the status badge without adding an extra list-time API
  waterfall. The Web resume client now mirrors Apple by trimming, de-duplicating,
  sorting, and encoding visible row IDs before calling `/api/resume`, and skips
  the network call entirely when an explicit visible row set contains no valid
  IDs so blank rows cannot trigger an accidental unfiltered resume scan. The
  backend resume route and filesystem/Postgres services now apply the same
  trimmed de-duplicated filtered-ID guard, so custom callers cannot reintroduce
  padded duplicate lookups, explicit-empty fallback scans, or divergent backend
  behavior. The
  public runtime descriptor now advertises bookmark and resume
  playback-state paths, including the batch resume list endpoint, so Apple and
  shared-pipeline preflights can catch playback-state contract drift; Apple
  Settings also surfaces this playback-state contract in the Create readiness
  journey so simulator checks validate the routes the app uses for bookmark and
  resume sync. The public runtime descriptor now also advertises the pipeline
  media-search path used by Apple playback search, and Apple Create readiness
  validates the full 32-path Create contract including acquisition job polling
  endpoints before simulator journeys run. The standalone Swift runtime
  descriptor payload check now decodes and asserts every Create descriptor path,
  using the backend's current camelCase descriptor shape while retaining a
  legacy snake-case smoke payload without pipeline metadata, keeping the
  compiled contract fixture aligned with backend descriptor changes.
  Apple API clients now share a route-component encoder that
  escapes `/`, `?`, and `#` for playback-state, Library, media, lookup,
  event-stream, notification, Create template, and acquisition artifact/job
  paths, including library media file URLs produced by the streaming resolver,
  and lookup-cache word paths, matching Web `encodeURIComponent` semantics so
  unusual job/bookmark/chunk/token/template/artifact IDs, looked-up words, or
  media path segments cannot split backend routes. Web jobs and media API clients now also encode pipeline status,
  action, metadata refresh, event-stream, media, and live-media job IDs before
  routing so both app families preserve the same path-component contract. Apple
  Library and Jobs list refresh now batch-fetch backend
  resume evidence for the visible row IDs through the shared snapshot provider,
  preserving the same local/iCloud badge decisions while avoiding one request
  per row. The filesystem resume service now resolves filtered `GET
  /api/resume?job_id=...` requests through direct per-job reads and sorts before
  applying the limit, so Web/Apple list badges do not scan every stored resume
  file and still return the freshest requested entries first. Corrupt resume
  storage now recovers as an empty state with a generic service warning that
  omits job ids, user fragments, storage paths, filenames, and raw JSON content
  across direct resume lookups and filtered list reads. The repo-owned
  `test-backend-playback-state` target now covers resume routes, bookmark
  routes, and the optimized filtered resume service path, and the shared Apple
  backend pipeline manifest runs it as a playback-state regression gate.
  Bookmark list/add/delete routes also record token-safe route duration metrics
  and logs through the shared route telemetry wrapper with only operation,
  result, count, and deleted facts, keeping user, job, bookmark, and payload
  identifiers out of playback-state observability. Corrupt bookmark storage now
  recovers as an empty list with a generic service warning for malformed JSON
  and structurally invalid payloads while omitting job ids, user fragments,
  storage paths, filenames, and raw JSON content. The
  shared MyLinguist read-aloud action now pauses active Apple playback before
  speaking and cached-narration playback stops any in-flight pronunciation task,
  keeping Apple TV video lookup, iPhone/iPad interactive lookup, and narration
  resume handoffs from competing for audio. Backend pronunciation bytes that
  cannot start in `AVAudioPlayer` now fall back to platform speech instead of
  leaving Apple TV/iOS lookup read-aloud or Create voice previews silent.
  The shared basic playback journey now asserts the Apple TV Return to Now
  Playing control immediately after backing out of playback, so simulator
  smoke runs catch regressions where the menu has no direct route back to the
  active item.
  Web Library rows now also add compact `Newly completed` and
  `Needs attention` secondary badges beside the existing status and Continue
  badges, and Apple Library/Jobs/search rows reuse the shared resume-status
  chip for the same fresh-completion and missing-media cues when no local or
  cloud resume evidence is present. This gives iPhone, iPad, Apple TV, and Web
  the same quick-scan treatment for resume-ready, newly ready, and attention
  rows.
  Lookup-cache full, summary, word,
  and bulk routes now record token-safe playback-state telemetry and aggregate
  logs through the shared route wrapper for success, unavailable, not-found,
  forbidden, cache-hit, and cache-miss outcomes without logging job ids, user ids,
  queried words, definitions, languages, or audio paths, and
  corrupt lookup-cache files now recover as unavailable/empty caches with
  generic service warnings that omit cache paths, job ids, source languages,
  definition languages, audio paths, and raw JSON content. The
  `test-backend-playback-state` covers the route family used by Web MyLinguist
  plus Apple online/offline lookup. Reading-bed
  list/fetch/upload/update/delete routes now record token-safe duration
  telemetry and aggregate logs for success/error/unauthorized/not-found paths
  without logging bed ids, labels, filenames, paths, auth headers, or tokens.
  Uploaded reading-bed fetch, upload-size validation, and cleanup now use the
  shared tolerant stat helper, so Web/Apple background-music controls and admin
  storage updates do not race on direct file-existence checks.
  The
  repo-owned `test-backend-playback-media` target now covers job media
  manifests, Library media manifests with sentence metadata, Library serializer
  chunk ordering, token-safe media route timing, diagnostics counts, and ranged
  Library file streaming used by Web playback plus Apple Job/Library playback,
  and the shared Apple backend manifest runs it as a playback-media regression
  gate. The
  repo-owned `test-backend-reading-beds` target now also covers the
  reading-bed catalog, admin upload/default update, uploaded file streaming,
  cleanup fallback, and token-safe stale-file fetch logs through the shared
  route wrapper used by Web playback controls plus Apple playback and offline
  sync, and the shared Apple backend manifest runs it as a
  reading-bed regression gate. The repo-owned `test-backend-notifications`
  target now covers Apple Settings notification device registration,
  preferences, test sends, rich test sends, disabled-server messaging, and
  authentication guards without APNs credentials, plus token-safe
  NotificationService/APNs logging that omits user IDs, job IDs, device names,
  and APNs token prefixes; the shared Apple backend manifest runs it as a
  notification regression gate.
- Shared media diagnostics: surface missing timing/audio/image assets without
  opening logs. Status: media manifest responses now include a token-safe
  aggregate diagnostics object with media, chunk, audio, image, timing,
  metadata, URL, and size counts; Web Job Detail now shows a compact manifest
  health strip when diagnostics are available. Apple playback decodes the same
  aggregate counts but keeps the native strip hidden during healthy playback,
  surfacing it only when diagnostics report media gaps so device chrome stays
  focused on reading and playback controls. Manifest-provided `size`,
  `size_bytes`, and `sizeBytes` values now count as known sizes for URL-backed
  or persisted media entries, avoiding false missing-size warnings when a file
  cannot be statted locally. Web Job Detail now also counts chunks without files
  as media gaps, matching Apple playback's warning-only diagnostics semantics
  for manifests that may skip sections.
- Offline export from Apple: request `/api/exports` for a completed job/library
  item and show status in Jobs. Status: Apple Jobs and Library rows can request
  offline player exports for completed media, disable duplicate export requests,
  open the returned download URL, and now show a visible Creating offline
  export progress overlay while the backend archive is being prepared. Export
  busy state is tracked per source row so one archive request does not disable
  unrelated completed jobs/library items while still preventing duplicate
  requests for the same source. The
  public runtime descriptor now also advertises the offline export create path,
  download URL template, supported source kinds, and player type so Apple and
  shared pipeline preflights can detect export contract drift. Apple Settings
  and the Create readiness journey surface the Library action and offline
  export descriptor sections alongside Create so simulator checks catch drift
  before device deployment. The Apple offline-export client now has a shared
  download-route helper that substitutes the advertised runtime template, so
  future native download handling can reuse the same encoded route contract
  instead of deriving it ad hoc. The shared pipeline backend manifest now pins the
  offline export `sourceKinds` and `playerTypes` list values as well as the
  export URLs, so reusable backend preflight fails if the Web/Apple offline
  player payload contract changes. The manifest-registered
  `test-backend-offline-export` target now exercises the `/api/exports` create
  and download routes, including missing-download handling, token-safe logging,
  and Prometheus timing metrics through the shared route wrapper, so Apple
  export actions are covered by the regular backend pipeline. Offline export
  manifest metadata now also reuses the shared acquisition URL-safety policy to
  drop sensitive keys and scrub credential-bearing public URLs recursively,
  protecting older persisted jobs before Apple/Web offline players receive
  their manifest. The repo-owned `test-backend-offline-export` target now runs
  that manifest sanitizer test alongside export route coverage so reusable
  Apple pipeline validation owns both the route contract and archive payload
  safety.
- Apple Jobs/Library action route contract. Status: Apple jobs list/status,
  SSE event stream, delete/restart, and Library move/remove endpoints now use
  shared client runtime helpers. The public runtime descriptor advertises both
  Jobs action routes and Library action routes, and Apple Settings/readiness
  checks compare them before simulator or device deployment.
- Apple playback media/linguist route contract. Status: Apple media,
  live-media, chunk, library media, timing, subtitle metadata, lookup-cache,
  assistant lookup, and audio synthesis paths now use route helpers. The public
  runtime descriptor advertises the playback media and linguist endpoints, and
  Apple Settings/readiness checks compare them before simulator or device
  deployment.
- Status: Apple auth/playback-state preflight contract now advertises OAuth,
  session, bookmarks, reading-bed, and resume paths in the public runtime
  descriptor, routes Apple auth/playback-state calls through shared helpers,
  surfaces Auth Contract plus Playback State Contract rows in Settings, and
  includes auth/playback-state descriptor drift checks in Create readiness.
- Status: Apple notification preflight contract now advertises notification
  device registration/removal, test, rich-test, and preference endpoints in the
  public runtime descriptor, surfaces the Notification Contract row in Settings
  and the Create readiness journey, and routes Apple notification client calls
  through shared helpers.

## Verification Contract

Every cross-surface change should pass the relevant subset:

- Backend: targeted `pytest` for touched routers/services, including the
  manifest-registered saved creation-template route slice when template
  behavior changes.
- Web: focused Vitest files plus a production/export build. Use the package
  manager available in the checkout, for example `npm --prefix web test -- --run
  ...` and `npm --prefix web run build`; the Web build script should remain
  package-manager neutral. For ebook-tools, prefer
  `make apple-pipeline-backend-tests`, which runs the manifest registered
  backend pytest bundle through the shared pipeline runner with generated-cache
  cleanup, and `make apple-pipeline-web-checks`, which calls the shared pipeline runner for
  the registered Create, saved-template, Sidebar, Library, Job Progress, Playback, Video
  Dubbing, and Subtitle Tool focused checks, production/export build, and generated-artifact
  cleanup. The repo-side shared-pipeline manifest validator now requires the full
  repo-owned backend and Web checkpoint target inventories, and the Web pipeline
  contract pins those manifest commands so a newly split focused gate cannot drift
  out of the reusable Apple pipeline. The manifest validator also checks every
  declared `make` command against the local Makefile target table, so a typo or
  stale target name fails before shared-pipeline orchestration dry-runs. It also
  requires the UI-test and macOS iPad-style app-owned journeys, keeping those
  newer local-surface lanes in the reusable manifest contract. The same validator
  now compares `APPLE_PIPELINE_JOURNEY_PROFILES` plus the default journey with
  the manifest app-owned journey map, and compares `APPLE_PIPELINE_SMOKE_PROFILES`
  plus the default smoke profile with the manifest simulator profiles, so
  aggregate and single-profile dry-runs cannot miss a registered local lane.
- Apple: release contract, including Markdown/in-app changelog day, visible
  date label, release version, plist, Xcode, and journey badge consistency,
  exposed as `make test-release-version` and inherited by
  `make test-apple-contracts`, the Web production/export build plus Apple local verification via the
  cross-surface checkpoint gate, iOS/tvOS simulator builds, the
  iPhone/iPad simulator compile lanes, the iOS UITest build-for-testing lane,
  the tvOS simulator compile lane, the tvOS UITest build-for-testing lane, the
  office-iPad local build/verification gates, the local Apple surface build gate,
  the local Apple verification gate,
  `make apple-device-preflight`,
  `make apple-device-signed-build-only`, `make apple-device-deploy-dry-run`,
  `make apple-device-full-entitlement-plan`,
  `make apple-device-full-entitlement-stable-install`,
  `make apple-device-full-entitlement-fallback-install`, guarded CoreDevice
  preflight before confirmed physical-device updates,
  `make apple-runtime-fast-forward` plus `make apple-runtime-ssh-check` for
  the remembered `fifo@192.168.1.9:/Users/fifo/Projects/home/ebook-tools`
  Mac Studio runtime checkout, shared Apple pipeline preflight targets
  whose aggregate runs contract/backend-health/backend-pytest/Web checks plus
  simulator/journey orchestration dry-runs without source-sync or
  physical deployment, `make verify-apple-dogfood-pipeline` when a change needs
  the repo-owned Web/Apple cross-surface checkpoint plus the shared pipeline
  aggregate in one non-physical gate, with the cross-surface checkpoint now
  running the shared backend manifest slices plus focused Web manifest checks,
  full Vitest, the Web production/export build, and Apple local-surface
  verification,
  `make verify-apple-golden-pipeline`, which runs the Mac Studio runtime
  fast-forward, SSH check, and source-sync before that dogfood gate, repo-owned
  shared simulator-smoke dry-runs, explicit app-owned journey listing, and
  app-owned-journey dry-runs including
  `make apple-pipeline-orchestration-dry-runs`, and shared pipeline simulator
  smokes. Apple E2E Xcode runs now go through
  `scripts/run_xcodebuild_e2e.py`, which preserves the last-30-lines output and
  retries once only for the known `mobile.notification_proxy` secure-connection
  simulator service failure after cleaning stale result/DerivedData paths, so a
  pre-app Xcode service hiccup does not masquerade as a tvOS Music-bed
  regression. Job and Library interactive autoplay now validates tracked
  resume/start sentences against the loaded job, lets start-only placeholder
  chunks resolve their first sentence for metadata hydration, and shares a
  longer bounded retry schedule, so stale Library sentence trackers or slow
  tvOS chunk metadata hydration can still load reader audio before
  Music-bed E2E assertions expect `reader=playing`. June 30 dogfood evidence: after the stricter TV first-pause verifier
  and documentation pins, `make verify-apple-shared-pipeline` passed through
  the reusable pipeline runner at `1010eb5fe` as part of
  `make verify-apple-living-room-candidate`. The run checked live backend
  health/runtime, all manifest-owned backend pytest slices, focused and full
  Web Vitest checks, the Web production/export build, Apple contract groups,
  iPhone/iPad/tvOS/Cinema simulator-smoke dry-runs, app-owned journey listing,
  and app-owned dry-runs for iPhone, iPad, tvOS, Create-readiness,
  Music-bed-sync, UITest-build, runtime Xcode readiness, and local Mac
  iPad-style profiles without booting simulators, loading remote secrets, or
  touching physical devices. The Living Room candidate then ran the live tvOS
  Music-bed simulator journey and passed one test with zero failures and zero
  skipped tests after the setup-recovery timers were guarded against real reader
  transport commands. The dry-run registry expanded both
  `make test-e2e-ipad-music-bed-sync` and `make test-e2e-tvos-music-bed-sync`,
  while live Music-bed simulator evidence remains tracked in the dedicated
  playback sections. On July 1, the Cinema TV candidate added a Music-bed
  watchdog reassertion for reader-owned pauses after physical logs showed
  repeated broker pauses without an intervening explicit reader play; `make
  test-e2e-tvos-music-bed-sync` passed 1/1 with 0 failures and 0 skipped before
  any physical redeploy. Playback media manifest loading also moved lazy chunk
  manifest checks onto the NAS-tolerant stat helper so Web and Apple playback
  routes avoid direct existence checks on flaky job metadata roots. Later on
  July 1, `make verify-apple-shared-pipeline` passed again at `0b0a25cb9`
  after the reader started preserving active original-only or translation-only
  mode across chunk/batch setup; the reusable run covered backend
  health/runtime, manifest-owned backend pytest slices, focused/full Web
  Vitest, the Web production/export build, Apple contract groups,
  iPhone/iPad/tvOS/Cinema simulator-smoke dry-runs, and every app-owned
  journey dry-run without touching physical devices. After the reader transport resolver
  centralization and duplicate-window cleanup at `41668756`, the live
  simulator journeys were re-run on June 29, 2026: `make
  test-e2e-tvos-music-bed-sync` passed 1/1 with 0 failures and 0 skipped, and
  `make test-e2e-ipad-music-bed-sync` passed 1/1 with 0 failures and 0 skipped,
  giving fresh unattended evidence before any iPad Pro or Living Room TV
  physical-device deployment.
- Pipeline: `check_app_source_sync.py`, `check_app_backend.py`, and deploy-delta tests when version/deploy ledger changes.

Physical device deployment remains attended and explicit only.
