import type { LiveMediaItem } from '../hooks/useLiveMedia';

export function deriveMediaItemId(item: LiveMediaItem, index: number): string | null {
  if (typeof item.url === 'string' && item.url.length > 0) {
    return item.url;
  }

  if (item.name && item.name.length > 0) {
    return `${item.type}:${item.name}`;
  }

  if (item.updated_at) {
    return `${item.type}:${item.updated_at}`;
  }

  return `${item.type}:${index}`;
}
