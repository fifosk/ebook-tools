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
  book_metadata?: Record<string, unknown> | null;
  media?: Record<string, PipelineMediaFile[] | undefined> | null;
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
