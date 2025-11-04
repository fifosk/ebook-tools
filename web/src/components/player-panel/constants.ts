import type { LiveMediaState } from '../../hooks/useLiveMedia';

export const MEDIA_CATEGORIES = ['text', 'audio', 'video'] as const;
export type MediaCategory = (typeof MEDIA_CATEGORIES)[number];
export type NavigationIntent = 'first' | 'previous' | 'next' | 'last';

export interface TabDefinition {
  key: MediaCategory;
  label: string;
  emptyMessage: string;
}

export const TAB_DEFINITIONS: TabDefinition[] = [
  { key: 'text', label: 'Interactive Reader', emptyMessage: 'No interactive reader media yet.' },
  { key: 'video', label: 'Video', emptyMessage: 'No video media yet.' },
];

export const DEFAULT_COVER_URL = '/assets/default-cover.png';

export function selectInitialTab(media: LiveMediaState): MediaCategory {
  const populated = TAB_DEFINITIONS.find((tab) => media[tab.key].length > 0);
  return populated?.key ?? 'text';
}
