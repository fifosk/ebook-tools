import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

const buildStorageUrlMock = vi.hoisted(() =>
  vi.fn<[string], string>((path) => `https://storage.example/${path}`)
);

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client');
  return {
    ...actual,
    buildStorageUrl: buildStorageUrlMock
  };
});

import { fireEvent, render, screen } from '@testing-library/react';
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
  beforeEach(() => {
    buildStorageUrlMock.mockReset();
    buildStorageUrlMock.mockImplementation((path) => `https://storage.example/${path}`);
  });

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
        onReload={vi.fn()}
        canManage={true}
      />
    );

    expect(screen.getByText('Example Title')).toBeInTheDocument();
    const image = screen.getByAltText('Cover of Example Title by Author Name') as HTMLImageElement;
    expect(image).toBeInTheDocument();
    expect(image.src).toBe('https://storage.example/runtime/example-cover.jpg');
    expect(buildStorageUrlMock).toHaveBeenCalledWith('runtime/example-cover.jpg');
    expect(screen.getByRole('button', { name: /reload metadata/i })).toBeEnabled();
  });

  it('normalises storage-rooted cover metadata to avoid double storage prefixes', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-2a',
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
          book_title: 'Storage Rooted Title',
          book_author: 'Storage Rooted Author',
          book_cover_file: 'storage/runtime/storage-rooted-cover.jpg'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-2a"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    const image = screen.getByAltText(
      'Cover of Storage Rooted Title by Storage Rooted Author'
    ) as HTMLImageElement;
    expect(image.src).toBe('https://storage.example/runtime/storage-rooted-cover.jpg');
    expect(buildStorageUrlMock).toHaveBeenCalledWith('runtime/storage-rooted-cover.jpg');
    expect(screen.getByText('storage/runtime/storage-rooted-cover.jpg')).toBeInTheDocument();
  });

  it('resolves shared cover storage paths', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-2b',
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
          book_title: 'Shared Cover Title',
          book_author: 'Shared Cover Author',
          book_cover_file: '/Users/me/ebook-tools/storage/covers/shared-cover.jpg'
        }
      }
    };

    render(
      <JobProgress
        jobId='job-2b'
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    const image = screen.getByAltText('Cover of Shared Cover Title by Shared Cover Author') as HTMLImageElement;
    expect(image.src.endsWith('/storage/covers/shared-cover.jpg')).toBe(true);
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
        canManage={true}
      />
    );

    expect(screen.getByText('Performance tuning')).toBeInTheDocument();
    expect(screen.getByText('Translation threads')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Translation queue size')).toBeInTheDocument();
    expect(screen.getByText('32')).toBeInTheDocument();
  });

  it('falls back to placeholder text when the cover fails to load', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-4',
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
          book_title: 'Broken Cover',
          book_author: 'Author Name',
          book_cover_file: 'runtime/broken-cover.jpg'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-4"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    let image = screen.getByAltText('Cover of Broken Cover by Author Name') as HTMLImageElement;
    expect(image.src).toBe('https://storage.example/runtime/broken-cover.jpg');

    fireEvent.error(image);
    image = screen.getByAltText('Cover of Broken Cover by Author Name') as HTMLImageElement;
    expect(image.src.endsWith('/storage/runtime/broken-cover.jpg')).toBe(true);

    fireEvent.error(image);
    image = screen.getByAltText('Cover of Broken Cover by Author Name') as HTMLImageElement;
    expect(image.src.endsWith('/runtime/broken-cover.jpg')).toBe(true);

    fireEvent.error(image);

    expect(screen.getByText(/Cover preview could not be loaded/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry preview/i })).toBeInTheDocument();
    expect(screen.queryByAltText('Cover of Broken Cover by Author Name')).not.toBeInTheDocument();
  });

  it('allows retrying the cover preview after a failure', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-4',
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
          book_title: 'Broken Cover',
          book_author: 'Author Name',
          book_cover_file: 'runtime/broken-cover.jpg'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-4"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    let image = screen.getByAltText('Cover of Broken Cover by Author Name');
    fireEvent.error(image);
    image = screen.getByAltText('Cover of Broken Cover by Author Name');
    fireEvent.error(image);
    image = screen.getByAltText('Cover of Broken Cover by Author Name');
    fireEvent.error(image);

    expect(screen.getByText(/Cover preview could not be loaded/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /retry preview/i }));

    expect(screen.getByAltText('Cover of Broken Cover by Author Name')).toBeInTheDocument();
  });

  it('retries the cover preview when metadata refreshes without changing the path', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-6',
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
          book_title: 'Broken Cover',
          book_author: 'Author Name',
          book_cover_file: 'runtime/broken-cover.jpg'
        }
      }
    };

    const { rerender } = render(
      <JobProgress
        jobId="job-6"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    let image = screen.getByAltText('Cover of Broken Cover by Author Name');
    fireEvent.error(image);
    image = screen.getByAltText('Cover of Broken Cover by Author Name');
    fireEvent.error(image);
    image = screen.getByAltText('Cover of Broken Cover by Author Name');
    fireEvent.error(image);

    expect(screen.getByText(/Cover preview could not be loaded/i)).toBeInTheDocument();

    const refreshedStatus: PipelineStatusResponse = {
      ...status,
      result: {
        ...status.result!,
        book_metadata: {
          ...status.result!.book_metadata,
          book_summary: 'An updated summary after metadata refresh.'
        }
      }
    };

    rerender(
      <JobProgress
        jobId="job-6"
        status={refreshedStatus}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    expect(screen.queryByText(/Cover preview could not be loaded/i)).not.toBeInTheDocument();
    expect(screen.getByAltText('Cover of Broken Cover by Author Name')).toBeInTheDocument();

    image = screen.getByAltText('Cover of Broken Cover by Author Name');
    expect(image.src).toBe('https://storage.example/runtime/broken-cover.jpg');
  });

  it('normalises cover metadata rooted in the output directory to storage paths', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-7',
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
          book_title: 'Output Rooted Cover',
          book_author: 'Author Name',
          book_cover_file: '/Users/me/modules/output/runtime/output-cover.jpg'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-7"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    const image = screen.getByAltText('Cover of Output Rooted Cover by Author Name') as HTMLImageElement;
    expect(image.src).toBe('https://storage.example/runtime/output-cover.jpg');
    expect(buildStorageUrlMock).toHaveBeenCalledWith('runtime/output-cover.jpg');
    expect(screen.getByText('storage/runtime/output-cover.jpg')).toBeInTheDocument();
  });

  it('tries a relative storage path when building a storage URL fails', () => {
    buildStorageUrlMock.mockImplementation(() => {
      throw new Error('Missing storage base URL');
    });

    const status: PipelineStatusResponse = {
      job_id: 'job-7',
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
          book_cover_file: '/storage/runtime/example-cover.jpg'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-7"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    const image = screen.getByAltText('Cover of Example Title by Author Name') as HTMLImageElement;
    expect(image.src.endsWith('/storage/runtime/example-cover.jpg')).toBe(true);
    expect(buildStorageUrlMock).toHaveBeenCalledWith('runtime/example-cover.jpg');
  });

  it('shows a fallback cover when no cover metadata is available', () => {
    const status: PipelineStatusResponse = {
      job_id: 'job-5',
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
          book_title: 'No Cover Title',
          book_author: 'No Cover Author'
        }
      }
    };

    render(
      <JobProgress
        jobId="job-5"
        status={status}
        latestEvent={undefined}
        onEvent={vi.fn()}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onReload={vi.fn()}
        canManage={true}
      />
    );

    const image = screen.getByAltText('Cover of No Cover Title by No Cover Author') as HTMLImageElement;
    expect(image).toBeInTheDocument();
    expect(image.src).toContain('/assets/default-cover.png');
  });
});
