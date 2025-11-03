import { useCallback, useEffect, useMemo, useState } from 'react';
import type { LiveMediaItem } from '../hooks/useLiveMedia';
import { formatFileSize, formatTimestamp } from '../utils/mediaFormatters';

type MediaCategory = LiveMediaItem['type'];

export interface MediaListProps {
  items: LiveMediaItem[];
  category: MediaCategory;
  emptyMessage?: string;
  id?: string;
  selectedKey?: string | null;
  onSelectItem?: (item: LiveMediaItem) => void;
}

function deriveEmptyMessage(category: MediaCategory): string {
  switch (category) {
    case 'audio':
      return 'No audio media yet.';
    case 'video':
      return 'No video media yet.';
    case 'text':
    default:
      return 'No interactive reader media yet.';
  }
}

interface MediaListEntry extends LiveMediaItem {
  key: string;
  sizeLabel: string | null;
  updatedAtLabel: string | null;
}

export default function MediaList({
  items,
  category,
  emptyMessage,
  id,
  selectedKey,
  onSelectItem,
}: MediaListProps) {
  const resolvedEmptyMessage = emptyMessage ?? deriveEmptyMessage(category);

  const entries = useMemo(
    () =>
      items.map((item, index) => {
        const key = item.url ?? `${item.type}:${item.name ?? 'media'}:${index}`;
        const sizeLabel = formatFileSize(item.size ?? null);
        const updatedAtLabel = formatTimestamp(item.updated_at ?? null);
        return { ...item, key, sizeLabel, updatedAtLabel } satisfies MediaListEntry;
      }),
    [items],
  );

  const [internalSelectedKey, setInternalSelectedKey] = useState<string | null>(null);
  const isControlled = selectedKey !== undefined;
  const resolvedSelectedKey = isControlled ? selectedKey ?? null : internalSelectedKey;

  useEffect(() => {
    if (isControlled) {
      return;
    }

    if (entries.length === 0) {
      if (internalSelectedKey !== null) {
        setInternalSelectedKey(null);
      }
      return;
    }

    const hasSelected =
      internalSelectedKey !== null && entries.some((entry) => entry.key === internalSelectedKey);

    if (!hasSelected) {
      setInternalSelectedKey(entries[entries.length - 1].key);
    }
  }, [entries, internalSelectedKey, isControlled]);

  const handleSelect = useCallback(
    (entry: MediaListEntry) => {
      if (!isControlled) {
        setInternalSelectedKey(entry.key);
      }
      onSelectItem?.(entry);
    },
    [isControlled, onSelectItem],
  );

  if (entries.length === 0) {
    return (
      <div className="media-list" id={id} role="status" data-testid={`media-list-${category}`}>
        {resolvedEmptyMessage}
      </div>
    );
  }

  return (
    <ul className="media-list" id={id} data-testid={`media-list-${category}`} aria-live="polite">
      {entries.map((item) => {
        const isSelected = item.key === resolvedSelectedKey;
        const actionLabel = item.type === 'text' ? 'Open' : 'Download';
        const actionTarget = item.type === 'text' ? '_blank' : undefined;
        const actionRel = item.type === 'text' ? 'noreferrer' : undefined;
        const actionDownload = item.type !== 'text' ? item.name ?? true : undefined;
        return (
          <li key={item.key} className="media-list__item" data-selected={isSelected ? 'true' : 'false'}>
            <button
              type="button"
              className="media-list__details"
              aria-pressed={isSelected}
              onClick={() => handleSelect(item)}
            >
              <span className="media-list__name">{item.name}</span>
              <div className="media-list__meta">
                {item.updatedAtLabel ? (
                  <time className="media-list__timestamp" dateTime={item.updated_at ?? undefined}>
                    {item.updatedAtLabel}
                  </time>
                ) : null}
                {item.sizeLabel ? <span className="media-list__size">{item.sizeLabel}</span> : null}
                <span className="media-list__source" data-source={item.source}>
                  {item.source === 'completed' ? 'Completed' : 'Live'}
                </span>
              </div>
            </button>
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
