import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { JobProgress } from '../JobProgress';
import { PipelineStatusResponse, ProgressEventPayload } from '../../api/dtos';

describe('JobProgress', () => {
  it('renders snapshot metrics when an event is supplied', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-1',
      status: 'completed',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      result: null,
      error: null,
      latest_event: null
    };

    const event: ProgressEventPayload = {
      event_type: 'update',
      timestamp: Date.now() / 1000,
      metadata: {},
      error: null,
      snapshot: {
        completed: 10,
        total: 20,
        elapsed: 5,
        speed: 2,
        eta: 5
      }
    };

    render(
      <JobProgress
        jobId="job-1"
        status={status}
        latestEvent={event}
        onEvent={vi.fn()}
        onRemove={vi.fn()}
        onReload={vi.fn()}
      />
    );

    expect(screen.getByText(/Latest progress/i)).toBeInTheDocument();
    expect(screen.getByText(/10 /)).toBeInTheDocument();
    expect(screen.getByText(/2.00 items/)).toBeInTheDocument();
  });

  it('renders metadata when present and enables reload control', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-2',
      status: 'completed',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      latest_event: null,
      error: null,
      result: {
        success: true,
        refined_updated: false,
        stitched_documents: {},
        book_metadata: {
          book_title: 'Example Title',
          book_author: 'Author Name'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-2"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onRemove={vi.fn()}
        onReload={vi.fn()}
      />
    );

    expect(screen.getByText('Example Title')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload metadata/i })).toBeEnabled();
  });

  it('renders pause and cancel controls for active jobs', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-3',
      status: 'running',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: null,
      result: null,
      error: null,
      latest_event: null
    };

    const handlePause = vi.fn();
    const handleCancel = vi.fn();

    render(
      <JobProgress
        jobId="job-3"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onRemove={vi.fn()}
        onReload={vi.fn()}
        onPause={handlePause}
        onCancel={handleCancel}
      />
    );

    const pauseButton = screen.getByRole('button', { name: /pause job job-3/i });
    const cancelButton = screen.getByRole('button', { name: /cancel job job-3/i });
    expect(pauseButton).toBeEnabled();
    expect(cancelButton).toBeEnabled();

    fireEvent.click(pauseButton);
    fireEvent.click(cancelButton);
    expect(handlePause).toHaveBeenCalled();
    expect(handleCancel).toHaveBeenCalled();
  });

  it('disables controls while pause or cancel is pending', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-4',
      status: 'running',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: null,
      result: null,
      error: null,
      latest_event: null
    };

    render(
      <JobProgress
        jobId="job-4"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onRemove={vi.fn()}
        onReload={vi.fn()}
        onPause={vi.fn()}
        onCancel={vi.fn()}
        isPausing
        isCancelling
      />
    );

    const pauseButton = screen.getByRole('button', { name: /pause job job-4/i });
    const cancelButton = screen.getByRole('button', { name: /cancel job job-4/i });
    expect(pauseButton).toBeDisabled();
    expect(cancelButton).toBeDisabled();
    expect(pauseButton).toHaveTextContent('Pausing…');
    expect(cancelButton).toHaveTextContent('Cancelling…');
  });
});
