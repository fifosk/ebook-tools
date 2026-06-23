import '@testing-library/jest-dom/vitest';

function isUsableStorage(storage: unknown): storage is Storage {
  return (
    typeof storage === 'object' &&
    storage !== null &&
    typeof (storage as Storage).getItem === 'function' &&
    typeof (storage as Storage).setItem === 'function' &&
    typeof (storage as Storage).removeItem === 'function' &&
    typeof (storage as Storage).clear === 'function'
  );
}

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    removeItem: (key) => {
      values.delete(key);
    },
    setItem: (key, value) => {
      values.set(key, String(value));
    }
  };
}

function installStorageIfNeeded(name: 'localStorage' | 'sessionStorage') {
  const existing = typeof window !== 'undefined' ? window[name] : undefined;
  if (isUsableStorage(existing)) {
    Object.defineProperty(globalThis, name, {
      configurable: true,
      value: existing
    });
    return;
  }

  const storage = createMemoryStorage();
  Object.defineProperty(globalThis, name, {
    configurable: true,
    value: storage
  });

  if (typeof window !== 'undefined') {
    Object.defineProperty(window, name, {
      configurable: true,
      value: storage
    });
  }
}

installStorageIfNeeded('localStorage');
installStorageIfNeeded('sessionStorage');

if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false
    })
  });
}
