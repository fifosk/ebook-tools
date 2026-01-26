import type { BookNarrationFormSection } from '../components/book-narration/BookNarrationForm';

// View type constants
export const ADMIN_USER_MANAGEMENT_VIEW = 'admin:users' as const;
export const ADMIN_READING_BEDS_VIEW = 'admin:reading-beds' as const;
export const ADMIN_SETTINGS_VIEW = 'admin:settings' as const;
export const ADMIN_SYSTEM_VIEW = 'admin:system' as const;
export const JOB_PROGRESS_VIEW = 'job:progress' as const;
export const JOB_MEDIA_VIEW = 'job:media' as const;
export const LIBRARY_VIEW = 'library:list' as const;
export const CREATE_BOOK_VIEW = 'books:create' as const;
export const SUBTITLES_VIEW = 'subtitles:home' as const;
export const YOUTUBE_SUBTITLES_VIEW = 'subtitles:youtube' as const;
export const YOUTUBE_DUB_VIEW = 'subtitles:youtube-dub' as const;

export type PipelineMenuView =
  | 'pipeline:source'
  | 'pipeline:metadata'
  | 'pipeline:language'
  | 'pipeline:output'
  | 'pipeline:images'
  | 'pipeline:performance'
  | 'pipeline:submit';

export type SelectedView =
  | PipelineMenuView
  | typeof ADMIN_USER_MANAGEMENT_VIEW
  | typeof ADMIN_READING_BEDS_VIEW
  | typeof ADMIN_SETTINGS_VIEW
  | typeof ADMIN_SYSTEM_VIEW
  | typeof JOB_PROGRESS_VIEW
  | typeof JOB_MEDIA_VIEW
  | typeof LIBRARY_VIEW
  | typeof CREATE_BOOK_VIEW
  | typeof SUBTITLES_VIEW
  | typeof YOUTUBE_SUBTITLES_VIEW
  | typeof YOUTUBE_DUB_VIEW;

export const BOOK_NARRATION_SECTION_MAP: Record<PipelineMenuView, BookNarrationFormSection> = {
  'pipeline:source': 'source',
  'pipeline:metadata': 'metadata',
  'pipeline:language': 'language',
  'pipeline:output': 'output',
  'pipeline:images': 'images',
  'pipeline:performance': 'performance',
  'pipeline:submit': 'submit'
};

export const BOOK_NARRATION_SECTION_TO_VIEW: Record<BookNarrationFormSection, PipelineMenuView> = {
  source: 'pipeline:source',
  metadata: 'pipeline:metadata',
  language: 'pipeline:language',
  output: 'pipeline:output',
  images: 'pipeline:images',
  performance: 'pipeline:performance',
  submit: 'pipeline:submit'
};

const JOB_CREATION_VIEWS = new Set<SelectedView>([
  CREATE_BOOK_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW
]);

export const isJobCreationView = (view: SelectedView): boolean => {
  if (typeof view === 'string' && view.startsWith('pipeline:')) {
    return true;
  }
  return JOB_CREATION_VIEWS.has(view);
};

export const isPipelineView = (view: SelectedView): boolean =>
  typeof view === 'string' && view.startsWith('pipeline:');

export const APP_BRANCH =
  typeof __APP_BRANCH__ === 'string' && __APP_BRANCH__.trim()
    ? __APP_BRANCH__.trim()
    : (import.meta.env.VITE_APP_BRANCH as string | undefined)?.trim() || 'unknown';
