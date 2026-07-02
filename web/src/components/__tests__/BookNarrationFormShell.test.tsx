import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  BOOK_NARRATION_SECTION_META,
  BOOK_NARRATION_TAB_SECTIONS,
} from '../book-narration/bookNarrationFormDefaults';
import { BookNarrationFormShell } from '../book-narration/BookNarrationFormShell';
import type { BookNarrationSubmitPresentation } from '../book-narration/bookNarrationFormUtils';

const submitPresentation: BookNarrationSubmitPresentation = {
  headerTitle: 'Narrate Ebook',
  headerDescription: 'Create narrated ebook assets.',
  missingRequirements: [],
  hasMissingRequirements: false,
  missingRequirementText: '',
  isSubmitDisabled: false,
  submitText: 'Submit job',
};

function renderShell(
  overrides: Partial<Parameters<typeof BookNarrationFormShell>[0]> = {},
) {
  const handleSubmit = vi.fn((event) => event.preventDefault());
  const handleSectionChange = vi.fn();
  const handleSaveTemplate = vi.fn();
  const props: Parameters<typeof BookNarrationFormShell>[0] = {
    showInfoHeader: true,
    submitPresentation,
    onSubmit: handleSubmit,
    tabSections: BOOK_NARRATION_TAB_SECTIONS,
    sectionMeta: BOOK_NARRATION_SECTION_META,
    activeTab: 'source',
    onSectionChange: handleSectionChange,
    isSubmitting: false,
    isSavingTemplate: false,
    onSaveTemplate: handleSaveTemplate,
    intakeStatus: null,
    isLoadingIntakeStatus: false,
    error: null,
    externalError: null,
    templateStatus: null,
    templateError: null,
    children: <div data-testid="section-panel">Section content</div>,
    ...overrides,
  };

  const rendered = render(<BookNarrationFormShell {...props} />);
  return { ...rendered, handleSubmit, handleSectionChange, handleSaveTemplate };
}

describe('BookNarrationFormShell', () => {
  it('renders header, step chrome, status area, and section content', () => {
    renderShell({
      templateStatus: 'Template saved',
      submitPresentation: {
        ...submitPresentation,
        hasMissingRequirements: true,
        missingRequirementText: 'input file',
      },
    });

    expect(screen.getByRole('heading', { name: 'Narrate Ebook' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Source/i })).toHaveClass('is-active');
    expect(screen.getByText('Template saved')).toBeInTheDocument();
    expect(screen.getByText('Provide input file before submitting.')).toBeInTheDocument();
    expect(screen.getByTestId('section-panel')).toHaveTextContent('Section content');
  });

  it('can hide the informational header without hiding form controls', () => {
    renderShell({ showInfoHeader: false });

    expect(screen.queryByRole('heading', { name: 'Narrate Ebook' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Submit job/i })).toBeInTheDocument();
  });

  it('routes submit, section, and template actions', () => {
    const { handleSubmit, handleSectionChange, handleSaveTemplate } = renderShell();

    fireEvent.click(screen.getByRole('tab', { name: /Language & translation/i }));
    expect(handleSectionChange).toHaveBeenCalledWith('language');

    fireEvent.click(screen.getByRole('button', { name: /Save template/i }));
    expect(handleSaveTemplate).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: /Submit job/i }));
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });
});
