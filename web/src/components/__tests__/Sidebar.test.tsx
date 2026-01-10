import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { JobState } from '../JobList';
import Sidebar from '../Sidebar';

const sampleJob: JobState = {
  jobId: '123',
  status: {
    job_id: '123',
    job_type: 'pipeline',
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

const youtubeDubJob: JobState = {
  jobId: 'dub-1',
  status: {
    job_id: 'dub-1',
    job_type: 'youtube_dub',
    status: 'pending',
    created_at: new Date().toISOString(),
    started_at: null,
    completed_at: null,
    result: { youtube_dub: { output_path: '/tmp/out.mp4' } },
    error: null,
    latest_event: null,
    tuning: null,
    parameters: {
      target_languages: ['es'],
      video_path: '/Volumes/Data/Download/DStation/sample.mp4',
      subtitle_path: '/Volumes/Data/Download/DStation/sample.es.ass'
    }
  },
  latestEvent: undefined,
  isReloading: false,
  isMutating: false,
  canManage: true
};

const runningWithProgress: JobState = {
  jobId: '789',
  status: {
    job_id: '789',
    job_type: 'pipeline',
    status: 'running',
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    completed_at: null,
    result: null,
    error: null,
    latest_event: null,
    tuning: null
  },
  latestEvent: {
    event_type: 'progress',
    timestamp: Date.now(),
    metadata: {},
    snapshot: {
      completed: 5,
      total: 10,
      elapsed: 5,
      speed: 1,
      eta: 5
    },
    error: null
  },
  isReloading: false,
  isMutating: false,
  canManage: true
};

describe('Sidebar', () => {
  it('renders the Narrate Ebook entry as active for pipeline views', () => {
    render(
      <Sidebar
        selectedView="pipeline:source"
        onSelectView={vi.fn()}
        sidebarJobs={[sampleJob]}
        activeJobId={null}
        onSelectJob={vi.fn()}
        onOpenPlayer={vi.fn()}
        isAdmin={false}
        canScheduleJobs={true}
        createBookView="books:create"
        libraryView="library:list"
        subtitlesView="subtitles:home"
	        youtubeSubtitlesView="subtitles:youtube"
	        youtubeDubView="subtitles:youtube-dub"
	        jobMediaView="job:media"
	        adminUserManagementView="admin:users"
	        adminReadingBedsView="admin:reading-beds"
	      />
	    );

    const narrateButton = screen.getByRole('button', { name: /Narrate Ebook/i });
    expect(narrateButton).toBeInTheDocument();
    expect(narrateButton).toHaveClass('is-active');
    expect(screen.getByRole('button', { name: /Subtitles/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /YouTube Video/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Dub Video/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create audiobook/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Browse library/i })).toBeInTheDocument();
    expect(screen.queryByText(/No subtitle jobs yet/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/No dubbing jobs yet/i)).not.toBeInTheDocument();
  });

  it('shows progress for running jobs with progress events', () => {
    render(
      <Sidebar
        selectedView="pipeline:source"
        onSelectView={vi.fn()}
        sidebarJobs={[runningWithProgress]}
        activeJobId={null}
        onSelectJob={vi.fn()}
        onOpenPlayer={vi.fn()}
        isAdmin={false}
        canScheduleJobs={true}
        createBookView="books:create"
        libraryView="library:list"
        subtitlesView="subtitles:home"
	        youtubeSubtitlesView="subtitles:youtube"
	        youtubeDubView="subtitles:youtube-dub"
	        jobMediaView="job:media"
	        adminUserManagementView="admin:users"
	        adminReadingBedsView="admin:reading-beds"
	      />
	    );

    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByLabelText('Running')).toBeInTheDocument();
  });

  it('invokes callbacks when selecting different entries', () => {
    const handleSelectView = vi.fn();
    const handleSelectJob = vi.fn();
    const handleOpenPlayer = vi.fn();

    render(
      <Sidebar
        selectedView="library:list"
        onSelectView={handleSelectView}
        sidebarJobs={[sampleJob, youtubeDubJob]}
        activeJobId={null}
        onSelectJob={handleSelectJob}
        onOpenPlayer={handleOpenPlayer}
        isAdmin={true}
        canScheduleJobs={true}
        createBookView="books:create"
        libraryView="library:list"
        subtitlesView="subtitles:home"
	        youtubeSubtitlesView="subtitles:youtube"
	        youtubeDubView="subtitles:youtube-dub"
	        jobMediaView="job:media"
	        adminUserManagementView="admin:users"
	        adminReadingBedsView="admin:reading-beds"
	      />
	    );

    fireEvent.click(screen.getByRole('button', { name: /Narrate Ebook/i }));
    fireEvent.click(screen.getByRole('button', { name: /^🎙️ Dub Video$/i }));
    fireEvent.click(screen.getByRole('button', { name: /User management/i }));
    expect(handleSelectView.mock.calls).toContainEqual(['pipeline:source']);
    expect(handleSelectView.mock.calls).toContainEqual(['subtitles:youtube-dub']);
    expect(handleSelectView.mock.calls).toContainEqual(['admin:users']);

    fireEvent.click(screen.getByRole('button', { name: /Job 123/i }));
    expect(handleSelectJob).toHaveBeenCalledWith('123');
    fireEvent.click(screen.getByRole('button', { name: /Spanish Pending/i }));
    expect(handleSelectJob).toHaveBeenCalledWith('dub-1');

    const playerButton = screen.getByRole('button', { name: /Player Select a job/i });
    expect(playerButton).toBeDisabled();
    fireEvent.click(playerButton);
    expect(handleOpenPlayer).not.toHaveBeenCalled();
  });
});
