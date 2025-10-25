import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import TextViewer, { type TextFile } from '../TextViewer';

describe('TextViewer', () => {
  it('shows loading state while waiting for content', () => {
    render(<TextViewer file={null} isLoading />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading text files');
  });

  it('renders inline content when provided', () => {
    const file: TextFile = {
      id: 'intro',
      name: 'Introduction',
      content: 'Welcome to the preview.'
    };

    render(<TextViewer file={file} />);

    expect(screen.getByTestId('text-viewer-content')).toHaveTextContent('Welcome to the preview.');
    expect(screen.getByText('Introduction')).toBeInTheDocument();
  });

  it('opens a new tab for linked documents', async () => {
    const user = userEvent.setup();
    const file: TextFile = {
      id: 'chapter-1',
      name: 'Chapter 1',
      url: 'https://example.com/chapter-1.pdf'
    };

    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    render(<TextViewer file={file} />);

    await user.click(screen.getByRole('button', { name: /open document/i }));

    expect(openSpy).toHaveBeenCalledWith(file.url, '_blank', 'noopener');

    openSpy.mockRestore();
  });

  it('shows waiting message when no text file is active', () => {
    render(<TextViewer file={null} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for text files');
  });
});
