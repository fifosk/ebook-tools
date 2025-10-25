import { useMemo } from 'react';
import type { LiveMediaItem } from '../hooks/useLiveMedia';
import { deriveMediaItemId } from './mediaUtils';

type MediaCategory = LiveMediaItem['type'];

export interface MediaListProps {
  items: LiveMediaItem[];
  category: MediaCategory;
  emptyMessage?: string;
  selectedId?: string | null;
  onSelect?: (item: LiveMediaItem, id: string) => void;
}

interface MediaEntry extends LiveMediaItem {
  key: string;
  size: string | null;
  updatedAt: string | null;
  id: string | null;
  isSelectable: boolean;
}

function formatFileSize(size: number | null | undefined): string | null {
  if (typeof size !== 'number' || !Number.isFinite(size) || size <= 0) {
    return null;
  }

  if (size < 1024) {
    return `${size} B`;
  }

  const units = ['KB', 'MB', 'GB'];
  let value = size;
  let unitIndex = -1;
  while (value >= 1024 && unitIndex + 1 < units.length) {
    value /= 1024;
    unitIndex += 1;
  }

  const formatted = value < 10 ? value.toFixed(1) : Math.round(value).toString();
  const unit = units[Math.max(unitIndex, 0)];
  return `${formatted} ${unit}`;
}

function formatTimestamp(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toLocaleString();
}

function deriveEmptyMessage(category: MediaCategory): string {
  switch (category) {
    case 'audio':
      return 'No audio media yet.';
    case 'video':
      return 'No video media yet.';
    case 'text':
    default:
      return 'No text media yet.';
  }
}

export default function MediaList({ items, category, emptyMessage, selectedId, onSelect }: MediaListProps) {
  const resolvedEmptyMessage = emptyMessage ?? deriveEmptyMessage(category);

  const entries: MediaEntry[] = useMemo(
    () =>
      items.map((item, index) => {
        const id = deriveMediaItemId(item, index);
        const key = id ?? `${item.type}:${index}`;
        const size = formatFileSize(item.size ?? null);
        const updatedAt = formatTimestamp(item.updated_at ?? null);
        const hasUrl = typeof item.url === 'string' && item.url.length > 0;
        const isSelectable = Boolean(id) && (category === 'text' ? true : hasUrl);
        return { ...item, key, id, size, updatedAt, isSelectable };
      }),
    [items, category],
  );

  if (entries.length === 0) {
    return (
      <div className="media-list" role="status" data-testid={`media-list-${category}`}>
        {resolvedEmptyMessage}
      </div>
    );
  }

  return (
    <ul className="media-list" data-testid={`media-list-${category}`} aria-live="polite">
      {entries.map((item) => {
        const isActive = item.id !== null && item.id === selectedId;
        const actionLabel =
          category === 'audio' ? 'Play audio' : category === 'video' ? 'Play video' : 'View text';

        return (
          <li key={item.key} className="media-list__item" data-active={isActive || undefined}>
            <button
              type="button"
              className="media-list__button"
              onClick={() => (item.id && item.isSelectable && onSelect ? onSelect(item, item.id) : undefined)}
              disabled={!item.isSelectable || !onSelect}
              aria-pressed={isActive}
            >
              <div className="media-list__details">
                <span className="media-list__name">{item.name}</span>
                {item.updatedAt ? (
                  <time className="media-list__timestamp" dateTime={item.updated_at ?? undefined}>
                    {item.updatedAt}
                  </time>
                ) : null}
                {item.size ? <span className="media-list__size">{item.size}</span> : null}
                <span className="media-list__source" data-source={item.source}>
                  {item.source === 'completed' ? 'Completed' : 'Live'}
                </span>
              </div>
              <span className="media-list__action" aria-hidden="true">
                {item.isSelectable && onSelect ? actionLabel : 'Unavailable'}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
