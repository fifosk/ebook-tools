import { useEffect, useRef, useState } from 'react';
import { extractTextFromHtml } from '../../utils/mediaFormatters';

type TextPreview = {
  url: string;
  content: string;
  raw: string;
};

type UseTextPreviewResult = {
  textPreview: TextPreview | null;
  textLoading: boolean;
  textError: string | null;
};

export function useTextPreview(url: string | null | undefined): UseTextPreviewResult {
  const textContentCache = useRef(new Map<string, { raw: string; plain: string }>());
  const [textPreview, setTextPreview] = useState<TextPreview | null>(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);

  useEffect(() => {
    const targetUrl = typeof url === 'string' ? url : '';
    if (!targetUrl) {
      setTextPreview(null);
      setTextError(null);
      setTextLoading(false);
      return;
    }

    const cached = textContentCache.current.get(targetUrl);
    if (cached) {
      setTextPreview({ url: targetUrl, content: cached.plain, raw: cached.raw });
      setTextError(null);
      setTextLoading(false);
      return;
    }

    let cancelled = false;
    setTextLoading(true);
    setTextError(null);
    setTextPreview(null);

    if (typeof fetch !== 'function') {
      setTextLoading(false);
      setTextPreview(null);
      setTextError('Document preview is unavailable in this environment.');
      return;
    }

    fetch(targetUrl, { credentials: 'include' })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load document (status ${response.status})`);
        }
        return response.text();
      })
      .then((raw) => {
        if (cancelled) {
          return;
        }

        const normalised = extractTextFromHtml(raw);
        textContentCache.current.set(targetUrl, { raw, plain: normalised });
        setTextPreview({ url: targetUrl, content: normalised, raw });
        setTextError(null);
      })
      .catch((requestError) => {
        if (cancelled) {
          return;
        }
        const message =
          requestError instanceof Error
            ? requestError.message
            : 'Failed to load document.';
        setTextError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setTextLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [url]);

  return { textPreview, textLoading, textError };
}
