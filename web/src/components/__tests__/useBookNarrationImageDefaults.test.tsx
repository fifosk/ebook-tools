import { renderHook, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import type { FormState, ImageDefaults } from '../book-narration/bookNarrationFormTypes';
import { useBookNarrationImageDefaults } from '../book-narration/useBookNarrationImageDefaults';

type RenderImageDefaultsOptions = {
  hasPrefillAddImages?: boolean;
  imageDefaults?: ImageDefaults | null;
  initialState?: FormState;
};

const DEFAULT_IMAGE_SETTINGS: ImageDefaults = {
  add_images: true,
  image_prompt_pipeline: 'visual-canon',
  image_style_template: 'watercolor',
  image_prompt_context_sentences: 99,
  image_width: '1024',
  image_height: '768',
};

function renderImageDefaultsHook({
  hasPrefillAddImages = false,
  imageDefaults = DEFAULT_IMAGE_SETTINGS,
  initialState = DEFAULT_FORM_STATE,
}: RenderImageDefaultsOptions = {}) {
  return renderHook(({ nextImageDefaults, nextHasPrefillAddImages }) => {
    const [formState, setFormState] = useState<FormState>(initialState);
    const imageDefaultsState = useBookNarrationImageDefaults({
      hasPrefillAddImages: nextHasPrefillAddImages,
      imageDefaults: nextImageDefaults,
      setFormState,
    });

    return {
      formState,
      ...imageDefaultsState,
    };
  }, {
    initialProps: {
      nextHasPrefillAddImages: hasPrefillAddImages,
      nextImageDefaults: imageDefaults,
    },
  });
}

describe('useBookNarrationImageDefaults', () => {
  it('applies backend image defaults to unedited form state', async () => {
    const { result } = renderImageDefaultsHook();

    await waitFor(() => {
      expect(result.current.formState.image_width).toBe('1024');
    });

    expect(result.current.formState.add_images).toBe(true);
    expect(result.current.formState.image_prompt_pipeline).toBe('visual_canon');
    expect(result.current.formState.image_style_template).toBe('watercolor');
    expect(result.current.formState.image_prompt_context_sentences).toBe(50);
    expect(result.current.formState.image_height).toBe('768');
  });

  it('keeps user-edited image default fields across backend default changes', async () => {
    const { result, rerender } = renderImageDefaultsHook({
      imageDefaults: null,
      initialState: {
        ...DEFAULT_FORM_STATE,
        image_width: '256',
      },
    });

    result.current.userEditedImageDefaultsRef.current.add('image_width');

    rerender({
      nextHasPrefillAddImages: false,
      nextImageDefaults: DEFAULT_IMAGE_SETTINGS,
    });

    await waitFor(() => {
      expect(result.current.formState.image_height).toBe('768');
    });
    expect(result.current.formState.image_width).toBe('256');
  });

  it('does not override prefilled add_images choices', async () => {
    const { result } = renderImageDefaultsHook({
      hasPrefillAddImages: true,
      initialState: {
        ...DEFAULT_FORM_STATE,
        add_images: false,
      },
    });

    await waitFor(() => {
      expect(result.current.formState.image_prompt_pipeline).toBe('visual_canon');
    });

    expect(result.current.formState.add_images).toBe(false);
  });
});
