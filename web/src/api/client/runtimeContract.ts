/**
 * Shared Web API route contracts mirrored from the public backend runtime descriptor.
 */

export const WEB_AUTH_RUNTIME_CONTRACT = {
  loginPath: '/api/auth/login',
  oauthPath: '/api/auth/oauth',
  sessionPath: '/api/auth/session',
  logoutPath: '/api/auth/logout',
  passwordPath: '/api/auth/password',
  registerPath: '/api/auth/register',
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
  jobMediaChunkPathTemplate: '/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}',
  jobTimingPathTemplate: '/api/jobs/{job_id}/timing',
  subtitleTvMetadataPathTemplate: '/api/subtitles/jobs/{job_id}/metadata/tv',
  subtitleTvMetadataLookupPathTemplate: '/api/subtitles/jobs/{job_id}/metadata/tv/lookup',
  youtubeVideoMetadataPathTemplate: '/api/subtitles/jobs/{job_id}/metadata/youtube',
  youtubeVideoMetadataLookupPathTemplate: '/api/subtitles/jobs/{job_id}/metadata/youtube/lookup',
  subtitleJobResultPathTemplate: '/api/subtitles/jobs/{job_id}/result',
  libraryMediaPathTemplate: '/api/library/media/{job_id}',
  libraryMediaFilePathTemplate: '/api/library/media/{job_id}/file/{file_path}',
  sentenceImageInfoPathTemplate: '/api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}',
  sentenceImageBatchPathTemplate: '/api/pipelines/jobs/{job_id}/media/images/sentences/batch',
  sentenceImageRegeneratePathTemplate: '/api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}/regenerate',
  sentenceImageBatchQuery: 'sentence_numbers',
} as const;

export const WEB_PIPELINE_JOBS_RUNTIME_CONTRACT = {
  listPath: '/api/pipelines/jobs',
  statusPathTemplate: '/api/pipelines/{job_id}',
  eventStreamPathTemplate: '/api/pipelines/{job_id}/events',
  pausePathTemplate: '/api/pipelines/jobs/{job_id}/pause',
  resumePathTemplate: '/api/pipelines/jobs/{job_id}/resume',
  cancelPathTemplate: '/api/pipelines/jobs/{job_id}/cancel',
  deletePathTemplate: '/api/pipelines/jobs/{job_id}/delete',
  restartPathTemplate: '/api/pipelines/jobs/{job_id}/restart',
  accessPathTemplate: '/api/pipelines/{job_id}/access',
  metadataRefreshPathTemplate: '/api/pipelines/{job_id}/metadata/refresh',
  metadataEnrichPathTemplate: '/api/pipelines/{job_id}/metadata/enrich',
  bookMetadataPathTemplate: '/api/pipelines/{job_id}/metadata/book',
  bookMetadataLookupPathTemplate: '/api/pipelines/{job_id}/metadata/book/lookup',
  coverPathTemplate: '/api/pipelines/{job_id}/cover',
  cacheBusterQuery: 'ts',
} as const;

export const WEB_OFFLINE_EXPORT_RUNTIME_CONTRACT = {
  createPath: '/api/exports',
  downloadPathTemplate: '/api/exports/{export_id}/download',
  sourceKinds: ['job', 'library'],
  playerTypes: ['interactive-text'],
} as const;

export const WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT = {
  itemsPath: '/api/library/items',
  itemMetadataPathTemplate: '/api/library/items/{job_id}',
  accessPathTemplate: '/api/library/items/{job_id}/access',
  sourceUploadPathTemplate: '/api/library/items/{job_id}/upload-source',
  movePathTemplate: '/api/library/move/{job_id}',
  removePathTemplate: '/api/library/remove/{job_id}',
  removeMediaPathTemplate: '/api/library/remove-media/{job_id}',
  isbnLookupPath: '/api/library/isbn/lookup',
  isbnApplyPathTemplate: '/api/library/items/{job_id}/isbn',
  metadataRefreshPathTemplate: '/api/library/items/{job_id}/refresh',
  metadataEnrichPathTemplate: '/api/library/items/{job_id}/enrich',
  reindexPath: '/api/library/reindex',
} as const;

export const WEB_CREATE_RUNTIME_CONTRACT = {
  bookOptionsPath: '/api/books/options',
  bookJobsPath: '/api/books/jobs',
  pipelineJobsPath: '/api/pipelines',
  pipelineFilesPath: '/api/pipelines/files',
  pipelineFilesMinLimit: 1,
  pipelineFilesDefaultLimit: 200,
  pipelineFilesMaxLimit: 500,
  pipelineContentIndexPath: '/api/pipelines/files/content-index',
  pipelineUploadPath: '/api/pipelines/files/upload',
  pipelineCoverUploadPath: '/api/pipelines/covers/upload',
  pipelineIntakeStatusPath: '/api/pipelines/intake/status',
  pipelineDefaultsPath: '/api/pipelines/defaults',
  pipelineLlmModelsPath: '/api/pipelines/llm-models',
  pipelineSearchPath: '/api/pipelines/search',
  imageNodeAvailabilityPath: '/api/pipelines/image-nodes/availability',
  audioVoicesPath: '/api/audio/voices',
  subtitleSourcesPath: '/api/subtitles/sources',
  subtitleDeleteSourcePath: '/api/subtitles/delete-source',
  subtitleModelsPath: '/api/subtitles/models',
  subtitleTvMetadataPreviewPath: '/api/subtitles/metadata/tv/lookup',
  subtitleTvMetadataCacheClearPath: '/api/subtitles/metadata/tv/cache/clear',
  youtubeMetadataPreviewPath: '/api/subtitles/metadata/youtube/lookup',
  youtubeMetadataCacheClearPath: '/api/subtitles/metadata/youtube/cache/clear',
  bookMetadataPreviewPath: '/api/pipelines/metadata/book/lookup',
  bookMetadataCacheClearPath: '/api/pipelines/metadata/book/cache/clear',
  youtubeLibraryPath: '/api/subtitles/youtube/library',
  youtubeSubtitlesPath: '/api/subtitles/youtube/subtitles',
  youtubeSubtitleDownloadPath: '/api/subtitles/youtube/download',
  youtubeVideoDownloadPath: '/api/subtitles/youtube/video',
  youtubeSubtitleStreamsPath: '/api/subtitles/youtube/subtitle-streams',
  youtubeExtractSubtitlesPath: '/api/subtitles/youtube/extract-subtitles',
  youtubeSubtitleDeletePath: '/api/subtitles/youtube/delete-subtitle',
  youtubeVideoDeletePath: '/api/subtitles/youtube/delete-video',
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
  lookupCachePathTemplate: '/api/pipelines/jobs/{job_id}/lookup-cache',
  lookupCacheWordPathTemplate: '/api/pipelines/jobs/{job_id}/lookup-cache/{word}',
  lookupCacheBulkPathTemplate: '/api/pipelines/jobs/{job_id}/lookup-cache/bulk',
  lookupCacheSummaryPathTemplate: '/api/pipelines/jobs/{job_id}/lookup-cache/summary',
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
