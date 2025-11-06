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
  written_mode: string;
  selected_voice: string;
  voice_overrides?: Record<string, string>;
  output_html: boolean;
  output_pdf: boolean;
  generate_video: boolean;
  include_transliteration: boolean;
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
}

export interface PipelineStatusResponse {
  job_id: string;
  job_type: string;
  status: PipelineJobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: PipelineResponsePayload | null;
  error: string | null;
  latest_event: ProgressEventPayload | null;
  tuning: Record<string, unknown> | null;
  user_id?: string | null;
  user_role?: string | null;
  generated_files?: Record<string, unknown> | null;
  media_completed?: boolean | null;
}

export interface SubtitleSourceEntry {
  name: string;
  path: string;
}

export interface SubtitleSourceListResponse {
  sources: SubtitleSourceEntry[];
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

export interface TrackTimingPayload {
  trackType: 'translated' | 'original_translated';
  chunkId: string;
  words: WordTiming[];
  pauses: PauseTiming[];
  trackOffset: number;
  tempoFactor: number;
  version: string;
}

export interface JobTimingEntry {
  token: string;
  t0: number;
  t1: number;
  sentence_id?: string | number | null;
}

export interface JobTimingResponse {
  job_id: string;
  track: string;
  segments: JobTimingEntry[];
  playback_rate?: number | null;
}

export interface ChunkSentenceMetadata {
  sentence_number?: number | null;
  original: ChunkSentenceVariant;
  translation?: ChunkSentenceVariant | null;
  transliteration?: ChunkSentenceVariant | null;
  timeline: ChunkSentenceTimelineEvent[];
  total_duration?: number | null;
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
  audio_tracks?: Record<string, string> | null;
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
