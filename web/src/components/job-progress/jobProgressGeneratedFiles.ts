import type { PipelineStatusResponse } from '../../api/dtos';

function coerceGeneratedRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function coerceGeneratedNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function generatedFileCandidates(status: PipelineStatusResponse): unknown[] {
  const resultGenerated =
    status.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)['generated_files']
      : undefined;
  return [status.generated_files, resultGenerated];
}

export function resolveGeneratedFileRecord(
  generatedFiles: unknown,
  key: string,
): Record<string, unknown> | null {
  const generated = coerceGeneratedRecord(generatedFiles);
  return generated ? coerceGeneratedRecord(generated[key]) : null;
}

export function resolveGeneratedChunks(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown>[] {
  const chunks: Record<string, unknown>[] = [];
  const seenChunkIds = new Set<string>();
  if (!status) {
    return chunks;
  }
  const candidates = generatedFileCandidates(status);
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== 'object') {
      continue;
    }
    const records = (candidate as Record<string, unknown>).chunks;
    if (Array.isArray(records)) {
      for (const entry of records) {
        if (entry && typeof entry === 'object') {
          const record = entry as Record<string, unknown>;
          const rawChunkId = record.chunk_id ?? record.chunkId;
          const chunkId = typeof rawChunkId === 'string' ? rawChunkId.trim() : '';
          if (chunkId) {
            if (seenChunkIds.has(chunkId)) {
              continue;
            }
            seenChunkIds.add(chunkId);
          }
          chunks.push(record);
        }
      }
    }
  }
  return chunks;
}

export function resolveGeneratedFiles(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown>[] {
  const files: Record<string, unknown>[] = [];
  const seenKeys = new Set<string>();
  if (!status) {
    return files;
  }
  const candidates = generatedFileCandidates(status);
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== 'object') {
      continue;
    }
    const records = (candidate as Record<string, unknown>).files;
    if (Array.isArray(records)) {
      for (const entry of records) {
        if (entry && typeof entry === 'object') {
          const record = entry as Record<string, unknown>;
          const pathValue = typeof record.path === 'string' ? record.path.trim() : '';
          const typeValue = typeof record.type === 'string' ? record.type.trim() : '';
          const key = `${typeValue}\u0000${pathValue}`;
          if (pathValue || typeValue) {
            if (seenKeys.has(key)) {
              continue;
            }
            seenKeys.add(key);
          }
          files.push(record);
        }
      }
    }
  }
  return files;
}

export function resolveImagePromptPlanSummary(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown> | null {
  if (!status) {
    return null;
  }
  const candidates = generatedFileCandidates(status);
  for (const candidate of candidates) {
    const record = coerceGeneratedRecord(candidate);
    if (!record) {
      continue;
    }
    const summary = coerceGeneratedRecord(record['image_prompt_plan_summary']);
    if (summary) {
      return summary;
    }
  }
  return null;
}

export function countGeneratedImages(status: PipelineStatusResponse | undefined): number {
  const files = resolveGeneratedFiles(status);
  let count = 0;
  for (const entry of files) {
    const typeValue = typeof entry.type === 'string' ? entry.type.trim().toLowerCase() : '';
    const pathValue = typeof entry.path === 'string' ? entry.path.toLowerCase() : '';
    if (typeValue === 'image') {
      count += 1;
      continue;
    }
    if (
      pathValue.includes('/images/') &&
      (pathValue.endsWith('.png') || pathValue.endsWith('.jpg') || pathValue.endsWith('.jpeg'))
    ) {
      count += 1;
    }
  }
  return count;
}

export function sumRetryCounts(bucket: Record<string, number> | null | undefined): number {
  if (!bucket) {
    return 0;
  }
  return Object.values(bucket).reduce((sum, count) => {
    if (typeof count !== 'number' || !Number.isFinite(count)) {
      return sum;
    }
    return sum + Math.max(0, count);
  }, 0);
}

export function resolveSentenceRange(
  status: PipelineStatusResponse | undefined,
): { start: number | null; end: number | null } {
  const chunks = resolveGeneratedChunks(status);
  let minStart: number | null = null;
  let maxEnd: number | null = null;
  for (const chunk of chunks) {
    const rawStart = chunk['start_sentence'] ?? chunk['startSentence'];
    const rawEnd = chunk['end_sentence'] ?? chunk['endSentence'];
    const startValue = coerceGeneratedNumber(rawStart);
    const endValue = coerceGeneratedNumber(rawEnd);
    if (startValue !== null && (minStart === null || startValue < minStart)) {
      minStart = startValue;
    }
    if (endValue !== null && (maxEnd === null || endValue > maxEnd)) {
      maxEnd = endValue;
    }
  }
  return { start: minStart, end: maxEnd };
}
