import { describe, expect, it } from 'vitest';
import {
  APPLE_CREATE_WEB_VIEW_BY_MODE,
  buildAppViewHandoffPath,
  parseAppView,
  parseDeepLinkedCreationTemplateId,
  parseDeepLinkedAppView
} from '../appViewDeepLink';

describe('app view deep links', () => {
  it('validates known app views', () => {
    expect(parseAppView('books:create')).toBe('books:create');
    expect(parseAppView(' pipeline:source ')).toBe('pipeline:source');
    expect(parseAppView('settings')).toBeNull();
    expect(parseAppView(null)).toBeNull();
  });

  it('reads explicit view query links before persisted UI state', () => {
    expect(parseDeepLinkedAppView({ search: '?view=subtitles%3Ayoutube-dub', hash: '' })).toBe(
      'subtitles:youtube-dub'
    );
  });

  it('supports hash fallbacks for static exports and local handoffs', () => {
    expect(parseDeepLinkedAppView({ search: '', hash: '#books:create' })).toBe('books:create');
    expect(parseDeepLinkedAppView({ search: '', hash: '#?view=pipeline%3Asubmit' })).toBe(
      'pipeline:submit'
    );
  });

  it('builds compact handoff paths', () => {
    expect(buildAppViewHandoffPath('books:create')).toBe('/?view=books%3Acreate');
    expect(buildAppViewHandoffPath('pipeline:source', { templateId: 'draft/template?1' })).toBe(
      '/?view=pipeline%3Asource&template_id=draft%2Ftemplate%3F1'
    );
  });

  it('reads template ids from query links and hash fallbacks', () => {
    expect(parseDeepLinkedCreationTemplateId({ search: '?template_id=draft%2Fone', hash: '' })).toBe(
      'draft/one'
    );
    expect(
      parseDeepLinkedCreationTemplateId({
        search: '',
        hash: '#?view=books%3Acreate&template_id=generated-template'
      })
    ).toBe('generated-template');
    expect(parseDeepLinkedCreationTemplateId({ search: '', hash: '#books:create' })).toBeNull();
  });

  it('keeps Apple creation modes mapped to Web creation views', () => {
    expect(APPLE_CREATE_WEB_VIEW_BY_MODE).toEqual({
      generatedBook: 'books:create',
      narrateEbook: 'pipeline:source',
      subtitleJob: 'subtitles:home',
      youtubeDub: 'subtitles:youtube-dub'
    });
  });
});
