import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { PipelineFileBrowserResponse } from '../../api/dtos';
import { BookNarrationFileDialog } from '../book-narration/BookNarrationFileDialog';

const fileOptions: PipelineFileBrowserResponse = {
  ebooks: [
    { name: 'latest.epub', path: '/books/latest.epub', type: 'file' }
  ],
  outputs: [
    { name: 'Outbox', path: '/output', type: 'directory' }
  ],
  books_root: '/books',
  output_root: '/output'
};

describe('BookNarrationFileDialog', () => {
  it('renders nothing without an active dialog and file options', () => {
    const { container, rerender } = render(
      <BookNarrationFileDialog
        activeFileDialog={null}
        fileOptions={fileOptions}
        onInputFileSelect={vi.fn()}
        onOutputPathSelect={vi.fn()}
        onClose={vi.fn()}
        onDeleteEbook={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();

    rerender(
      <BookNarrationFileDialog
        activeFileDialog="input"
        fileOptions={null}
        onInputFileSelect={vi.fn()}
        onOutputPathSelect={vi.fn()}
        onClose={vi.fn()}
        onDeleteEbook={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('routes input selection and ebook deletion', () => {
    const handleInputSelect = vi.fn();
    const handleClose = vi.fn();
    const handleDelete = vi.fn();

    render(
      <BookNarrationFileDialog
        activeFileDialog="input"
        fileOptions={fileOptions}
        onInputFileSelect={handleInputSelect}
        onOutputPathSelect={vi.fn()}
        onClose={handleClose}
        onDeleteEbook={handleDelete}
      />
    );

    expect(screen.getByRole('dialog', { name: /Select ebook file/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Select latest.epub/i }));
    expect(handleInputSelect).toHaveBeenCalledWith('/books/latest.epub');
    expect(handleClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: /Delete latest.epub/i }));
    expect(handleDelete).toHaveBeenCalledWith(fileOptions.ebooks[0]);
  });

  it('routes output path selection without delete controls', () => {
    const handleOutputSelect = vi.fn();
    const handleClose = vi.fn();

    render(
      <BookNarrationFileDialog
        activeFileDialog="output"
        fileOptions={fileOptions}
        onInputFileSelect={vi.fn()}
        onOutputPathSelect={handleOutputSelect}
        onClose={handleClose}
        onDeleteEbook={vi.fn()}
      />
    );

    expect(screen.getByRole('dialog', { name: /Select output path/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Delete Outbox/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Select Outbox/i }));
    expect(handleOutputSelect).toHaveBeenCalledWith('/output');
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
