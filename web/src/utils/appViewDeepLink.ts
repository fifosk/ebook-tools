import {
  APP_VIEW_QUERY_PARAM,
  CREATE_BOOK_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW,
  isSelectedView,
  type SelectedView
} from '../constants/appViews';

type LocationParts = Pick<Location, 'search' | 'hash'>;

export function parseAppView(value: string | null | undefined): SelectedView | null {
  const trimmed = value?.trim();
  return trimmed && isSelectedView(trimmed) ? trimmed : null;
}

export function parseDeepLinkedAppView(location: LocationParts): SelectedView | null {
  const searchView = parseAppView(new URLSearchParams(location.search).get(APP_VIEW_QUERY_PARAM));
  if (searchView) {
    return searchView;
  }

  const hash = location.hash.replace(/^#/, '');
  if (!hash) {
    return null;
  }

  if (hash.startsWith('?')) {
    return parseAppView(new URLSearchParams(hash.slice(1)).get(APP_VIEW_QUERY_PARAM));
  }

  return parseAppView(hash);
}

export function buildAppViewHandoffPath(view: SelectedView): string {
  return `/?${APP_VIEW_QUERY_PARAM}=${encodeURIComponent(view)}`;
}

export const APPLE_CREATE_WEB_VIEW_BY_MODE = {
  generatedBook: CREATE_BOOK_VIEW,
  narrateEbook: 'pipeline:source',
  subtitleJob: SUBTITLES_VIEW,
  youtubeDub: YOUTUBE_DUB_VIEW
} as const;
