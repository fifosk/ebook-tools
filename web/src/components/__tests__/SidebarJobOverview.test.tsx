import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { JobState } from '../JobList';
import { SidebarJobOverview } from '../sidebar/SidebarJobOverview';

function makeJob(jobId: string, jobType: JobState['status']['job_type'], inputFile: string): JobState {
  return {
    jobId,
    status: {
      job_id: jobId,
      job_type: jobType,
      status: 'pending',
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
      result: null,
      error: null,
      latest_event: null,
      tuning: null,
      parameters: {
        input_file: inputFile,
        video_path: inputFile,
        subtitle_path: inputFile,
        target_languages: ['es']
      }
    },
    latestEvent: undefined,
    isReloading: false,
    isMutating: false,
    canManage: true
  };
}

describe('SidebarJobOverview', () => {
  it('renders an empty state when no jobs are available', () => {
    render(
      <SidebarJobOverview
        sidebarJobs={[]}
        activeJobId={null}
        onSelectJob={vi.fn()}
        onOpenPlayer={vi.fn()}
      />
    );

    expect(screen.getByText('No jobs yet.')).toBeInTheDocument();
  });

  it('groups jobs by cross-surface category and routes row actions', () => {
    const handleSelectJob = vi.fn();
    const handleOpenPlayer = vi.fn();
    const jobs = [
      makeJob('book-1', 'pipeline', '/books/current-book.epub'),
      makeJob('subtitle-1', 'subtitle', '/subs/current-show.srt'),
      makeJob('video-1', 'youtube_dub', '/videos/current-video.mp4')
    ];

    render(
      <SidebarJobOverview
        sidebarJobs={jobs}
        activeJobId="subtitle-1"
        onSelectJob={handleSelectJob}
        onOpenPlayer={handleOpenPlayer}
      />
    );

    expect(screen.getByText('🎧 Audiobooks')).toBeInTheDocument();
    expect(screen.getByText('🎞️ Subtitles')).toBeInTheDocument();
    expect(screen.getByText('📺 Videos')).toBeInTheDocument();

    const subtitleButton = screen
      .getAllByRole('button', { name: /current-show/i })
      .find((button) => button.classList.contains('sidebar__job-main'));
    if (!subtitleButton) {
      throw new Error('Expected subtitle job row.');
    }
    expect(subtitleButton).toHaveClass('is-active');
    fireEvent.click(subtitleButton);
    expect(handleSelectJob).toHaveBeenCalledWith('subtitle-1');

    fireEvent.click(screen.getByRole('button', { name: /Play current-video/i }));
    expect(handleOpenPlayer).toHaveBeenCalledWith('video-1', { autoPlay: true });
  });
});
