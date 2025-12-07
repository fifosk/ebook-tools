import { getAuthContext, withBase } from './client';
import type { PipelineRequestPayload, PipelineSubmissionResponse } from './dtos';

export interface CreateBookPayload {
  input_language: string;
  output_language: string;
  voice?: string | null;
  num_sentences: number;
  topic: string;
  book_name: string;
  genre: string;
  author?: string;
}

export interface BookCreationResponse {
  job_id?: string | null;
  status: string;
  metadata: Record<string, unknown>;
  messages: string[];
  warnings: string[];
  epub_path: string | null;
  input_file?: string | null;
  sentences_preview: string[];
}

export async function createBook(payload: CreateBookPayload): Promise<BookCreationResponse> {
  const { token, userId, userRole } = getAuthContext();
  const headers = new Headers({
    'Content-Type': 'application/json'
  });
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (userId) {
    headers.set('X-User-Id', userId);
  }
  if (userRole) {
    headers.set('X-User-Role', userRole);
  }

  const response = await fetch(withBase('/api/books/create'), {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to create book');
  }

  return (await response.json()) as BookCreationResponse;
}

export interface BookGenerationJobRequest {
  generator: {
    topic: string;
    book_name: string;
    genre: string;
    author?: string;
    num_sentences: number;
    input_language?: string | null;
    output_language?: string | null;
    voice?: string | null;
  };
  pipeline: PipelineRequestPayload;
}

export async function submitBookJob(
  payload: BookGenerationJobRequest
): Promise<PipelineSubmissionResponse> {
  const { token, userId, userRole } = getAuthContext();
  const headers = new Headers({
    'Content-Type': 'application/json'
  });
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (userId) {
    headers.set('X-User-Id', userId);
  }
  if (userRole) {
    headers.set('X-User-Role', userRole);
  }

  const response = await fetch(withBase('/api/books/jobs'), {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to submit book generation job');
  }

  return (await response.json()) as PipelineSubmissionResponse;
}
