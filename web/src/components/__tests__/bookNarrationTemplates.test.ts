import { describe, expect, it } from 'vitest';
import type { AcquisitionCandidate, CreationTemplateEntry } from '../../api/dtos';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import {
  buildBookDiscoveryTemplateState,
  buildBookNarrationTemplatePayload,
  buildSparseBookDiscoveryTemplateState,
  extractBookNarrationTemplateFormState
} from '../book-narration/bookNarrationTemplates';

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'gutenberg:123',
    provider: 'gutenberg',
    media_kind: 'book',
    title: 'Portable Book',
    rights: 'public_domain',
    capabilities: ['metadata', 'acquire'],
    candidate_token: 'secret-token',
    contributors: ['Author'],
    language: ' en ',
    year: 2026,
    source_url: ' https://example.test/book ',
    cover_url: ' https://example.test/cover.jpg ',
    local_path: ' /books/portable.epub ',
    subtitles: [],
    metadata: {},
    requires_confirmation: true,
    policy_notes: [],
    ...overrides
  };
}

describe('bookNarrationTemplates', () => {
  it('builds compact discovery template state without raw candidate tokens', () => {
    const state = buildBookDiscoveryTemplateState(candidate(), {
      provider: 'gutenberg',
      query: ' portable mystery ',
      selectedPath: ' /books/selected.epub ',
      preparedMetadata: {
        source_provider: ' internet_archive ',
        acquisition_provider: ' gutenberg ',
        acquisition_candidate_id: ' gutenberg:123 ',
        source_kind: ' acquired_epub ',
        source_url: (
          ' https://user:secret@indexer.example.invalid/download/demo.epub' +
          '?title=Demo&apikey=secret#name=Demo&access_token=secret '
        ),
        candidate_token: 'drop-me',
        authorization: 'Bearer drop-me'
      }
    });

    expect(state).toEqual({
      media_kind: 'book',
      provider: 'gutenberg',
      candidate_id: 'gutenberg:123',
      title: 'Portable Book',
      rights: 'public_domain',
      capabilities: ['metadata', 'acquire'],
      selected_provider: 'gutenberg',
      query: 'portable mystery',
      selected_path: '/books/selected.epub',
      source_provider: 'internet_archive',
      acquisition_provider: 'gutenberg',
      acquisition_candidate_id: 'gutenberg:123',
      source_kind: 'acquired_epub',
      local_path: '/books/portable.epub',
      source_url: 'https://indexer.example.invalid/download/demo.epub?title=Demo#name=Demo',
      cover_url: 'https://example.test/cover.jpg',
      language: 'en',
      year: 2026
    });
    expect(JSON.stringify(state)).not.toContain('secret-token');
    expect(JSON.stringify(state)).not.toContain('drop-me');
    expect(JSON.stringify(state)).not.toContain('apikey');
    expect(JSON.stringify(state)).not.toContain('access_token');
  });

  it('omits blank optional discovery fields from saved template state', () => {
    const state = buildBookDiscoveryTemplateState(candidate({
      language: '   ',
      year: null,
      source_url: '',
      cover_url: null,
      local_path: undefined
    }), {
      provider: 'openlibrary',
      query: '',
      selectedPath: ' '
    });

    expect(state).toEqual({
      media_kind: 'book',
      provider: 'gutenberg',
      candidate_id: 'gutenberg:123',
      title: 'Portable Book',
      rights: 'public_domain',
      capabilities: ['metadata', 'acquire'],
      selected_provider: 'openlibrary'
    });
  });

  it('builds sparse provider/query discovery template state before candidate selection', () => {
    expect(buildSparseBookDiscoveryTemplateState({
      provider: ' manual_downloads ',
      query: '  dan brown origin  '
    })).toEqual({
      media_kind: 'book',
      provider: 'manual_downloads',
      selected_provider: 'manual_downloads',
      query: 'dan brown origin'
    });
    expect(buildSparseBookDiscoveryTemplateState({
      provider: 'local_epub',
      query: '   '
    })).toEqual({
      media_kind: 'book',
      provider: 'local_epub',
      selected_provider: 'local_epub'
    });
    expect(buildSparseBookDiscoveryTemplateState({
      provider: '   ',
      query: 'ignored'
    })).toBeNull();
  });

  it('builds sanitized Web creation templates without environment secrets', () => {
    const payload = buildBookNarrationTemplatePayload({
      formState: {
        ...DEFAULT_FORM_STATE,
        input_file: '/books/origin.epub',
        base_output_file: 'dan-brown-next',
        target_languages: ['German'],
        custom_target_languages: 'French, German',
        config: '{"book_title":"Portable Template","api_key":"drop-me"}',
        environment_overrides: '{"authToken":"drop-me","PUBLIC_VALUE":"also-drop"}',
        pipeline_overrides: '{"voice":"gTTS","nested":{"password":"drop-me","safe":true}}',
        book_metadata: '{"book_title":"Portable Template","secret_note":"drop-me"}'
      },
      normalizedTargetLanguages: ['German', 'French'],
      sourceMode: 'upload',
      activeSection: 'source',
      payloadExtras: {
        handoff_source: 'apple',
        source: 'should-not-overwrite',
        form_state: { input_file: 'should-not-overwrite' }
      }
    });

    expect(payload).toMatchObject({
      name: 'Portable Template',
      mode: 'narrate_ebook',
      payload: {
        kind: 'book_narration_form',
        source: 'web',
        handoff_source: 'apple',
        source_mode: 'upload',
        active_section: 'source'
      }
    });

    const formState = payload.payload.form_state as Record<string, unknown>;
    expect(formState.target_languages).toEqual(['German', 'French']);
    expect(formState.custom_target_languages).toBe('');
    expect(formState.environment_overrides).toBe('{}');
    expect(formState.config).toBe('{\n  "book_title": "Portable Template"\n}');
    expect(formState.pipeline_overrides).toBe('{\n  "voice": "gTTS",\n  "nested": {\n    "safe": true\n  }\n}');
    expect(formState.book_metadata).toBe('{\n  "book_title": "Portable Template"\n}');
    expect(JSON.stringify(payload)).not.toContain('drop-me');
  });

  it('includes sanitized generated-book prompt state when provided', () => {
    const payload = buildBookNarrationTemplatePayload({
      formState: {
        ...DEFAULT_FORM_STATE,
        base_output_file: 'next-dan-brown'
      },
      normalizedTargetLanguages: ['Arabic'],
      sourceMode: 'generated',
      activeSection: 'language',
      payloadExtras: {
        generator_state: {
          topic: 'Continue the current Dan Brown book',
          book_name: 'Cipher Continuation',
          genre: 'Mystery thriller',
          author: 'Me',
          num_sentences: 60,
          api_key: 'drop-me'
        },
        form_state: {
          input_file: 'should-not-overwrite'
        }
      }
    });

    expect(payload.mode).toBe('generated_book');
    expect(payload.payload.generator_state).toEqual({
      topic: 'Continue the current Dan Brown book',
      book_name: 'Cipher Continuation',
      genre: 'Mystery thriller',
      author: 'Me',
      num_sentences: 60
    });
    expect((payload.payload.form_state as Record<string, unknown>).base_output_file).toBe(
      'next-dan-brown'
    );
    expect(JSON.stringify(payload)).not.toContain('drop-me');
    expect(JSON.stringify(payload)).not.toContain('should-not-overwrite');
  });

  it('extracts compatible template form state for Web handoff', () => {
    const template: CreationTemplateEntry = {
      id: 'template-1',
      name: 'Portable',
      mode: 'narrate_ebook',
      created_at: 1,
      updated_at: 2,
      payload: {
        kind: 'book_narration_form',
        source_mode: 'upload',
        active_section: 'language',
        discovery_state: {
          media_kind: 'book',
          provider: 'local_epub',
          candidate_id: 'local_epub:current.epub',
          selected_path: '/books/current.epub',
          candidate_token: 'drop-me'
        },
        form_state: {
          input_file: '/books/current.epub',
          input_language: 'English',
          target_languages: ['Arabic', 'German'],
          generate_audio: false,
          tempo: '1.25',
          voice_overrides: {
            en: 'macOS-auto',
            empty: ''
          },
          unknown_field: 'ignored'
        }
      }
    };

    expect(extractBookNarrationTemplateFormState(template, 'upload')).toEqual({
      activeSection: 'language',
      discoveryState: {
        media_kind: 'book',
        provider: 'local_epub',
        candidate_id: 'local_epub:current.epub',
        selected_path: '/books/current.epub'
      },
      formState: {
        input_file: '/books/current.epub',
        input_language: 'English',
        target_languages: ['Arabic', 'German'],
        generate_audio: false,
        tempo: 1.25,
        voice_overrides: {
          en: 'macOS-auto'
        }
      }
    });
    expect(extractBookNarrationTemplateFormState(template, 'generated')).toBeNull();
  });

  it('extracts sparse discovery-only template state for cross-surface handoff', () => {
    const template: CreationTemplateEntry = {
      id: 'template-apple-sparse',
      name: 'Sparse Apple discovery',
      mode: 'narrate_ebook',
      created_at: 1,
      updated_at: 2,
      payload: {
        kind: 'book_narration_form',
        source_mode: 'upload',
        discovery_state: {
          media_kind: 'book',
          provider: 'local_epub',
          candidate_id: 'local_epub:current.epub',
          selected_provider: 'local_epub',
          selected_path: '/books/current.epub',
          local_path: '/books/current.epub',
          title: 'Current Book',
          rights: 'user_provided',
          capabilities: ['metadata'],
          language: 'en',
          year: 2026,
          candidate_token: 'drop-me'
        },
        form_state: {}
      }
    };

    expect(extractBookNarrationTemplateFormState(template, 'upload')).toEqual({
      activeSection: null,
      discoveryState: {
        media_kind: 'book',
        provider: 'local_epub',
        candidate_id: 'local_epub:current.epub',
        selected_provider: 'local_epub',
        selected_path: '/books/current.epub',
        local_path: '/books/current.epub',
        title: 'Current Book',
        rights: 'user_provided',
        capabilities: ['metadata'],
        language: 'en',
        year: 2026
      },
      formState: {}
    });
  });
});
