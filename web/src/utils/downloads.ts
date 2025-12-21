type SaveFilePicker = (options?: {
  suggestedName?: string;
  types?: Array<{ description?: string; accept: Record<string, string[]> }>;
}) => Promise<{
  createWritable: () => Promise<{ write: (data: Blob | Uint8Array) => Promise<void>; close: () => Promise<void> }>;
}>;

const DEFAULT_EXPORT_NAME = 'export.zip';
const ZIP_TYPES = [
  {
    description: 'Zip archive',
    accept: {
      'application/zip': ['.zip']
    }
  }
];

const getSavePicker = (): SaveFilePicker | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  const picker = (window as Window & { showSaveFilePicker?: SaveFilePicker }).showSaveFilePicker;
  return typeof picker === 'function' ? picker : null;
};

const isDomError = (error: unknown, names: string[]) =>
  error instanceof DOMException && names.includes(error.name);

export async function downloadWithSaveAs(url: string, filename?: string | null): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  const safeName = filename && filename.trim() ? filename.trim() : DEFAULT_EXPORT_NAME;
  const savePicker = getSavePicker();
  if (savePicker) {
    try {
      const handle = await savePicker({
        suggestedName: safeName,
        types: ZIP_TYPES
      });
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) {
        throw new Error(`Download failed (${response.status})`);
      }
      const writable = await handle.createWritable();
      if (response.body) {
        const reader = response.body.getReader();
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }
          if (value) {
            await writable.write(value);
          }
        }
        await writable.close();
      } else {
        const blob = await response.blob();
        await writable.write(blob);
        await writable.close();
      }
      return;
    } catch (error) {
      if (isDomError(error, ['AbortError', 'NotAllowedError'])) {
        return;
      }
      if (!isDomError(error, ['SecurityError'])) {
        throw error;
      }
    }
  }

  if (typeof document === 'undefined') {
    return;
  }
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = safeName;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}
