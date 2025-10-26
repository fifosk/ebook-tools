import { useCallback, useEffect, useMemo, useState, type KeyboardEvent } from 'react';
import type { LiveMediaItem } from '../hooks/useLiveMedia';

type MediaCategory = LiveMediaItem['type'];

export interface MediaListProps {
  items: LiveMediaItem[];
  category: MediaCategory;
  emptyMessage?: string;
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

export default function MediaList({ items, category, emptyMessage }: MediaListProps) {
  const resolvedEmptyMessage = emptyMessage ?? deriveEmptyMessage(category);

  const entries = useMemo(
    () =>
      items.map((item, index) => {
        const key = item.url ?? `${item.type}:${item.name ?? 'media'}:${index}`;
        const size = formatFileSize(item.size ?? null);
        const updatedAt = formatTimestamp(item.updated_at ?? null);
        return { ...item, key, size, updatedAt };
      }),
    [items],
  );

  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    if (entries.length === 0) {
      if (selectedKey !== null) {
        setSelectedKey(null);
      }
      return;
    }

    const hasSelected = selectedKey !== null && entries.some((entry) => entry.key === selectedKey);

    if (!hasSelected) {
      setSelectedKey(entries[entries.length - 1].key);
    }
  }, [entries, selectedKey]);

  const handleSelect = useCallback((key: string) => {
    setSelectedKey(key);
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>, key: string) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleSelect(key);
      }
    },
    [handleSelect],
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
        const isSelected = item.key === selectedKey;
        const actionLabel = item.type === 'text' ? 'Open' : 'Download';
        const actionTarget = item.type === 'text' ? '_blank' : undefined;
        const actionRel = item.type === 'text' ? 'noreferrer' : undefined;
        const actionDownload = item.type !== 'text' ? item.name ?? true : undefined;
        return (
          <li key={item.key} className="media-list__item" data-selected={isSelected ? 'true' : 'false'}>
            <div
              className="media-list__details"
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              onClick={() => handleSelect(item.key)}
              onKeyDown={(event) => handleKeyDown(event, item.key)}
            >
              {item.url ? (
                <a
                  className="media-list__name"
                  href={item.url}
                  target={actionTarget}
                  rel={actionRel}
                  download={actionDownload}
                >
                  {item.name}
                </a>
              ) : (
                <span className="media-list__name">{item.name}</span>
              )}
              <div className="media-list__meta">
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
            </div>
            {item.url ? (
              <a
                className="media-list__action"
                href={item.url}
                target={actionTarget}
                rel={actionRel}
                download={actionDownload}
              >
                {actionLabel}
              </a>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
