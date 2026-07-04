import type { PipelineStatusResponse } from '../../api/dtos';
import { IMAGE_API_NODE_OPTIONS } from '../../constants/imageNodes';

export type ImageClusterNodeSummary = {
  baseUrl: string;
  active: boolean;
  processed: number | null;
  avgSecondsPerImage: number | null;
};

function coerceImageRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function coerceImageNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function resolveImageClusterSummary(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown> | null {
  if (!status) {
    return null;
  }
  const resultGenerated =
    status.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)['generated_files']
      : undefined;
  const candidates = [status.generated_files, resultGenerated];
  for (const candidate of candidates) {
    const record = coerceImageRecord(candidate);
    if (!record) {
      continue;
    }
    const summary = coerceImageRecord(record['image_cluster']);
    if (summary) {
      return summary;
    }
  }
  return null;
}

export function normalizeBaseUrl(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, '');
}

export function resolveImageClusterBaseUrls(
  config: Record<string, unknown> | null,
): string[] {
  if (!config) {
    return [];
  }
  const urlsRaw = config['image_api_base_urls'];
  const baseUrls: string[] = [];
  if (Array.isArray(urlsRaw)) {
    for (const entry of urlsRaw) {
      const normalized = normalizeBaseUrl(entry);
      if (normalized) {
        baseUrls.push(normalized);
      }
    }
  } else if (typeof urlsRaw === 'string') {
    const normalized = normalizeBaseUrl(urlsRaw);
    if (normalized) {
      baseUrls.push(normalized);
    }
  }

  const fallback = normalizeBaseUrl(config['image_api_base_url']);
  if (fallback) {
    baseUrls.push(fallback);
  }

  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const entry of baseUrls) {
    if (seen.has(entry)) {
      continue;
    }
    seen.add(entry);
    deduped.push(entry);
  }
  return deduped;
}

export function buildImageClusterNodes(
  summary: Record<string, unknown> | null,
  config: Record<string, unknown> | null,
  enabled: boolean,
): ImageClusterNodeSummary[] {
  const nodes: ImageClusterNodeSummary[] = [];
  const summaryRecord = summary ? coerceImageRecord(summary) : null;
  const rawNodes = summaryRecord && Array.isArray(summaryRecord['nodes']) ? summaryRecord['nodes'] : [];
  const statsByUrl = new Map<string, Record<string, unknown>>();
  if (Array.isArray(rawNodes)) {
    for (const entry of rawNodes) {
      if (!entry || typeof entry !== 'object') {
        continue;
      }
      const record = entry as Record<string, unknown>;
      const url = normalizeBaseUrl(record['base_url'] ?? record['baseUrl']);
      if (!url) {
        continue;
      }
      statsByUrl.set(url, record);
    }
  }

  const configuredUrls = resolveImageClusterBaseUrls(config);
  if (!enabled && statsByUrl.size === 0) {
    return nodes;
  }
  if (statsByUrl.size === 0 && configuredUrls.length === 0) {
    return nodes;
  }

  const configuredSet = new Set(configuredUrls);
  const knownUrls = new Set<string>();
  for (const option of IMAGE_API_NODE_OPTIONS) {
    const url = normalizeBaseUrl(option.value);
    if (!url) {
      continue;
    }
    knownUrls.add(url);
    const stats = statsByUrl.get(url) ?? {};
    const activeOverride = typeof stats['active'] === 'boolean' ? (stats['active'] as boolean) : null;
    const processed = coerceImageNumber(stats['processed']);
    const avgSeconds = coerceImageNumber(stats['avg_seconds_per_image'] ?? stats['avgSecondsPerImage']);
    nodes.push({
      baseUrl: url,
      active: activeOverride ?? configuredSet.has(url),
      processed: processed ?? 0,
      avgSecondsPerImage: avgSeconds,
    });
  }

  for (const [url, stats] of statsByUrl.entries()) {
    if (knownUrls.has(url)) {
      continue;
    }
    const activeOverride = typeof stats['active'] === 'boolean' ? (stats['active'] as boolean) : null;
    const processed = coerceImageNumber(stats['processed']);
    const avgSeconds = coerceImageNumber(stats['avg_seconds_per_image'] ?? stats['avgSecondsPerImage']);
    nodes.push({
      baseUrl: url,
      active: activeOverride ?? configuredSet.has(url),
      processed: processed ?? 0,
      avgSecondsPerImage: avgSeconds,
    });
  }

  for (const url of configuredUrls) {
    if (knownUrls.has(url)) {
      continue;
    }
    if (nodes.some((node) => node.baseUrl === url)) {
      continue;
    }
    nodes.push({
      baseUrl: url,
      active: configuredSet.has(url),
      processed: 0,
      avgSecondsPerImage: null,
    });
  }

  return nodes;
}

export function formatSecondsPerImage(value: number | null): string {
  if (value === null || !Number.isFinite(value) || value <= 0) {
    return '— s/image';
  }
  if (value < 1) {
    return `${value.toFixed(2)} s/image`;
  }
  if (value < 10) {
    return `${value.toFixed(1)} s/image`;
  }
  return `${Math.round(value)} s/image`;
}
