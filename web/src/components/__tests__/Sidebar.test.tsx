import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { JobState } from '../JobList';
import Sidebar from '../Sidebar';

const sampleJob: JobState = {
  jobId: '123',
  status: {
    job_id: '123',
    status: 'running',
    created_at: new Date().toISOString(),
    started_at: null,
    completed_at: null,
    result: null,
    error: null,
    latest_event: null,
    tuning: null,
    user_id: 'user'
  },
  latestEvent: undefined,
  isReloading: false,
  isMutating: false,
  canManage: true
};

describe('Sidebar', () => {
  it('renders the New immersive book entry as active for pipeline views', () => {
    render(
      <Sidebar
        selectedView="pipeline:source"
        onSelectView={vi.fn()}
        sidebarJobs={[sampleJob]}
        activeJobId={null}
        onSelectJob={vi.fn()}
        onOpenPlayer={vi.fn()}
        isAdmin={false}
        createBookView="books:create"
        libraryView="library:list"
        jobMediaView="job:media"
        adminView="admin:users"
      />
    );

    const immersiveButton = screen.getByRole('button', { name: /New immersive book/i });
    expect(immersiveButton).toBeInTheDocument();
    expect(immersiveButton).toHaveClass('is-active');

    expect(screen.getByRole('button', { name: /Create book/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Browse library/i })).toBeInTheDocument();
  });

  it('invokes callbacks when selecting different entries', () => {
    const handleSelectView = vi.fn();
    const handleSelectJob = vi.fn();
    const handleOpenPlayer = vi.fn();

    render(
      <Sidebar
        selectedView="library:list"
        onSelectView={handleSelectView}
        sidebarJobs={[sampleJob]}
        activeJobId={null}
        onSelectJob={handleSelectJob}
        onOpenPlayer={handleOpenPlayer}
        isAdmin={true}
        createBookView="books:create"
        libraryView="library:list"
        jobMediaView="job:media"
        adminView="admin:users"
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /New immersive book/i }));
    fireEvent.click(screen.getByRole('button', { name: /User management/i }));
    expect(handleSelectView.mock.calls).toContainEqual(['pipeline:source']);
    expect(handleSelectView.mock.calls).toContainEqual(['admin:users']);

    fireEvent.click(screen.getByRole('button', { name: /Job 123/i }));
    expect(handleSelectJob).toHaveBeenCalledWith('123');

    const playerButton = screen.getByRole('button', { name: /Select a job to open the player/i });
    expect(playerButton).toBeDisabled();
    fireEvent.click(playerButton);
    expect(handleOpenPlayer).not.toHaveBeenCalled();
  });
});
