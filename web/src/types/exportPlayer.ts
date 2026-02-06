import type { PipelineMediaChunk, PipelineMediaFile } from '../api/dtos';

export type ExportPlayerFeatureFlags = {
  linguist?: boolean;
  painter?: boolean;
  search?: boolean;
};

export type ExportReadingBed = {
  id: string;
  label: string;
  url: string;
};

export type ExportPlayerSource = {
  kind: 'job' | 'library';
  id: string;
  job_type?: string | null;
  item_type?: 'book' | 'video' | 'narrated_subtitle' | null;
  label?: string | null;
  author?: string | null;
};

export type ExportPlayerManifest = {
  schema_version: number;
  export_label?: string | null;
  player?: {
    type?: string | null;
    features?: ExportPlayerFeatureFlags | null;
  } | null;
  source?: ExportPlayerSource | null;
  media_metadata?: Record<string, unknown> | null;
  /** @deprecated Use media_metadata. Kept for backward compat with old exports. */
  book_metadata?: Record<string, unknown> | null;
  media?: Record<string, PipelineMediaFile[] | undefined> | null;
  inline_subtitles?: Record<string, string> | null;
  chunks?: PipelineMediaChunk[] | null;
  complete?: boolean | null;
  reading_bed?: ExportReadingBed | null;
  created_at?: string | null;
};

declare global {
  interface Window {
    __EXPORT_DATA__?: ExportPlayerManifest;
  }
}

export {};
