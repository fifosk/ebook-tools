export type LlmProviderTag = 'ollama_local' | 'ollama_cloud' | 'lmstudio_local';

const PROVIDER_ALIASES: Record<string, LlmProviderTag> = {
  'ollama_local': 'ollama_local',
  'ollama-local': 'ollama_local',
  'ollama_cloud': 'ollama_cloud',
  'ollama-cloud': 'ollama_cloud',
  'lmstudio': 'lmstudio_local',
  'lmstudio_local': 'lmstudio_local',
  'lmstudio-local': 'lmstudio_local',
};

export function splitLlmModelId(
  value: string | null | undefined,
): { provider: LlmProviderTag | null; model: string | null } {
  if (!value) {
    return { provider: null, model: null };
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return { provider: null, model: null };
  }
  const separatorIndex = trimmed.indexOf(':');
  if (separatorIndex < 0) {
    return { provider: null, model: trimmed };
  }
  const prefix = trimmed.slice(0, separatorIndex).trim().toLowerCase();
  const provider = PROVIDER_ALIASES[prefix] ?? null;
  if (!provider) {
    return { provider: null, model: trimmed };
  }
  const model = trimmed.slice(separatorIndex + 1).trim();
  return { provider, model: model.length > 0 ? model : null };
}

export function isLocalLlmProvider(provider: LlmProviderTag | null): boolean | null {
  if (!provider) {
    return null;
  }
  if (provider === 'ollama_cloud') {
    return false;
  }
  if (provider === 'ollama_local' || provider === 'lmstudio_local') {
    return true;
  }
  return null;
}
