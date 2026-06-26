import { describe, expect, it } from 'vitest';
import type { CreationTemplateEntry } from '../../api/dtos';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import {
  buildBookNarrationTemplatePayload,
  extractBookNarrationTemplateFormState
} from '../book-narration/bookNarrationTemplates';

describe('bookNarrationTemplates', () => {
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
      activeSection: 'source'
    });

    expect(payload).toMatchObject({
      name: 'Portable Template',
      mode: 'narrate_ebook',
      payload: {
        kind: 'book_narration_form',
        source: 'web',
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
});
