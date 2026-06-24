import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SidebarCreationLinks } from '../sidebar/SidebarCreationLinks';

const defaultProps = {
  createBookView: 'books:create',
  subtitlesView: 'subtitles:home',
  youtubeSubtitlesView: 'subtitles:youtube',
  youtubeDubView: 'subtitles:youtube-dub'
} as const;

describe('SidebarCreationLinks', () => {
  it('marks pipeline book creation as active across pipeline subviews', () => {
    render(
      <SidebarCreationLinks
        {...defaultProps}
        selectedView="pipeline:language"
        onSelectView={vi.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /Book Page/i })).toHaveClass('is-active');
    expect(screen.getByRole('button', { name: /Create Audiobook/i })).not.toHaveClass('is-active');
  });

  it('routes each creation entry to its configured view', () => {
    const handleSelectView = vi.fn();

    render(
      <SidebarCreationLinks
        {...defaultProps}
        selectedView="library:list"
        onSelectView={handleSelectView}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Book Page/i }));
    fireEvent.click(screen.getByRole('button', { name: /Create Audiobook/i }));
    fireEvent.click(screen.getByRole('button', { name: /Subtitles/i }));
    fireEvent.click(screen.getByRole('button', { name: /YouTube Video/i }));
    fireEvent.click(screen.getByRole('button', { name: /Dub Video/i }));

    expect(handleSelectView.mock.calls).toEqual([
      ['pipeline:source'],
      ['books:create'],
      ['subtitles:home'],
      ['subtitles:youtube'],
      ['subtitles:youtube-dub']
    ]);
  });
});
