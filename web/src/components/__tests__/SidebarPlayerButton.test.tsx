import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { JobState } from '../JobList';
import { SidebarPlayerButton } from '../sidebar/SidebarPlayerButton';

const activeJob: JobState = {
  jobId: 'player-1',
  status: {
    job_id: 'player-1',
    job_type: 'pipeline',
    status: 'completed',
    created_at: new Date().toISOString(),
    started_at: null,
    completed_at: new Date().toISOString(),
    result: null,
    error: null,
    latest_event: null,
    tuning: null,
    parameters: {
      target_languages: ['fr'],
      input_file: '/books/player-title.epub'
    }
  },
  latestEvent: undefined,
  isReloading: false,
  isMutating: false,
  canManage: true
};

describe('SidebarPlayerButton', () => {
  it('disables the player entry when no job is selected', () => {
    const handleOpenPlayer = vi.fn();

    render(
      <SidebarPlayerButton
        selectedView="library:list"
        jobMediaView="job:media"
        activeJob={null}
        onOpenPlayer={handleOpenPlayer}
      />
    );

    const button = screen.getByRole('button', { name: /player select a job/i });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(handleOpenPlayer).not.toHaveBeenCalled();
  });

  it('renders active job metadata and opens the player', () => {
    const handleOpenPlayer = vi.fn();

    render(
      <SidebarPlayerButton
        selectedView="job:media"
        jobMediaView="job:media"
        activeJob={activeJob}
        onOpenPlayer={handleOpenPlayer}
      />
    );

    const button = screen.getByRole('button', { name: /player-title/i });
    expect(button).toHaveClass('is-active');
    expect(screen.getByLabelText('Completed')).toBeInTheDocument();
    expect(screen.getByLabelText('French')).toBeInTheDocument();

    fireEvent.click(button);
    expect(handleOpenPlayer).toHaveBeenCalledWith();
  });
});
