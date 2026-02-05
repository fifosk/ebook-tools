export function sanitizeLookupQuery(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return '';
  }
  const stripped = trimmed.replace(/^[\s"'""''()[\]{}<>.,!?;:]+|[\s"'""''()[\]{}<>.,!?;:]+$/g, '');
  return stripped.trim() || trimmed;
}

export function tokenizeSentenceText(value: string | null | undefined): string[] {
  if (!value) {
    return [];
  }
  return value
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}
