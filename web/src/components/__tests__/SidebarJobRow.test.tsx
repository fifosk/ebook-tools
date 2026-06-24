import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { JobState } from '../JobList';
import { SidebarJobRow } from '../sidebar/SidebarJobRow';

const runningJob: JobState = {
  jobId: 'row-1',
  status: {
    job_id: 'row-1',
    job_type: 'pipeline',
    status: 'running',
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    completed_at: null,
    result: null,
    error: null,
    latest_event: null,
    tuning: null,
    parameters: {
      target_languages: ['es'],
      input_file: '/books/current-book.epub'
    }
  },
  latestEvent: {
    event_type: 'progress',
    timestamp: Date.now(),
    metadata: {},
    snapshot: {
      completed: 3,
      total: 4,
      elapsed: 10,
      speed: 1,
      eta: 4
    },
    error: null
  },
  isReloading: false,
  isMutating: false,
  canManage: true
};

describe('SidebarJobRow', () => {
  it('renders active job metadata and routes row actions', () => {
    const handleSelectJob = vi.fn();
    const handleOpenPlayer = vi.fn();

    render(
      <ul>
        <SidebarJobRow
          job={runningJob}
          activeJobId="row-1"
          onSelectJob={handleSelectJob}
          onOpenPlayer={handleOpenPlayer}
        />
      </ul>
    );

    const jobButton = screen
      .getAllByRole('button', { name: /current-book/i })
      .find((button) => button.classList.contains('sidebar__job-main'));
    if (!jobButton) {
      throw new Error('Expected to find the main job row button.');
    }
    expect(jobButton).toHaveClass('is-active');
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByLabelText('Running')).toBeInTheDocument();

    fireEvent.click(jobButton);
    expect(handleSelectJob).toHaveBeenCalledWith('row-1');

    fireEvent.click(screen.getByRole('button', { name: /play current-book/i }));
    expect(handleOpenPlayer).toHaveBeenCalledWith('row-1', { autoPlay: true });
    expect(handleSelectJob).toHaveBeenCalledTimes(1);
  });
});
