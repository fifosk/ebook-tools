/**
 * Group LLM model identifiers by their provider prefix for `<optgroup>` and
 * picker section UIs. The backend returns strings like
 * `ollama_cloud:mistral-large-3:675b` and `lmstudio_macbook:google/gemma-4-31b`;
 * this helper carves them into the four buckets the user-facing picker shows.
 */

export type LlmProviderTag =
  | 'ollama_cloud'
  | 'ollama_local'
  | 'lmstudio_macstudio'
  | 'lmstudio_macbook'
  | 'lmstudio_local'
  | 'unknown';

export type LlmModelGroup = {
  tag: LlmProviderTag;
  label: string;
  models: string[];
};

const PROVIDER_LABELS: Record<LlmProviderTag, string> = {
  ollama_cloud: 'Ollama Cloud',
  ollama_local: 'Ollama Local',
  lmstudio_macstudio: 'LM Studio – Mac Studio',
  lmstudio_macbook: 'LM Studio – MacBook Pro',
  lmstudio_local: 'LM Studio – Mac Studio',
  unknown: 'Other'
};

const GROUP_ORDER: LlmProviderTag[] = [
  'ollama_cloud',
  'ollama_local',
  'lmstudio_macstudio',
  'lmstudio_macbook',
  'lmstudio_local',
  'unknown'
];

const PROVIDER_ALIASES: Record<string, LlmProviderTag> = {
  ollama_cloud: 'ollama_cloud',
  'ollama-cloud': 'ollama_cloud',
  ollama_local: 'ollama_local',
  'ollama-local': 'ollama_local',
  lmstudio_macstudio: 'lmstudio_macstudio',
  'lmstudio-macstudio': 'lmstudio_macstudio',
  lmstudio_macbook: 'lmstudio_macbook',
  'lmstudio-macbook': 'lmstudio_macbook',
  lmstudio_local: 'lmstudio_local',
  'lmstudio-local': 'lmstudio_local',
  lmstudio: 'lmstudio_local'
};

export function parseLlmProvider(identifier: string): {
  provider: LlmProviderTag;
  model: string;
} {
  const trimmed = (identifier ?? '').trim();
  if (!trimmed) {
    return { provider: 'unknown', model: trimmed };
  }
  const colonIndex = trimmed.indexOf(':');
  if (colonIndex < 0) {
    return { provider: 'unknown', model: trimmed };
  }
  const prefix = trimmed.slice(0, colonIndex).toLowerCase();
  const rest = trimmed.slice(colonIndex + 1);
  const tag = PROVIDER_ALIASES[prefix];
  if (!tag) {
    return { provider: 'unknown', model: trimmed };
  }
  return { provider: tag, model: rest };
}

export function llmProviderLabel(tag: LlmProviderTag): string {
  return PROVIDER_LABELS[tag] ?? PROVIDER_LABELS.unknown;
}

/**
 * Strip the provider prefix and return the bare model name for display in a
 * picker option label. The optgroup title already announces the provider, so
 * the option itself shows just the model.
 */
export function bareLlmModelName(identifier: string): string {
  const { provider, model } = parseLlmProvider(identifier);
  if (provider === 'unknown' || !model) {
    return identifier;
  }
  return model;
}

/**
 * Group a flat list of provider-prefixed identifiers into ordered sections
 * suitable for `<optgroup>` elements. Group ordering matches the backend
 * sort: Ollama (cloud → local) before LM Studio (Mac Studio → MacBook).
 */
export function groupLlmModelsByProvider(
  models: readonly string[]
): LlmModelGroup[] {
  const buckets = new Map<LlmProviderTag, string[]>();
  for (const id of models) {
    if (!id) continue;
    const { provider } = parseLlmProvider(id);
    const list = buckets.get(provider) ?? [];
    list.push(id);
    buckets.set(provider, list);
  }
  const groups: LlmModelGroup[] = [];
  for (const tag of GROUP_ORDER) {
    const list = buckets.get(tag);
    if (!list || list.length === 0) continue;
    groups.push({ tag, label: PROVIDER_LABELS[tag], models: list });
  }
  return groups;
}
