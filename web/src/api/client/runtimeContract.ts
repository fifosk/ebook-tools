/**
 * Shared Web API route contracts mirrored from the public backend runtime descriptor.
 */

export const WEB_AUTH_RUNTIME_CONTRACT = {
  loginPath: '/api/auth/login',
  oauthPath: '/api/auth/oauth',
  sessionPath: '/api/auth/session',
} as const;

export const WEB_PLAYBACK_STATE_RUNTIME_CONTRACT = {
  resumeListPath: '/api/resume',
  resumePathTemplate: '/api/resume/{job_id}',
  resumeFilterQuery: 'job_id',
} as const;

export function replaceRuntimePathParameter(
  template: string,
  name: string,
  value: string
): string {
  return template.replace(`{${name}}`, encodeURIComponent(value));
}
