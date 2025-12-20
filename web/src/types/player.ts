import type { LibraryItem } from '../api/dtos';

export type MediaCategory = 'text' | 'audio' | 'video';

export type PlayerMode = 'online' | 'export';

export type PlayerFeatureFlags = {
  linguist?: boolean;
  painter?: boolean;
  search?: boolean;
};

export interface MediaSelectionRequest {
  baseId: string | null;
  preferredType?: MediaCategory | null;
  offsetRatio?: number | null;
  approximateTime?: number | null;
  token?: number;
}

export interface LibraryOpenRequest {
  kind: 'library-open';
  jobId: string;
  item?: LibraryItem;
  selection?: MediaSelectionRequest | null;
}

export type LibraryOpenInput = string | LibraryItem | LibraryOpenRequest;

export function isLibraryOpenRequest(value: unknown): value is LibraryOpenRequest {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const candidate = value as Partial<LibraryOpenRequest>;
  if (candidate.kind !== 'library-open') {
    return false;
  }

  return typeof candidate.jobId === 'string' && candidate.jobId.trim().length > 0;
}
