/**
 * Configuration management API endpoints.
 */

import { apiFetch, handleResponse } from './base';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface ConfigKeyMetadata {
  key: string;
  displayName: string;
  description?: string;
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object' | 'secret';
  defaultValue?: unknown;
  currentValue?: unknown;
  isSensitive: boolean;
  isEnvOverride: boolean;
  requiresRestart: boolean;
  validationRules?: Record<string, unknown>;
}

export interface ConfigGroupMetadata {
  name: string;
  displayName: string;
  description: string;
  icon?: string;
  keyCount: number;
  hasSensitive: boolean;
}

export interface ConfigGroup {
  group: string;
  metadata: ConfigGroupMetadata;
  keys: ConfigKeyMetadata[];
}

export interface GroupedConfigResponse {
  groups: ConfigGroup[];
  effectiveSources: Record<string, string>;
  lastModified?: string;
  activeSnapshotId?: string;
}

export interface ConfigGroupUpdatePayload {
  values: Record<string, unknown>;
  createBackup?: boolean;
}

export interface ConfigGroupUpdateResponse {
  group: string;
  updatedKeys: string[];
  requiresRestart: boolean;
  backupSnapshotId?: string;
}

export interface SnapshotMetadata {
  snapshotId: string;
  label?: string;
  description?: string;
  createdBy?: string;
  createdAt: string;
  isActive: boolean;
  source: string;
  configHash: string;
}

export interface SnapshotListResponse {
  snapshots: SnapshotMetadata[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateSnapshotPayload {
  label?: string;
  description?: string;
  activate?: boolean;
}

export interface CreateSnapshotResponse {
  snapshotId: string;
  label?: string;
  createdAt: string;
  isActive: boolean;
}

export interface RestoreSnapshotResponse {
  snapshotId: string;
  label?: string;
  restoredAt: string;
  requiresRestart: boolean;
  restartKeys: string[];
}

export interface ExportSnapshotResponse {
  snapshotId: string;
  label?: string;
  description?: string;
  createdAt: string;
  createdBy?: string;
  source: string;
  config: Record<string, unknown>;
}

export interface ImportConfigResponse {
  snapshotId: string;
  label?: string;
  keyCount: number;
  isActive: boolean;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  username?: string;
  action: string;
  snapshotId?: string;
  groupName?: string;
  keyName?: string;
  oldValue?: string;
  newValue?: string;
  ipAddress?: string;
  metadata?: Record<string, unknown>;
  success: boolean;
  errorMessage?: string;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditLogQueryParams {
  limit?: number;
  offset?: number;
  username?: string;
  action?: string;
  since?: string;
  groupName?: string;
}

export interface ValidationError {
  key: string;
  message: string;
  errorType: 'error' | 'warning';
}

export interface ConfigValidationResponse {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface SystemStatusResponse {
  uptimeSeconds: number;
  configLoadedAt?: string;
  activeSnapshotId?: string;
  dbEnabled: boolean;
  configDbPath?: string;
  libraryDbPath?: string;
  pendingChanges: boolean;
  restartRequired: boolean;
  restartKeys: string[];
}

export interface ReloadConfigResponse {
  success: boolean;
  reloadedAt: string;
  changedKeys: string[];
  error?: string;
}

export interface RestartRequestPayload {
  reason?: string;
  delaySeconds?: number;
  force?: boolean;
}

export interface RestartResponse {
  scheduled: boolean;
  restartAt: string;
  delaySeconds: number;
  preRestartSnapshotId?: string;
  runningJobs: number;
}

export interface HealthCheckResponse {
  status: 'ok' | 'degraded' | 'unhealthy';
  configLoaded: boolean;
  dbAvailable: boolean;
  tmpWorkspace?: string;
  isRamdisk: boolean;
  uptimeSeconds: number;
  checks: Record<string, boolean>;
}

export interface SecretKeyInfo {
  keyPath: string;
  updatedAt?: string;
  updatedBy?: string;
}

export interface SecretListResponse {
  secrets: SecretKeyInfo[];
  encryptionAvailable: boolean;
}

export interface SetSecretPayload {
  keyPath: string;
  value: string;
}

export interface SetSecretResponse {
  keyPath: string;
  success: boolean;
  error?: string;
}

// -----------------------------------------------------------------------------
// Configuration Endpoints
// -----------------------------------------------------------------------------

export async function fetchGroupedConfig(
  options?: { showSecrets?: boolean; signal?: AbortSignal }
): Promise<GroupedConfigResponse> {
  const params = new URLSearchParams();
  if (options?.showSecrets) params.set('show_secrets', 'true');
  const queryString = params.toString();
  const url = queryString ? `/api/admin/config?${queryString}` : '/api/admin/config';
  const response = await apiFetch(url, { signal: options?.signal });
  return handleResponse<GroupedConfigResponse>(response);
}

export async function fetchConfigGroup(
  groupName: string,
  options?: { showSecrets?: boolean; signal?: AbortSignal }
): Promise<ConfigGroup> {
  const params = new URLSearchParams();
  if (options?.showSecrets) params.set('show_secrets', 'true');
  const queryString = params.toString();
  const url = queryString
    ? `/api/admin/config/groups/${encodeURIComponent(groupName)}?${queryString}`
    : `/api/admin/config/groups/${encodeURIComponent(groupName)}`;
  const response = await apiFetch(url, { signal: options?.signal });
  return handleResponse<ConfigGroup>(response);
}

export async function updateConfigGroup(
  groupName: string,
  payload: ConfigGroupUpdatePayload
): Promise<ConfigGroupUpdateResponse> {
  const response = await apiFetch(`/api/admin/config/groups/${encodeURIComponent(groupName)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<ConfigGroupUpdateResponse>(response);
}

export async function validateConfig(
  values: Record<string, unknown>,
  group?: string
): Promise<ConfigValidationResponse> {
  const response = await apiFetch('/api/admin/config/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ values, group })
  });
  return handleResponse<ConfigValidationResponse>(response);
}

// -----------------------------------------------------------------------------
// Snapshot Endpoints
// -----------------------------------------------------------------------------

export async function listSnapshots(
  limit = 50,
  offset = 0,
  signal?: AbortSignal
): Promise<SnapshotListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const response = await apiFetch(`/api/admin/config/snapshots?${params}`, { signal });
  return handleResponse<SnapshotListResponse>(response);
}

export async function createSnapshot(payload: CreateSnapshotPayload): Promise<CreateSnapshotResponse> {
  const response = await apiFetch('/api/admin/config/snapshots', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<CreateSnapshotResponse>(response);
}

export async function restoreSnapshot(snapshotId: string): Promise<RestoreSnapshotResponse> {
  const response = await apiFetch(`/api/admin/config/snapshots/${encodeURIComponent(snapshotId)}/restore`, {
    method: 'POST'
  });
  return handleResponse<RestoreSnapshotResponse>(response);
}

export async function deleteSnapshot(snapshotId: string): Promise<void> {
  const response = await apiFetch(`/api/admin/config/snapshots/${encodeURIComponent(snapshotId)}`, {
    method: 'DELETE'
  });
  await handleResponse<unknown>(response);
}

export async function exportSnapshot(
  snapshotId: string,
  maskSensitive = true
): Promise<ExportSnapshotResponse> {
  const params = new URLSearchParams({ mask_sensitive: String(maskSensitive) });
  const response = await apiFetch(
    `/api/admin/config/snapshots/${encodeURIComponent(snapshotId)}/export?${params}`
  );
  return handleResponse<ExportSnapshotResponse>(response);
}

export async function importConfig(
  file: File,
  label?: string,
  activate = false
): Promise<ImportConfigResponse> {
  const form = new FormData();
  form.append('file', file);

  const params = new URLSearchParams();
  if (label) params.set('label', label);
  if (activate) params.set('activate', 'true');

  const queryString = params.toString();
  const url = queryString ? `/api/admin/config/import?${queryString}` : '/api/admin/config/import';

  const response = await apiFetch(url, {
    method: 'POST',
    body: form
  });
  return handleResponse<ImportConfigResponse>(response);
}

// -----------------------------------------------------------------------------
// Audit Log Endpoints
// -----------------------------------------------------------------------------

export async function fetchAuditLog(
  params: AuditLogQueryParams = {},
  signal?: AbortSignal
): Promise<AuditLogResponse> {
  const searchParams = new URLSearchParams();
  if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params.offset !== undefined) searchParams.set('offset', String(params.offset));
  if (params.username) searchParams.set('username', params.username);
  if (params.action) searchParams.set('action', params.action);
  if (params.since) searchParams.set('since', params.since);
  if (params.groupName) searchParams.set('group_name', params.groupName);

  const response = await apiFetch(`/api/admin/config/audit?${searchParams}`, { signal });
  return handleResponse<AuditLogResponse>(response);
}

// -----------------------------------------------------------------------------
// System Control Endpoints
// -----------------------------------------------------------------------------

export async function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatusResponse> {
  const response = await apiFetch('/api/admin/system/status', { signal });
  return handleResponse<SystemStatusResponse>(response);
}

export async function fetchHealthCheck(signal?: AbortSignal): Promise<HealthCheckResponse> {
  const response = await apiFetch('/api/admin/system/health', { signal });
  return handleResponse<HealthCheckResponse>(response);
}

export async function reloadConfig(): Promise<ReloadConfigResponse> {
  const response = await apiFetch('/api/admin/system/reload-config', {
    method: 'POST'
  });
  return handleResponse<ReloadConfigResponse>(response);
}

export async function requestRestart(payload: RestartRequestPayload = {}): Promise<RestartResponse> {
  const response = await apiFetch('/api/admin/system/restart', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<RestartResponse>(response);
}

export async function cancelRestart(): Promise<{ cancelled: boolean; message: string }> {
  const response = await apiFetch('/api/admin/system/restart/cancel', {
    method: 'POST'
  });
  return handleResponse<{ cancelled: boolean; message: string }>(response);
}

export async function fetchRestartStatus(): Promise<{
  restartScheduled: boolean;
  restartAt?: string;
  pendingRestartKeys: string[];
}> {
  const response = await apiFetch('/api/admin/system/restart/status');
  return handleResponse(response);
}

// -----------------------------------------------------------------------------
// Secrets Management Endpoints
// -----------------------------------------------------------------------------

export async function listSecrets(signal?: AbortSignal): Promise<SecretListResponse> {
  const response = await apiFetch('/api/admin/config/secrets', { signal });
  return handleResponse<SecretListResponse>(response);
}

export async function setSecret(payload: SetSecretPayload): Promise<SetSecretResponse> {
  const response = await apiFetch('/api/admin/config/secrets', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<SetSecretResponse>(response);
}

export async function deleteSecret(keyPath: string): Promise<void> {
  const response = await apiFetch(`/api/admin/config/secrets/${encodeURIComponent(keyPath)}`, {
    method: 'DELETE'
  });
  await handleResponse<unknown>(response);
}
