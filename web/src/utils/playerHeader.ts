const HEADER_COLLAPSE_KEY = 'player.headerCollapsed';

function parseBool(value: string | null): boolean {
  if (!value) {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized === 'true' || normalized === '1' || normalized === 'yes' || normalized === 'on';
}

export function loadHeaderCollapsed(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    return parseBool(window.localStorage.getItem(HEADER_COLLAPSE_KEY));
  } catch {
    return false;
  }
}

export function storeHeaderCollapsed(value: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(HEADER_COLLAPSE_KEY, String(value));
  } catch {
    return;
  }
}

export { HEADER_COLLAPSE_KEY };
