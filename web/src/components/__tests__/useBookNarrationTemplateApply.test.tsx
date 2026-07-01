import { renderHook, waitFor } from '@testing-library/react';
import { useRef, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { CreationTemplateEntry } from '../../api/dtos';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import type { BookNarrationSourcePanel } from '../book-narration/BookNarrationSourceSection';
import type { BookNarrationFormSection, FormState } from '../book-narration/bookNarrationFormTypes';
import { useBookNarrationTemplateApply } from '../book-narration/useBookNarrationTemplateApply';

function template(overrides: Partial<CreationTemplateEntry> = {}): CreationTemplateEntry {
  return {
    id: 'template-1',
    name: 'Current book continuation',
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
        selected_path: '/books/current.epub',
      },
      form_state: {
        input_file: '/books/current.epub',
        input_language: 'Spanish',
        target_languages: ['German', 'French'],
        enable_lookup_cache: false,
        add_images: true,
      },
    },
    ...overrides,
  };
}

type HarnessOptions = {
  creationTemplate: CreationTemplateEntry | null;
  sourceMode?: 'upload' | 'generated';
};

function renderApplyHook({
  creationTemplate,
  sourceMode = 'upload',
}: HarnessOptions) {
  const handleSectionChange = vi.fn();
  const setSharedEnableLookupCache = vi.fn();
  const setSharedInputLanguage = vi.fn();
  const setSharedTargetLanguages = vi.fn();

  const rendered = renderHook(({ nextTemplate }) => {
    const [formState, setFormState] = useState<FormState>(DEFAULT_FORM_STATE);
    const [activeSourcePanel, setActiveSourcePanel] =
      useState<BookNarrationSourcePanel>('source');
    const [selectedDiscoveryTemplateState, setSelectedDiscoveryTemplateState] =
      useState<Record<string, unknown> | null>(null);
    const [templateStatus, setTemplateStatus] = useState<string | null>(null);
    const [templateError, setTemplateError] = useState<string | null>(null);
    const creationTemplateAppliedRef = useRef<string | null>(null);
    const lastAutoEndSentenceRef = useRef<string | null>('100');
    const userEditedEndRef = useRef(false);
    const userEditedFieldsRef = useRef<Set<keyof FormState>>(new Set());
    const userEditedImageDefaultsRef = useRef<Set<keyof FormState>>(new Set());
    const userEditedInputRef = useRef(false);
    const userEditedStartRef = useRef(false);

    useBookNarrationTemplateApply({
      creationTemplate: nextTemplate,
      creationTemplateAppliedRef,
      forcedBaseOutputFile: null,
      handleSectionChange,
      lastAutoEndSentenceRef,
      setActiveSourcePanel,
      setFormState,
      setSelectedDiscoveryTemplateState,
      setSharedEnableLookupCache,
      setSharedInputLanguage,
      setSharedTargetLanguages,
      setTemplateError,
      setTemplateStatus,
      sharedTargetLanguages: ['Arabic'],
      sourceMode,
      userEditedEndRef,
      userEditedFieldsRef,
      userEditedImageDefaultsRef,
      userEditedInputRef,
      userEditedStartRef,
    });

    return {
      activeSourcePanel,
      appliedKey: creationTemplateAppliedRef.current,
      formState,
      lastAutoEndSentence: lastAutoEndSentenceRef.current,
      selectedDiscoveryTemplateState,
      templateError,
      templateStatus,
      userEditedFields: Array.from(userEditedFieldsRef.current).sort(),
      userEditedImageDefaults: Array.from(userEditedImageDefaultsRef.current).sort(),
      userEditedInput: userEditedInputRef.current,
    };
  }, {
    initialProps: { nextTemplate: creationTemplate },
  });

  return {
    ...rendered,
    handleSectionChange,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
  };
}

describe('useBookNarrationTemplateApply', () => {
  it('applies compatible templates into form, discovery, section, and shared preference state', async () => {
    const { result, handleSectionChange, setSharedEnableLookupCache, setSharedInputLanguage, setSharedTargetLanguages } =
      renderApplyHook({ creationTemplate: template() });

    await waitFor(() => {
      expect(result.current.templateStatus).toBe('Applied template "Current book continuation".');
    });

    expect(result.current.formState).toMatchObject({
      input_file: '/books/current.epub',
      input_language: 'Spanish',
      target_languages: ['German'],
      custom_target_languages: 'French',
      enable_lookup_cache: false,
      add_images: true,
    });
    expect(result.current.activeSourcePanel).toBe('discovery');
    expect(result.current.selectedDiscoveryTemplateState).toMatchObject({
      provider: 'local_epub',
      selected_path: '/books/current.epub',
    });
    expect(result.current.appliedKey).toBe('template-1:2:upload');
    expect(result.current.lastAutoEndSentence).toBeNull();
    expect(result.current.userEditedInput).toBe(true);
    expect(result.current.userEditedFields).toContain('input_file');
    expect(result.current.userEditedImageDefaults).toContain('add_images');
    expect(handleSectionChange).toHaveBeenCalledWith('language');
    expect(setSharedTargetLanguages).toHaveBeenCalledWith(['German', 'French']);
    expect(setSharedInputLanguage).toHaveBeenCalledWith('Spanish');
    expect(setSharedEnableLookupCache).toHaveBeenCalledWith(false);
  });

  it('reports incompatible templates without applying form state', async () => {
    const { result } = renderApplyHook({
      creationTemplate: template({
        mode: 'generated_book',
        name: 'Generated draft',
        payload: {
          kind: 'book_narration_form',
          source_mode: 'generated',
          form_state: { input_file: '/books/generated.epub' },
        },
      }),
    });

    await waitFor(() => {
      expect(result.current.templateError).toBe(
        'Template "Generated draft" is not compatible with this book job.',
      );
    });

    expect(result.current.templateStatus).toBeNull();
    expect(result.current.formState.input_file).toBe('');
    expect(result.current.appliedKey).toBe('template-1:2:upload');
  });

  it('skips templates that were already applied', async () => {
    const firstTemplate = template();
    const { result, rerender, handleSectionChange } = renderApplyHook({
      creationTemplate: firstTemplate,
    });

    await waitFor(() => {
      expect(result.current.appliedKey).toBe('template-1:2:upload');
    });
    expect(handleSectionChange).toHaveBeenCalledTimes(1);

    rerender({ nextTemplate: firstTemplate });

    await waitFor(() => {
      expect(handleSectionChange).toHaveBeenCalledTimes(1);
    });
  });
});
