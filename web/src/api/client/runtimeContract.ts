/**
 * Shared Web API route contracts mirrored from the public backend runtime descriptor.
 */

export const WEB_AUTH_RUNTIME_CONTRACT = {
  loginPath: '/api/auth/login',
  oauthPath: '/api/auth/oauth',
  sessionPath: '/api/auth/session',
} as const;

export const WEB_PLAYBACK_STATE_RUNTIME_CONTRACT = {
  bookmarksPathTemplate: '/api/bookmarks/{job_id}',
  bookmarkDeletePathTemplate: '/api/bookmarks/{job_id}/{bookmark_id}',
  resumeListPath: '/api/resume',
  resumePathTemplate: '/api/resume/{job_id}',
  resumeFilterQuery: 'job_id',
} as const;

export const WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT = {
  jobMediaPathTemplate: '/api/pipelines/jobs/{job_id}/media',
  jobMediaLivePathTemplate: '/api/pipelines/jobs/{job_id}/media/live',
  libraryMediaPathTemplate: '/api/library/media/{job_id}',
  libraryMediaFilePathTemplate: '/api/library/media/{job_id}/file/{file_path}',
} as const;

export const WEB_OFFLINE_EXPORT_RUNTIME_CONTRACT = {
  createPath: '/api/exports',
} as const;

export const WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT = {
  itemsPath: '/api/library/items',
  itemMetadataPathTemplate: '/api/library/items/{job_id}',
  sourceUploadPathTemplate: '/api/library/items/{job_id}/upload-source',
  movePathTemplate: '/api/library/move/{job_id}',
  removePathTemplate: '/api/library/remove/{job_id}',
  isbnLookupPath: '/api/library/isbn/lookup',
  isbnApplyPathTemplate: '/api/library/items/{job_id}/isbn',
  metadataEnrichPathTemplate: '/api/library/items/{job_id}/enrich',
} as const;

export const WEB_CREATE_RUNTIME_CONTRACT = {
  bookOptionsPath: '/api/books/options',
  bookJobsPath: '/api/books/jobs',
  pipelineFilesPath: '/api/pipelines/files',
  pipelineContentIndexPath: '/api/pipelines/files/content-index',
  pipelineUploadPath: '/api/pipelines/files/upload',
  pipelineIntakeStatusPath: '/api/pipelines/intake/status',
  pipelineDefaultsPath: '/api/pipelines/defaults',
  pipelineLlmModelsPath: '/api/pipelines/llm-models',
  pipelineSearchPath: '/api/pipelines/search',
  imageNodeAvailabilityPath: '/api/pipelines/image-nodes/availability',
  audioVoicesPath: '/api/audio/voices',
  subtitleSourcesPath: '/api/subtitles/sources',
  subtitleDeleteSourcePath: '/api/subtitles/delete-source',
  subtitleTvMetadataPreviewPath: '/api/subtitles/metadata/tv/lookup',
  youtubeMetadataPreviewPath: '/api/subtitles/metadata/youtube/lookup',
  youtubeLibraryPath: '/api/subtitles/youtube/library',
  youtubeSubtitleStreamsPath: '/api/subtitles/youtube/subtitle-streams',
  youtubeExtractSubtitlesPath: '/api/subtitles/youtube/extract-subtitles',
  youtubeDubPath: '/api/subtitles/youtube/dub',
  subtitleJobsPath: '/api/subtitles/jobs',
  acquisitionProvidersPath: '/api/acquisition/providers',
  acquisitionDiscoverPath: '/api/acquisition/discover',
  acquisitionAcquirePath: '/api/acquisition/acquire',
  acquisitionArtifactPreparePathTemplate: '/api/acquisition/artifacts/{artifact_id}/prepare',
  acquisitionJobsPath: '/api/acquisition/jobs',
  acquisitionJobPathTemplate: '/api/acquisition/jobs/{task_id}',
  templateListPath: '/api/creation/templates',
  templatePathTemplate: '/api/creation/templates/{template_id}',
} as const;

export const WEB_LINGUIST_RUNTIME_CONTRACT = {
  assistantLookupPath: '/api/assistant/lookup',
  audioSynthesisPath: '/api/audio',
} as const;

export function replaceRuntimePathParameter(
  template: string,
  name: string,
  value: string
): string {
  return template.replace(`{${name}}`, encodeURIComponent(value));
}

export function replaceRuntimePathParameters(
  template: string,
  values: Record<string, string>
): string {
  return Object.entries(values).reduce(
    (path, [name, value]) => replaceRuntimePathParameter(path, name, value),
    template
  );
}
