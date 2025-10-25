export type PipelineJobStatus =
  | 'pending'
  | 'running'
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
  status: PipelineJobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: PipelineResponsePayload | null;
  error: string | null;
  latest_event: ProgressEventPayload | null;
  tuning: Record<string, unknown> | null;
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

export interface UserPasswordResetRequestPayload {
  password: string;
}

export interface UserUpdateRequestPayload {
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}
