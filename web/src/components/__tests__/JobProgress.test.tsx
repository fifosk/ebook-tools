import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { JobProgress } from '../JobProgress';
import { PipelineStatusResponse, ProgressEventPayload } from '../../api/dtos';

class MockEventSource {
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(): void {}

  removeEventListener(): void {}

  dispatchEvent(): boolean {
    return true;
  }

  close(): void {}
}

beforeAll(() => {
  // @ts-expect-error jsdom does not provide EventSource by default
  global.EventSource = MockEventSource;
});

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
      latest_event: null,
      tuning: null
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
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
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
      tuning: null,
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
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
      />
    );

    expect(screen.getByText('Example Title')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload metadata/i })).toBeEnabled();
  });

  it('renders tuning metrics when provided', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-3',
      status: 'running',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: null,
      result: null,
      error: null,
      latest_event: null,
      tuning: {
        thread_count: 4,
        queue_size: 32,
        job_worker_slots: 2
      }
    };

    render(
      <JobProgress
        jobId="job-3"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
      />
    );

    expect(screen.getByText('Performance tuning')).toBeInTheDocument();
    expect(screen.getByText('Translation threads')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Translation queue size')).toBeInTheDocument();
    expect(screen.getByText('32')).toBeInTheDocument();
  });
});
