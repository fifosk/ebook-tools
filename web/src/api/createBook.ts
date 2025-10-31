import { getAuthToken } from './client';

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
  job_id: string;
  status: string;
  metadata: Record<string, unknown>;
  messages: string[];
  warnings: string[];
  epub_path: string | null;
  sentences_preview: string[];
}

export async function createBook(payload: CreateBookPayload): Promise<BookCreationResponse> {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch('/api/books/create', {
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
