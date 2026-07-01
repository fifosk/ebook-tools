import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { CreationTemplateEntry, CreationTemplatePayload } from '../../api/dtos';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import { useBookNarrationTemplateSave } from '../book-narration/useBookNarrationTemplateSave';

describe('useBookNarrationTemplateSave', () => {
  it('saves a narrate ebook template and reports success state', async () => {
    const saveTemplate = vi.fn(
      async (payload: CreationTemplatePayload): Promise<CreationTemplateEntry> => ({
        id: 'template-1',
        name: 'travel-book',
        mode: 'narrate_ebook',
        created_at: 1,
        updated_at: 2,
        payload: payload.payload,
      }),
    );
    const { result } = renderHook(() =>
      useBookNarrationTemplateSave({
        activeSection: 'language',
        formState: {
          ...DEFAULT_FORM_STATE,
          base_output_file: 'travel-book',
          target_languages: ['German'],
        },
        normalizedTargetLanguages: ['German'],
        payloadExtras: { discovery_provider: 'backend_defaults' },
        saveTemplate,
        sourceMode: 'upload',
      }),
    );

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(saveTemplate).toHaveBeenCalledTimes(1);
    expect(saveTemplate.mock.calls[0][0]).toMatchObject({
      mode: 'narrate_ebook',
      name: 'travel-book',
      payload: {
        active_section: 'language',
        discovery_provider: 'backend_defaults',
        form_state: expect.objectContaining({
          base_output_file: 'travel-book',
          target_languages: ['German'],
        }),
      },
    });
    expect(result.current.templateStatus).toBe('Saved template "travel-book".');
    expect(result.current.effectiveTemplateStatus).toBe('Saved template "travel-book".');
    expect(result.current.templateError).toBeNull();
    expect(result.current.isSavingTemplate).toBe(false);
  });

  it('reports save errors while external template load errors keep precedence', async () => {
    const saveTemplate = vi.fn(async () => {
      throw new Error('template store unavailable');
    });
    const { result } = renderHook(() =>
      useBookNarrationTemplateSave({
        activeSection: 'source',
        creationTemplateError: 'Saved template could not be loaded.',
        formState: DEFAULT_FORM_STATE,
        isLoadingCreationTemplate: true,
        normalizedTargetLanguages: ['Arabic'],
        saveTemplate,
        sourceMode: 'generated',
      }),
    );

    expect(result.current.effectiveTemplateStatus).toBe('Loading saved template...');
    expect(result.current.effectiveTemplateError).toBe('Saved template could not be loaded.');

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(result.current.templateStatus).toBeNull();
    expect(result.current.templateError).toBe('template store unavailable');
    expect(result.current.effectiveTemplateError).toBe('Saved template could not be loaded.');
    expect(result.current.isSavingTemplate).toBe(false);
  });
});
