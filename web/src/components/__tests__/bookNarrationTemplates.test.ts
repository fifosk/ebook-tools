import { describe, expect, it } from 'vitest';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import { buildBookNarrationTemplatePayload } from '../book-narration/bookNarrationTemplates';

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
});
