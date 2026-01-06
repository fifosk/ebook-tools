export type PipelineJobStatus =
  | 'pending'
  | 'running'
  | 'pausing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type PipelineFileEntryType = 'file' | 'directory';

export interface PipelineFileEntry {
  name: string;
  path: string;
  type: PipelineFileEntryType;
}

export interface PipelineFileBrowserResponse {
  ebooks: PipelineFileEntry[];
  outputs: PipelineFileEntry[];
  books_root: string;
  output_root: string;
}

export interface PipelineDefaultsResponse {
  config: Record<string, unknown>;
}

export interface BookContentIndexResponse {
  input_file: string;
  content_index: Record<string, unknown> | null;
}

export interface ImageNodeAvailabilityRequestPayload {
  base_urls: string[];
}

export interface ImageNodeAvailabilityEntry {
  base_url: string;
  available: boolean;
}

export interface ImageNodeAvailabilityResponse {
  nodes: ImageNodeAvailabilityEntry[];
  available: string[];
  unavailable: string[];
}

export interface MacOSVoice {
  name: string;
  lang: string;
  quality?: string | null;
  gender?: string | null;
}

export interface GTTSLanguage {
  code: string;
  name: string;
}

export interface VoiceInventoryResponse {
  macos: MacOSVoice[];
  gtts: GTTSLanguage[];
}

export interface PipelineInputPayload {
  input_file: string;
  base_output_file: string;
  input_language: string;
  target_languages: string[];
  sentences_per_output_file: number;
  start_sentence: number;
  end_sentence: number | null;
  stitch_full: boolean;
  generate_audio: boolean;
  audio_mode: string;
  audio_bitrate_kbps?: number | null;
  written_mode: string;
  selected_voice: string;
  voice_overrides?: Record<string, string>;
  output_html: boolean;
  output_pdf: boolean;
  generate_video: boolean;
  add_images: boolean;
  include_transliteration: boolean;
  translation_provider?: string;
  transliteration_mode?: string;
  transliteration_model?: string | null;
  tempo: number;
  book_metadata: Record<string, unknown>;
}

export interface PipelineRequestPayload {
  config: Record<string, unknown>;
  environment_overrides: Record<string, unknown>;
  pipeline_overrides: Record<string, unknown>;
  inputs: PipelineInputPayload;
  correlation_id?: string;
}

export interface PipelineSubmissionResponse {
  job_id: string;
  status: PipelineJobStatus;
  created_at: string;
  job_type: string;
}

export interface ProgressSnapshotPayload {
  completed: number;
  total: number | null;
  elapsed: number;
  speed: number;
  eta: number | null;
}

export interface ProgressEventPayload {
  event_type: string;
  timestamp: number;
  metadata: Record<string, unknown>;
  snapshot: ProgressSnapshotPayload;
  error: string | null;
}

export interface PipelineResponsePayload {
  success: boolean;
  pipeline_config?: Record<string, unknown> | null;
  refined_sentences?: string[] | null;
  refined_updated: boolean;
  written_blocks?: string[] | null;
  audio_segments?: number[] | null;
  batch_video_files?: string[] | null;
  base_dir?: string | null;
  base_output_stem?: string | null;
  stitched_documents: Record<string, string>;
  stitched_audio_path?: string | null;
  stitched_video_path?: string | null;
  book_metadata: Record<string, unknown>;
  generated_files?: Record<string, unknown> | null;
}

export interface ImageGenerationSummary {
  enabled: boolean;
  expected?: number | null;
  generated?: number | null;
  completed?: number | null;
  pending?: number | null;
  percent?: number | null;
  sentence_total?: number | null;
  batch_size?: number | null;
}

export interface JobParameterSnapshot {
  input_file?: string | null;
  base_output_file?: string | null;
  input_language?: string | null;
  target_languages?: string[];
  start_sentence?: number | null;
  end_sentence?: number | null;
  sentences_per_output_file?: number | null;
  llm_model?: string | null;
  audio_mode?: string | null;
  audio_bitrate_kbps?: number | null;
  selected_voice?: string | null;
  voice_overrides?: Record<string, string>;
  worker_count?: number | null;
  batch_size?: number | null;
  show_original?: boolean | null;
  enable_transliteration?: boolean | null;
  start_time_offset_seconds?: number | null;
  end_time_offset_seconds?: number | null;
  video_path?: string | null;
  subtitle_path?: string | null;
  tempo?: number | null;
  macos_reading_speed?: number | null;
  output_dir?: string | null;
  original_mix_percent?: number | null;
  flush_sentences?: number | null;
  split_batches?: boolean | null;
  include_transliteration?: boolean | null;
  add_images?: boolean | null;
  translation_provider?: string | null;
  transliteration_mode?: string | null;
  transliteration_model?: string | null;
  transliteration_module?: string | null;
  target_height?: number | null;
  preserve_aspect_ratio?: boolean | null;
}

export interface PipelineStatusResponse {
  job_id: string;
  job_type: string;
  status: PipelineJobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: PipelineResponsePayload | Record<string, unknown> | null;
  error: string | null;
  latest_event: ProgressEventPayload | null;
  tuning: Record<string, unknown> | null;
  user_id?: string | null;
  user_role?: string | null;
  generated_files?: Record<string, unknown> | null;
  parameters?: JobParameterSnapshot | null;
  media_completed?: boolean | null;
  retry_summary?: Record<string, Record<string, number>> | null;
  job_label?: string | null;
  image_generation?: ImageGenerationSummary | null;
}

export interface SubtitleSourceEntry {
  name: string;
  path: string;
  format: string;
  language?: string | null;
  modified_at?: string | null;
}

export interface SubtitleSourceListResponse {
  sources: SubtitleSourceEntry[];
}

export interface SubtitleTvMetadataParse {
  series: string;
  season: number;
  episode: number;
  pattern: string;
}

export interface SubtitleTvMetadataResponse {
  job_id: string;
  source_name: string | null;
  parsed: SubtitleTvMetadataParse | null;
  media_metadata: Record<string, unknown> | null;
}

export interface SubtitleTvMetadataLookupRequest {
  force?: boolean;
}

export interface SubtitleTvMetadataPreviewResponse {
  source_name: string | null;
  parsed: SubtitleTvMetadataParse | null;
  media_metadata: Record<string, unknown> | null;
}

export interface SubtitleTvMetadataPreviewLookupRequest {
  source_name: string;
  force?: boolean;
}

export interface YoutubeVideoMetadataParse {
  video_id: string;
  pattern: string;
}

export interface YoutubeVideoMetadataResponse {
  job_id: string;
  source_name: string | null;
  parsed: YoutubeVideoMetadataParse | null;
  youtube_metadata: Record<string, unknown> | null;
}

export interface YoutubeVideoMetadataLookupRequest {
  force?: boolean;
}

export interface YoutubeVideoMetadataPreviewResponse {
  source_name: string | null;
  parsed: YoutubeVideoMetadataParse | null;
  youtube_metadata: Record<string, unknown> | null;
}

export interface YoutubeVideoMetadataPreviewLookupRequest {
  source_name: string;
  force?: boolean;
}

export interface BookOpenLibraryQuery {
  title?: string | null;
  author?: string | null;
  isbn?: string | null;
}

export interface BookOpenLibraryMetadataResponse {
  job_id: string;
  source_name: string | null;
  query: BookOpenLibraryQuery | null;
  book_metadata_lookup: Record<string, unknown> | null;
}

export interface BookOpenLibraryMetadataLookupRequest {
  force?: boolean;
}

export interface BookOpenLibraryMetadataPreviewResponse {
  source_name: string | null;
  query: BookOpenLibraryQuery | null;
  book_metadata_lookup: Record<string, unknown> | null;
}

export interface BookOpenLibraryMetadataPreviewLookupRequest {
  query: string;
  force?: boolean;
}

export interface SubtitleDeleteResponse {
  subtitle_path: string;
  base_dir?: string | null;
  removed: string[];
  missing: string[];
}

export type YoutubeSubtitleKind = 'auto' | 'manual';

export interface YoutubeSubtitleTrack {
  language: string;
  kind: YoutubeSubtitleKind;
  name?: string | null;
  formats: string[];
}

export interface YoutubeSubtitleListResponse {
  video_id: string;
  title?: string | null;
  tracks: YoutubeSubtitleTrack[];
  video_formats: YoutubeVideoFormat[];
}

export interface YoutubeSubtitleDownloadRequest {
  url: string;
  language: string;
  kind: YoutubeSubtitleKind;
  video_output_dir?: string | null;
  timestamp?: string | null;
}

export interface YoutubeSubtitleDownloadResponse {
  output_path: string;
  filename: string;
}

export interface YoutubeVideoDownloadRequest {
  url: string;
  output_dir?: string | null;
  format_id?: string | null;
  timestamp?: string | null;
}

export interface YoutubeVideoDownloadResponse {
  output_path: string;
  filename: string;
  folder: string;
}

export interface YoutubeVideoFormat {
  format_id: string;
  ext: string;
  resolution?: string | null;
  fps?: number | null;
  note?: string | null;
  bitrate_kbps?: number | null;
  filesize?: string | null;
}

export interface YoutubeNasSubtitle {
  path: string;
  filename: string;
  language?: string | null;
  format: string;
}

export interface YoutubeNasVideo {
  path: string;
  filename: string;
  folder: string;
  size_bytes: number;
  modified_at: string;
  source?: string;
   linked_job_ids?: string[];
  subtitles: YoutubeNasSubtitle[];
}

export interface YoutubeNasLibraryResponse {
  base_dir: string;
  videos: YoutubeNasVideo[];
}

export interface YoutubeInlineSubtitleStream {
  index: number;
  position: number;
  language?: string | null;
  codec?: string | null;
  title?: string | null;
  can_extract: boolean;
}

export interface YoutubeInlineSubtitleListResponse {
  video_path: string;
  streams: YoutubeInlineSubtitleStream[];
}

export interface YoutubeSubtitleExtractionResponse {
  video_path: string;
  extracted: YoutubeNasSubtitle[];
}

export interface YoutubeSubtitleDeleteResponse {
  video_path: string;
  subtitle_path: string;
  removed: string[];
  missing: string[];
}

export interface YoutubeVideoDeleteRequest {
  video_path: string;
}

export interface YoutubeVideoDeleteResponse {
  video_path: string;
  removed: string[];
  missing: string[];
}

export interface YoutubeDubRequest {
  video_path: string;
  subtitle_path: string;
  media_metadata?: Record<string, unknown> | null;
  target_language?: string | null;
  voice?: string | null;
  tempo?: number | null;
  macos_reading_speed?: number | null;
  output_dir?: string | null;
  start_time_offset?: string | null;
  end_time_offset?: string | null;
  original_mix_percent?: number | null;
  flush_sentences?: number | null;
  llm_model?: string | null;
  split_batches?: boolean | null;
  stitch_batches?: boolean | null;
  include_transliteration?: boolean | null;
  target_height?: number | null;
  preserve_aspect_ratio?: boolean | null;
}

export interface YoutubeDubResponse {
  job_id: string;
  status: PipelineJobStatus;
  created_at: string;
  job_type: string;
  output_path?: string | null;
}

export interface LlmModelListResponse {
  models: string[];
}

export type AssistantChatMessageRole = 'user' | 'assistant';

export interface AssistantChatMessage {
  role: AssistantChatMessageRole;
  content: string;
}

export interface AssistantRequestContext {
  source?: string | null;
  page?: string | null;
  job_id?: string | null;
  selection_text?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AssistantLookupRequest {
  query: string;
  input_language: string;
  lookup_language: string;
  llm_model?: string | null;
  system_prompt?: string | null;
  history?: AssistantChatMessage[];
  context?: AssistantRequestContext | null;
}

export interface AssistantLookupResponse {
  answer: string;
  model: string;
  token_usage?: Record<string, number>;
  source?: string | null;
}

export interface SubtitleJobResultPayload {
  subtitle?: {
    output_path?: string;
    relative_path?: string;
    metadata?: Record<string, unknown>;
    cues?: number;
    translated?: number;
  };
  [key: string]: unknown;
}

export interface PipelineJobListResponse {
  jobs: PipelineStatusResponse[];
}

export interface PipelineJobActionResponse {
  job: PipelineStatusResponse;
  error?: string | null;
}

export interface SessionUser {
  username: string;
  role: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  last_login: string | null;
}

export interface SessionStatusResponse {
  token: string;
  user: SessionUser;
}

export interface LoginRequestPayload {
  username: string;
  password: string;
}

export interface PasswordChangeRequestPayload {
  current_password: string;
  new_password: string;
}

export type UserAccountStatus = 'active' | 'suspended' | 'inactive';

export interface ManagedUserMetadata {
  [key: string]: unknown;
  last_login?: string | null;
  suspended?: boolean;
  is_suspended?: boolean;
}

export interface ManagedUser {
  username: string;
  roles: string[];
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  status?: UserAccountStatus;
  is_active?: boolean;
  is_suspended?: boolean;
  last_login?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  metadata?: ManagedUserMetadata;
}

export interface UserListResponse {
  users: ManagedUser[];
}

export interface UserAccountResponse {
  user: ManagedUser;
}

export interface UserCreateRequestPayload {
  username: string;
  password: string;
  roles: string[];
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}

export type LibraryViewMode = 'flat' | 'by_author' | 'by_genre' | 'by_language';

export interface LibraryItem {
  jobId: string;
  author: string;
  bookTitle: string;
  itemType: 'book' | 'video' | 'narrated_subtitle';
  genre?: string | null;
  language: string;
  status: 'finished' | 'paused';
  mediaCompleted: boolean;
  createdAt: string;
  updatedAt: string;
  libraryPath: string;
  coverPath?: string | null;
  isbn?: string | null;
  sourcePath?: string | null;
  metadata: Record<string, unknown>;
}

export interface LibraryMoveResponse {
  item: LibraryItem;
}

export interface LibrarySearchResponse {
  total: number;
  page: number;
  limit: number;
  view: LibraryViewMode;
  items: LibraryItem[];
  groups?: Record<string, unknown>[] | null;
}

export interface LibraryMediaRemovalResponse {
  jobId: string;
  location: 'library' | 'queue';
  removed: number;
  item?: LibraryItem | null;
}

export interface LibraryReindexResponse {
  indexed: number;
}

export interface LibraryMetadataUpdatePayload {
  title?: string | null;
  author?: string | null;
  genre?: string | null;
  language?: string | null;
  isbn?: string | null;
}

export interface LibraryIsbnLookupResponse {
  metadata: Record<string, unknown>;
}

export interface UserPasswordResetRequestPayload {
  password: string;
}

export interface UserUpdateRequestPayload {
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}

export interface PipelineMediaFile {
  name: string;
  url: string | null;
  size?: number | null;
  updated_at?: string | null;
  source: 'completed' | 'live';
  relative_path?: string | null;
  path?: string | null;
  chunk_id?: string | null;
  range_fragment?: string | null;
  start_sentence?: number | null;
  end_sentence?: number | null;
  type?: string | null;
}

export interface ChunkSentenceTimelineEvent {
  duration: number;
  original_index: number;
  translation_index: number;
  transliteration_index: number;
}

export interface ChunkSentenceVariant {
  text: string;
  tokens: string[];
}

export type WordTimingLanguage = 'orig' | 'trans' | 'xlit';

export interface WordTiming {
  id: string;
  sentenceId: number;
  tokenIdx: number;
  text: string;
  lang: WordTimingLanguage;
  t0: number;
  t1: number;
}

export interface PauseTiming {
  t0: number;
  t1: number;
  reason?: 'silence' | 'tempo' | 'gap';
}

export interface JobTimingEntry {
  token?: string;
  text?: string;
  t0?: number;
  t1?: number;
  start?: number;
  end?: number;
  begin?: number;
  offset?: number;
  time?: number;
  stop?: number;
  lane?: WordTimingLanguage;
  wordIdx?: number;
  sentence_id?: string | number | null;
  sentenceIdx?: string | number | null;
  sentenceId?: string | number | null;
  id?: string | number | null;
  policy?: string | null;
  source?: string | null;
  fallback?: boolean;
  start_gate?: number | null;
  end_gate?: number | null;
  startGate?: number | null;
  endGate?: number | null;
  pause_before_ms?: number | null;
  pause_after_ms?: number | null;
  pauseBeforeMs?: number | null;
  pauseAfterMs?: number | null;
  validation?: {
    drift?: number | null;
    count?: number | null;
  } | null;
}

export interface JobTimingTrackPayload {
  track: 'mix' | 'translation' | 'original';
  segments: JobTimingEntry[];
  playback_rate?: number | null;
}

export interface JobTimingAudioBinding {
  track: 'mix' | 'translation' | 'original';
  available?: boolean;
}

export interface JobTimingResponse {
  job_id: string;
  tracks: {
    mix?: JobTimingTrackPayload;
    translation?: JobTimingTrackPayload;
    original?: JobTimingTrackPayload;
  };
  audio: Record<string, JobTimingAudioBinding>;
  highlighting_policy: string | null;
  has_estimated_segments?: boolean;
}

export interface TrackTimingPayload {
  trackType: 'translated' | 'original_translated' | 'original';
  chunkId: string;
  words: WordTiming[];
  pauses: PauseTiming[];
  trackOffset: number;
  tempoFactor: number;
  version: string;
}

export interface TimingToken {
  lane: 'orig' | 'trans';
  sentenceIdx: number;
  wordIdx: number;
  start: number;
  end: number;
  text: string;
  policy?: string;
  source?: string;
  fallback?: boolean;
  startGate?: number;
  endGate?: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
  validation?: {
    drift?: number;
    count?: number;
  };
}

export interface TimingIndexResponse {
  mix?: TimingToken[];
  translation?: TimingToken[];
  original?: TimingToken[];
  sentences?: Array<{
    sentenceIdx: number;
    startGate?: number;
    endGate?: number;
    pauseBeforeMs?: number;
    pauseAfterMs?: number;
  }>;
}

export interface AudioTrackMetadata {
  path?: string | null;
  url?: string | null;
  duration?: number | null;
  sampleRate?: number | null;
}

export interface ChunkSentenceImagePayload {
  path?: string | null;
  prompt?: string | null;
  negative_prompt?: string | null;
  batch_start_sentence?: number | null;
  batch_end_sentence?: number | null;
  batch_size?: number | null;
}

export interface SentenceImageInfoResponse {
  job_id: string;
  sentence_number: number;
  range_fragment?: string | null;
  relative_path?: string | null;
  sentence?: string | null;
  prompt?: string | null;
  negative_prompt?: string | null;
}

export interface SentenceImageInfoBatchResponse {
  job_id: string;
  items: SentenceImageInfoResponse[];
  missing: number[];
}

export interface SentenceImageRegenerateRequestPayload {
  use_llm_prompt?: boolean | null;
  context_sentences?: number | null;
  prompt?: string | null;
  negative_prompt?: string | null;
  width?: number | null;
  height?: number | null;
  steps?: number | null;
  cfg_scale?: number | null;
  sampler_name?: string | null;
  seed?: number | null;
}

export interface SentenceImageRegenerateResponse {
  job_id: string;
  sentence_number: number;
  range_fragment?: string | null;
  relative_path: string;
  prompt: string;
  negative_prompt: string;
  width: number;
  height: number;
  steps: number;
  cfg_scale: number;
  sampler_name?: string | null;
  seed?: number | null;
}

export interface ChunkSentenceMetadata {
  sentence_number?: number | null;
  original: ChunkSentenceVariant;
  translation?: ChunkSentenceVariant | null;
  transliteration?: ChunkSentenceVariant | null;
  timeline: ChunkSentenceTimelineEvent[];
  image?: ChunkSentenceImagePayload | null;
  image_path?: string | null;
  imagePath?: string | null;
  total_duration?: number | null;
  start_gate?: number | null;
  end_gate?: number | null;
  startGate?: number | null;
  endGate?: number | null;
  original_start_gate?: number | null;
  original_end_gate?: number | null;
  originalStartGate?: number | null;
  originalEndGate?: number | null;
  highlight_granularity?: string | null;
  counts?: Record<string, number>;
  phase_durations?: Record<string, number> | null;
}

export interface PipelineMediaChunk {
  chunk_id?: string | null;
  range_fragment?: string | null;
  start_sentence?: number | null;
  end_sentence?: number | null;
  files: PipelineMediaFile[];
  sentences?: ChunkSentenceMetadata[];
  metadata_path?: string | null;
  metadata_url?: string | null;
  sentence_count?: number | null;
  audio_tracks?: Record<string, AudioTrackMetadata> | null;
}

export interface PipelineMediaResponse {
  media: Record<string, PipelineMediaFile[] | undefined>;
  chunks: PipelineMediaChunk[];
  complete: boolean;
}

export interface VideoGenerationResponse {
  request_id: string;
  job_id: string;
  status: string;
  output_path?: string | null;
  logs_url?: string | null;
}

export interface VideoGenerationRequestPayload {
  job_id: string;
  parameters: Record<string, unknown>;
}

export interface MediaSearchResult {
  job_id: string;
  job_label: string | null;
  base_id: string | null;
  chunk_id: string | null;
  chunk_index?: number | null;
  chunk_total?: number | null;
  range_fragment: string | null;
  start_sentence: number | null;
  end_sentence: number | null;
  snippet: string;
  occurrence_count: number;
  match_start: number | null;
  match_end: number | null;
  text_length: number | null;
  offset_ratio: number | null;
  approximate_time_seconds: number | null;
  media: Record<string, PipelineMediaFile[] | undefined>;
  source: 'pipeline' | 'library';
  libraryAuthor?: string | null;
  libraryGenre?: string | null;
  libraryLanguage?: string | null;
  coverPath?: string | null;
  libraryPath?: string | null;
}

export interface MediaSearchResponse {
  query: string;
  limit: number;
  count: number;
  results: MediaSearchResult[];
}

export interface ExportRequestPayload {
  source_kind: 'job' | 'library';
  source_id: string;
  player_type?: 'interactive-text';
}

export interface ExportResponse {
  export_id: string;
  download_url: string;
  filename: string;
  created_at: string;
}

export type ReadingBedKind = 'bundled' | 'uploaded';

export interface ReadingBedEntry {
  id: string;
  label: string;
  url: string;
  kind: ReadingBedKind;
  content_type?: string | null;
  is_default?: boolean;
}

export interface ReadingBedListResponse {
  default_id?: string | null;
  beds: ReadingBedEntry[];
}

export interface ReadingBedUpdateRequestPayload {
  label?: string | null;
  set_default?: boolean | null;
}

export interface ReadingBedDeleteResponse {
  deleted: boolean;
  default_id?: string | null;
}
