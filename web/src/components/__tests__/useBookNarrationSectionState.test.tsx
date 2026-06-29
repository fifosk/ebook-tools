import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BOOK_NARRATION_TAB_SECTIONS } from '../book-narration/bookNarrationFormDefaults';
import { useBookNarrationSectionState } from '../book-narration/useBookNarrationSectionState';

describe('useBookNarrationSectionState', () => {
  it('starts on the requested active section when it is a tab section', () => {
    const { result } = renderHook(() =>
      useBookNarrationSectionState({
        activeSection: 'metadata',
        tabSections: BOOK_NARRATION_TAB_SECTIONS,
      }),
    );

    expect(result.current.activeTab).toBe('metadata');
  });

  it('falls back to source when the requested section is not in the tab list', () => {
    const { result } = renderHook(() =>
      useBookNarrationSectionState({
        activeSection: 'images',
        tabSections: ['source', 'metadata'],
      }),
    );

    expect(result.current.activeTab).toBe('source');
  });

  it('updates local state and forwards section changes', () => {
    const onSectionChange = vi.fn();
    const { result } = renderHook(() =>
      useBookNarrationSectionState({
        tabSections: BOOK_NARRATION_TAB_SECTIONS,
        onSectionChange,
      }),
    );

    act(() => {
      result.current.handleSectionChange('output');
    });

    expect(result.current.activeTab).toBe('output');
    expect(onSectionChange).toHaveBeenCalledWith('output');
  });

  it('syncs later external active-section changes without firing callbacks', () => {
    const onSectionChange = vi.fn();
    const { result, rerender } = renderHook(
      ({ activeSection }: { activeSection?: Parameters<typeof useBookNarrationSectionState>[0]['activeSection'] }) =>
        useBookNarrationSectionState({
          activeSection,
          tabSections: BOOK_NARRATION_TAB_SECTIONS,
          onSectionChange,
        }),
      { initialProps: { activeSection: 'source' } },
    );

    rerender({ activeSection: 'metadata' });

    expect(result.current.activeTab).toBe('metadata');
    expect(onSectionChange).not.toHaveBeenCalled();
  });
});
