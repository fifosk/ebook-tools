const PARAM_PATTERN = /(\d+(?:\.\d+)?)([bt])/i;

export function extractModelParameters(model: string | null | undefined): string | null {
  if (!model) {
    return null;
  }
  const normalized = model.trim();
  if (!normalized) {
    return null;
  }
  const match = normalized.toLowerCase().match(PARAM_PATTERN);
  if (!match) {
    return null;
  }
  const [, value, unit] = match;
  const suffix = unit.toLowerCase() === 't' ? 'T' : 'B';
  return `${value}${suffix}`;
}

export function formatModelLabel(model: string | null | undefined): string | null {
  if (!model) {
    return null;
  }
  const normalized = model.trim();
  if (!normalized) {
    return null;
  }
  const parameters = extractModelParameters(normalized);
  if (!parameters) {
    return normalized;
  }
  return `${normalized} (${parameters})`;
}

export default formatModelLabel;
