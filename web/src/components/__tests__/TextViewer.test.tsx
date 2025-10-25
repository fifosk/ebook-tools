import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TextViewer, { TextFile } from '../TextViewer';

describe('TextViewer', () => {
  it('shows loading state until files are available', () => {
    render(<TextViewer files={[]} />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading text files');
  });

  it('supports progressive updates and selection changes', async () => {
    const user = userEvent.setup();
    const initialFile: TextFile = {
      id: 'intro',
      name: 'Introduction',
      content: 'Welcome to the preview.'
    };
    const additionalFile: TextFile = {
      id: 'chapter-1',
      name: 'Chapter 1',
      content: 'This is the first chapter.'
    };

    const { rerender } = render(<TextViewer files={[initialFile]} />);

    expect(screen.getByRole('tab', { name: 'Introduction' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('text-viewer-content')).toHaveTextContent('Welcome to the preview.');

    rerender(<TextViewer files={[initialFile, additionalFile]} />);

    expect(screen.getByRole('tab', { name: 'Introduction' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('text-viewer-content')).toHaveTextContent('Welcome to the preview.');

    await user.click(screen.getByRole('tab', { name: 'Chapter 1' }));

    expect(screen.getByRole('tab', { name: 'Chapter 1' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('text-viewer-content')).toHaveTextContent('This is the first chapter.');
  });
});
