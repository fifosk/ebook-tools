/**
 * API Client - Modular exports
 *
 * This module re-exports all API functions from their domain-specific modules.
 * Import from here to get all API functions, or import directly from specific
 * modules for tree-shaking benefits.
 */

// Base utilities
export {
  API_BASE_URL,
  STORAGE_BASE_URL,
  resolveApiBaseUrl,
  withBase,
  setAuthToken,
  getAuthToken,
  setAuthContext,
  getAuthContext,
  setUnauthorizedHandler,
  apiFetch,
  handleResponse,
  appendAccessToken,
  appendAccessTokenToStorageUrl,
  maybeAppendAccessTokenToStorage,
  normaliseApiUrl,
  type FetchOptions
} from './base';

// Authentication
export {
  login,
  loginWithOAuth,
  logout,
  fetchSessionStatus,
  changePassword
} from './auth';

// Jobs and pipelines
export {
  submitPipeline,
  fetchPipelineStatus,
  fetchJobs,
  pauseJob,
  resumeJob,
  cancelJob,
  deleteJob,
  restartJob,
  refreshPipelineMetadata,
  updateJobAccess,
  fetchJobTiming,
  fetchPipelineFiles,
  fetchPipelineDefaults,
  fetchBookContentIndex,
  checkImageNodeAvailability,
  uploadEpubFile,
  uploadCoverFile,
  deletePipelineEbook,
  fetchBookOpenLibraryMetadata,
  lookupBookOpenLibraryMetadata,
  lookupBookOpenLibraryMetadataPreview,
  fetchLlmModels,
  buildEventStreamUrl,
  resolveJobCoverUrl
} from './jobs';

// Admin and user management
export {
  listUsers,
  createUser,
  updateUserProfile,
  deleteUserAccount,
  suspendUserAccount,
  activateUserAccount,
  resetUserPassword,
  fetchReadingBeds,
  uploadReadingBed,
  updateReadingBed,
  deleteReadingBed
} from './admin';

// Media, images, video, audio
export {
  fetchJobMedia,
  fetchLiveJobMedia,
  fetchSentenceImageInfo,
  fetchSentenceImageInfoBatch,
  regenerateSentenceImage,
  generateVideo,
  fetchVideoStatus,
  fetchVoiceInventory,
  synthesizeVoicePreview,
  fetchPlaybackBookmarks,
  createPlaybackBookmark,
  deletePlaybackBookmark,
  createExport,
  searchMedia,
  buildStorageUrl,
  resolveSubtitleDownloadUrl,
  type VoicePreviewRequest
} from './media';

// Library
export {
  moveJobToLibrary,
  searchLibrary,
  removeLibraryMedia,
  removeLibraryEntry,
  reindexLibrary,
  refreshLibraryMetadata,
  updateLibraryMetadata,
  updateLibraryAccess,
  uploadLibrarySource,
  applyLibraryIsbn,
  lookupLibraryIsbnMetadata,
  resolveLibraryMediaUrl,
  fetchLibraryMedia,
  type LibrarySearchParams
} from './library';

// Subtitles and YouTube
export {
  fetchSubtitleSources,
  deleteSubtitleSource,
  fetchSubtitleTvMetadata,
  lookupSubtitleTvMetadata,
  lookupSubtitleTvMetadataPreview,
  fetchYoutubeVideoMetadata,
  lookupYoutubeVideoMetadata,
  lookupYoutubeVideoMetadataPreview,
  fetchYoutubeSubtitleTracks,
  downloadYoutubeSubtitle,
  downloadYoutubeVideo,
  fetchYoutubeLibrary,
  fetchInlineSubtitleStreams,
  extractInlineSubtitles,
  deleteNasSubtitle,
  deleteYoutubeVideo,
  generateYoutubeDub,
  submitSubtitleJob,
  fetchSubtitleResult,
  fetchSubtitleModels,
  assistantLookup
} from './subtitles';

// Configuration management
export {
  fetchGroupedConfig,
  fetchConfigGroup,
  updateConfigGroup,
  validateConfig,
  listSnapshots,
  createSnapshot,
  restoreSnapshot,
  deleteSnapshot,
  exportSnapshot,
  importConfig,
  fetchAuditLog,
  fetchSystemStatus,
  fetchHealthCheck,
  reloadConfig,
  requestRestart,
  cancelRestart,
  fetchRestartStatus,
  listSecrets,
  setSecret,
  deleteSecret,
  type ConfigKeyMetadata,
  type ConfigGroupMetadata,
  type ConfigGroup,
  type GroupedConfigResponse,
  type ConfigGroupUpdatePayload,
  type ConfigGroupUpdateResponse,
  type SnapshotMetadata,
  type SnapshotListResponse,
  type CreateSnapshotPayload,
  type CreateSnapshotResponse,
  type RestoreSnapshotResponse,
  type ExportSnapshotResponse,
  type ImportConfigResponse,
  type AuditLogEntry,
  type AuditLogResponse,
  type AuditLogQueryParams,
  type ValidationError,
  type ConfigValidationResponse,
  type SystemStatusResponse,
  type ReloadConfigResponse,
  type RestartRequestPayload,
  type RestartResponse,
  type HealthCheckResponse,
  type SecretKeyInfo,
  type SecretListResponse,
  type SetSecretPayload,
  type SetSecretResponse
} from './config';
