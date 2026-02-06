/**
 * Resume position API endpoints.
 */

import type {
  ResumePositionDeleteResponse,
  ResumePositionPayload,
  ResumePositionResponse,
} from '../dtos';
import { apiFetch, handleResponse } from './base';

export async function fetchResumePosition(jobId: string): Promise<ResumePositionResponse> {
  const response = await apiFetch(`/api/resume/${encodeURIComponent(jobId)}`);
  return handleResponse<ResumePositionResponse>(response);
}

export async function saveResumePosition(
  jobId: string,
  payload: ResumePositionPayload,
): Promise<ResumePositionResponse> {
  const response = await apiFetch(`/api/resume/${encodeURIComponent(jobId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<ResumePositionResponse>(response);
}

export async function clearResumePosition(jobId: string): Promise<ResumePositionDeleteResponse> {
  const response = await apiFetch(`/api/resume/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
  return handleResponse<ResumePositionDeleteResponse>(response);
}
