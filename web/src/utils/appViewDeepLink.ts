import {
  APP_VIEW_QUERY_PARAM,
  CREATE_BOOK_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW,
  isSelectedView,
  type SelectedView
} from '../constants/appViews';

type LocationParts = Pick<Location, 'search' | 'hash'>;
export const CREATION_TEMPLATE_QUERY_PARAM = 'template_id';
export const HANDOFF_SOURCE_QUERY_PARAM = 'source';
export const APPLE_HANDOFF_SOURCE = 'apple';

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

export function parseDeepLinkedCreationTemplateId(location: LocationParts): string | null {
  const searchTemplate = new URLSearchParams(location.search)
    .get(CREATION_TEMPLATE_QUERY_PARAM)
    ?.trim();
  if (searchTemplate) {
    return searchTemplate;
  }

  const hash = location.hash.replace(/^#/, '');
  if (!hash.startsWith('?')) {
    return null;
  }
  return (
    new URLSearchParams(hash.slice(1))
      .get(CREATION_TEMPLATE_QUERY_PARAM)
      ?.trim() || null
  );
}

export function parseDeepLinkedHandoffSource(location: LocationParts): string | null {
  const searchSource = new URLSearchParams(location.search)
    .get(HANDOFF_SOURCE_QUERY_PARAM)
    ?.trim();
  if (searchSource) {
    return searchSource;
  }

  const hash = location.hash.replace(/^#/, '');
  if (!hash.startsWith('?')) {
    return null;
  }
  return (
    new URLSearchParams(hash.slice(1))
      .get(HANDOFF_SOURCE_QUERY_PARAM)
      ?.trim() || null
  );
}

export function buildAppViewHandoffPath(
  view: SelectedView,
  options: { templateId?: string | null; source?: string | null } = {}
): string {
  const params = new URLSearchParams();
  params.set(APP_VIEW_QUERY_PARAM, view);
  if (options.source?.trim()) {
    params.set(HANDOFF_SOURCE_QUERY_PARAM, options.source.trim());
  }
  if (options.templateId?.trim()) {
    params.set(CREATION_TEMPLATE_QUERY_PARAM, options.templateId.trim());
  }
  return `/?${params.toString()}`;
}

export const APPLE_CREATE_WEB_VIEW_BY_MODE = {
  generatedBook: CREATE_BOOK_VIEW,
  narrateEbook: 'pipeline:source',
  subtitleJob: SUBTITLES_VIEW,
  youtubeDub: YOUTUBE_DUB_VIEW
} as const;
