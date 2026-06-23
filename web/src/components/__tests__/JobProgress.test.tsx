import { beforeAll, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { JobProgress } from '../JobProgress';
import type { PipelineStatusResponse, ProgressEventPayload } from '../../api/dtos';

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
      job_type: 'pipeline',
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
        onRestart={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    expect(screen.getByText(/Latest progress/i)).toBeInTheDocument();
    expect(screen.getByText(/10 /)).toBeInTheDocument();
    expect(screen.getByText(/2.00 items/)).toBeInTheDocument();
  });

  it('hides job action buttons when the session cannot manage the job', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-unauthorized',
      job_type: 'pipeline',
      status: 'running',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: null,
      latest_event: null,
      error: null,
      tuning: null,
      result: null
    };

    render(
      <JobProgress
        jobId="job-unauthorized"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onRestart={vi.fn()}
        onReload={vi.fn()}
        canManage={false}
      />
    );

    expect(screen.queryByRole('button', { name: /pause/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });

  it('renders metadata when present and enables reload control', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-2',
      job_type: 'pipeline',
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
          book_author: 'Author Name',
          book_cover_file: 'runtime/example-cover.jpg'
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
        onRestart={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    fireEvent.click(screen.getByRole('tab', { name: /metadata/i }));

    expect(screen.getByText('Book metadata')).toBeInTheDocument();
    expect(screen.getByText('Example Title')).toBeInTheDocument();
    expect(screen.getByText('Author Name')).toBeInTheDocument();
    expect(screen.getByText('runtime/example-cover.jpg')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Cover of Example Title by Author Name' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload job/i })).toBeEnabled();
  });

  it('renders book creation summary metadata on the metadata tab', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-creation-summary',
      job_type: 'pipeline',
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
          book_title: 'Generated Book',
          creation_summary: {
            epub_path: 'runtime/generated/source.epub',
            messages: ['Created outline', 'Wrote chapters'],
            sentences_preview: ['The first sentence.', 'The second sentence.'],
            warnings: ['Short source text']
          }
        }
      }
    };

    render(
      <JobProgress
        jobId="job-creation-summary"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onRestart={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    fireEvent.click(screen.getByRole('tab', { name: /metadata/i }));

    expect(screen.getByText('Book creation summary')).toBeInTheDocument();
    expect(screen.getByText(/runtime\/generated\/source\.epub/)).toBeInTheDocument();
    expect(screen.getByText('Created outline')).toBeInTheDocument();
    expect(screen.getByText(/The first sentence\. The second sentence\./)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Short source text');
  });

  it('renders tuning metrics when provided', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-3',
      job_type: 'pipeline',
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
        onRestart={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    expect(screen.getByText('Parallelism overview')).toBeInTheDocument();
    expect(screen.getByText('LLM parallel calls')).toBeInTheDocument();
    expect(screen.getByText('TTS parallel calls')).toBeInTheDocument();
    expect(screen.getAllByText('4')).toHaveLength(2);
  });
});
