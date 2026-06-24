import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  BOOK_NARRATION_SECTION_META,
  BOOK_NARRATION_TAB_SECTIONS
} from '../book-narration/bookNarrationFormDefaults';
import { BookNarrationStepBar } from '../book-narration/BookNarrationStepBar';

describe('BookNarrationStepBar', () => {
  it('renders pipeline tabs and routes section changes', () => {
    const handleSectionChange = vi.fn();

    render(
      <BookNarrationStepBar
        tabSections={BOOK_NARRATION_TAB_SECTIONS}
        sectionMeta={BOOK_NARRATION_SECTION_META}
        activeTab="language"
        onSectionChange={handleSectionChange}
        isSubmitDisabled={false}
        isSubmitting={false}
        submitText="Submit job"
      />
    );

    const languageTab = screen.getByRole('tab', { name: /Language & translation/i });
    expect(languageTab).toHaveClass('is-active');
    expect(languageTab).toHaveAttribute('aria-selected', 'true');

    fireEvent.click(screen.getByRole('tab', { name: /Output & narration/i }));
    expect(handleSectionChange).toHaveBeenCalledWith('output');
  });

  it('reflects submit disabled and submitting states', () => {
    const { rerender } = render(
      <BookNarrationStepBar
        tabSections={BOOK_NARRATION_TAB_SECTIONS}
        sectionMeta={BOOK_NARRATION_SECTION_META}
        activeTab="source"
        onSectionChange={vi.fn()}
        isSubmitDisabled={true}
        isSubmitting={false}
        submitText="Create book"
      />
    );

    expect(screen.getByRole('button', { name: /Create book/i })).toBeDisabled();

    rerender(
      <BookNarrationStepBar
        tabSections={BOOK_NARRATION_TAB_SECTIONS}
        sectionMeta={BOOK_NARRATION_SECTION_META}
        activeTab="source"
        onSectionChange={vi.fn()}
        isSubmitDisabled={true}
        isSubmitting={true}
        submitText="Create book"
      />
    );

    expect(screen.getByRole('button', { name: /Submitting/i })).toBeDisabled();
  });
});
