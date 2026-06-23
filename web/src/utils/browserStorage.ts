export type BrowserStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export function isBrowserStorage(value: unknown): value is BrowserStorage {
  return Boolean(
    value &&
      typeof value === 'object' &&
      typeof (value as BrowserStorage).getItem === 'function' &&
      typeof (value as BrowserStorage).setItem === 'function' &&
      typeof (value as BrowserStorage).removeItem === 'function',
  );
}

export function getBrowserStorage(kind: 'local' | 'session'): BrowserStorage | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const storage = kind === 'local' ? window.localStorage : window.sessionStorage;
    return isBrowserStorage(storage) ? storage : null;
  } catch (error) {
    return null;
  }
}

export function getStorageItem(storage: BrowserStorage | null, key: string): string | null {
  if (!isBrowserStorage(storage)) {
    return null;
  }
  try {
    return storage.getItem(key);
  } catch (error) {
    return null;
  }
}

export function setStorageItem(storage: BrowserStorage | null, key: string, value: string): void {
  if (!isBrowserStorage(storage)) {
    return;
  }
  try {
    storage.setItem(key, value);
  } catch (error) {
    // Ignore disabled storage and quota errors.
  }
}

export function removeStorageItem(storage: BrowserStorage | null, key: string): void {
  if (!isBrowserStorage(storage)) {
    return;
  }
  try {
    storage.removeItem(key);
  } catch (error) {
    // Ignore disabled storage errors.
  }
}

export function getLocalStorageItem(key: string): string | null {
  return getStorageItem(getBrowserStorage('local'), key);
}

export function setLocalStorageItem(key: string, value: string): void {
  setStorageItem(getBrowserStorage('local'), key, value);
}

export function removeLocalStorageItem(key: string): void {
  removeStorageItem(getBrowserStorage('local'), key);
}

