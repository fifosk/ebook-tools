export type PipelineJobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

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
}
