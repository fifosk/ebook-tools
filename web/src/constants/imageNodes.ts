export type ImageApiNodeOption = {
  value: string;
  label: string;
  defaultActive?: boolean;
  fallbackValues?: string[];
};

export const IMAGE_API_NODE_OPTIONS: ImageApiNodeOption[] = [
  {
    value: 'http://192.168.1.9:7860',
    label: 'Mac Studio (192.168.1.9:7860)',
    defaultActive: true
  },
  {
    value: 'http://192.168.1.157:7860',
    label: 'MacBook Air (192.168.1.157:7860)',
    defaultActive: true,
    fallbackValues: ['http://192.168.1.209:7860']
  },
  {
    value: 'http://192.168.1.76:7860',
    label: 'Ipad Pro (192.168.1.76:7860)',
    defaultActive: true
  }
];

export function normalizeImageNodeUrl(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, '');
}

export function getImageNodeFallbacks(value: string): string[] {
  const normalized = normalizeImageNodeUrl(value);
  if (!normalized) {
    return [];
  }
  const option = IMAGE_API_NODE_OPTIONS.find(
    (entry) => normalizeImageNodeUrl(entry.value) === normalized
  );
  if (!option?.fallbackValues?.length) {
    return [];
  }
  const fallbacks: string[] = [];
  for (const entry of option.fallbackValues) {
    const fallback = normalizeImageNodeUrl(entry);
    if (fallback) {
      fallbacks.push(fallback);
    }
  }
  return fallbacks;
}

export function expandImageNodeCandidates(values: string[]): string[] {
  const expanded: string[] = [];
  const seen = new Set<string>();
  values.forEach((entry) => {
    const normalized = normalizeImageNodeUrl(entry);
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    expanded.push(normalized);
    const fallbacks = getImageNodeFallbacks(normalized);
    fallbacks.forEach((fallback) => {
      if (!fallback || seen.has(fallback)) {
        return;
      }
      seen.add(fallback);
      expanded.push(fallback);
    });
  });
  return expanded;
}

export function resolveImageNodeLabel(value: string): string | null {
  const normalized = normalizeImageNodeUrl(value);
  if (!normalized) {
    return null;
  }
  for (const option of IMAGE_API_NODE_OPTIONS) {
    const primary = normalizeImageNodeUrl(option.value);
    if (primary && primary === normalized) {
      return option.label;
    }
    const fallbacks = option.fallbackValues ?? [];
    for (const entry of fallbacks) {
      const fallback = normalizeImageNodeUrl(entry);
      if (fallback && fallback === normalized) {
        return `${option.label} (fallback ${fallback})`;
      }
    }
  }
  return null;
}

export const DEFAULT_IMAGE_API_BASE_URLS = IMAGE_API_NODE_OPTIONS.filter(
  (option) => option.defaultActive
).map((option) => option.value);
