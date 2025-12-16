import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { fetchSentenceImageInfo, regenerateSentenceImage } from '../api/client';
import type { SentenceImageRegenerateRequestPayload } from '../api/dtos';
import { useMyPainter, type MyPainterSentenceContext } from '../context/MyPainterProvider';
import { resolve as resolveStoragePath } from '../utils/storageResolver';
import styles from './MyPainterAssistant.module.css';

type PanelSize = { width: number; height: number };
type ResizeDirection = 'nw' | 'ne' | 'sw' | 'se' | 'n' | 's' | 'e' | 'w';

const STORAGE_KEYS = {
  panelWidth: 'ebookTools.myPainter.panelWidth',
  panelHeight: 'ebookTools.myPainter.panelHeight',
} as const;

function toNumberOrNull(value: string, kind: 'int' | 'float'): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = kind === 'int' ? Number.parseInt(trimmed, 10) : Number.parseFloat(trimmed);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function loadStoredNumber(key: string): number | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(key);
    if (!stored) {
      return null;
    }
    const parsed = Number.parseFloat(stored);
    return Number.isFinite(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function storeNumber(key: string, value: number): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(key, String(value));
  } catch {
    // ignore
  }
}

function formatJobId(jobId: string | null | undefined): string {
  const trimmed = (jobId ?? '').trim();
  if (!trimmed) {
    return '';
  }
  if (trimmed.length <= 12) {
    return trimmed;
  }
  return `${trimmed.slice(0, 8)}…${trimmed.slice(-4)}`;
}

function sentenceKey(context: MyPainterSentenceContext | null): string {
  if (!context?.jobId || !context.sentenceNumber) {
    return '';
  }
  const fragment = context.rangeFragment ?? '';
  return `${context.jobId}::${context.sentenceNumber}::${fragment}`;
}

export default function MyPainterAssistant() {
  const { isOpen, open, close, toggle, playerSentence, consumePendingOpenOptions, bumpImageRefreshToken, imageRefreshToken } =
    useMyPainter();
  const [followPlayer, setFollowPlayer] = useState(true);
  const [targetSentence, setTargetSentence] = useState<MyPainterSentenceContext | null>(null);
  const [lastLoadedKey, setLastLoadedKey] = useState('');
  const [panelSize, setPanelSize] = useState<PanelSize>(() => ({
    width: loadStoredNumber(STORAGE_KEYS.panelWidth) ?? 420,
    height: loadStoredNumber(STORAGE_KEYS.panelHeight) ?? 520,
  }));
  const [viewport, setViewport] = useState<{ width: number; height: number }>(() => ({
    width: typeof window === 'undefined' ? 1280 : window.innerWidth,
    height: typeof window === 'undefined' ? 800 : window.innerHeight,
  }));

  const [sentenceText, setSentenceText] = useState('');
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');

  const [width, setWidth] = useState('500');
  const [height, setHeight] = useState('500');
  const [steps, setSteps] = useState('12');
  const [cfgScale, setCfgScale] = useState('7.0');
  const [samplerName, setSamplerName] = useState('');
  const [seed, setSeed] = useState('');

  const [isWorking, setIsWorking] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isMountedRef = useRef(true);
  const panelRef = useRef<HTMLElement | null>(null);
  const resizeSessionRef = useRef<{
    dir: ResizeDirection;
    pointerId: number;
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
  } | null>(null);
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    storeNumber(STORAGE_KEYS.panelWidth, panelSize.width);
    storeNumber(STORAGE_KEYS.panelHeight, panelSize.height);
  }, [panelSize.height, panelSize.width]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handle = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handle);
    return () => window.removeEventListener('resize', handle);
  }, []);

  const clampPanelSize = useCallback(
    (size: PanelSize): PanelSize => {
      const maxWidth = Math.min(520, Math.max(320, viewport.width - 36));
      const maxHeight = Math.min(720, Math.max(360, viewport.height - 120));
      return {
        width: Math.max(320, Math.min(maxWidth, size.width)),
        height: Math.max(360, Math.min(maxHeight, size.height)),
      };
    },
    [viewport.height, viewport.width],
  );

  useEffect(() => {
    setPanelSize((previous) => {
      const clamped = clampPanelSize(previous);
      if (clamped.width === previous.width && clamped.height === previous.height) {
        return previous;
      }
      return clamped;
    });
  }, [clampPanelSize]);

  const beginResize = useCallback(
    (event: ReactPointerEvent, dir: ResizeDirection) => {
      if (!panelRef.current) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      resizeSessionRef.current = {
        dir,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startWidth: panelSize.width,
        startHeight: panelSize.height,
      };
      try {
        panelRef.current.setPointerCapture(event.pointerId);
      } catch {
        // ignore
      }
    },
    [panelSize.height, panelSize.width],
  );

  const applyResize = useCallback(
    (event: ReactPointerEvent) => {
      const session = resizeSessionRef.current;
      if (!session || session.pointerId !== event.pointerId) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const dx = event.clientX - session.startX;
      const dy = event.clientY - session.startY;
      const affectsWidth = session.dir.includes('e') || session.dir.includes('w');
      const affectsHeight = session.dir.includes('n') || session.dir.includes('s');

      const nextWidth = affectsWidth
        ? session.startWidth + (session.dir.includes('w') ? -dx : dx)
        : session.startWidth;
      const nextHeight = affectsHeight
        ? session.startHeight + (session.dir.includes('n') ? -dy : dy)
        : session.startHeight;

      setPanelSize(clampPanelSize({ width: nextWidth, height: nextHeight }));
    },
    [clampPanelSize],
  );

  const endResize = useCallback((event: ReactPointerEvent) => {
    const session = resizeSessionRef.current;
    if (!session || session.pointerId !== event.pointerId) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    resizeSessionRef.current = null;
    try {
      panelRef.current?.releasePointerCapture(event.pointerId);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const pending = consumePendingOpenOptions();
    if (!pending) {
      return;
    }
    setLastLoadedKey('');
    setErrorMessage(null);
    setStatusMessage(null);

    const follow = typeof pending.followPlayer === 'boolean' ? pending.followPlayer : true;
    setFollowPlayer(follow);

    if (pending.sentence) {
      setTargetSentence(pending.sentence);
      return;
    }
    setTargetSentence(playerSentence);
  }, [consumePendingOpenOptions, isOpen, playerSentence]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    if (!followPlayer) {
      return;
    }
    setTargetSentence(playerSentence);
  }, [followPlayer, isOpen, playerSentence]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const key = sentenceKey(targetSentence);
    if (!key || key === lastLoadedKey) {
      return;
    }
    setLastLoadedKey(key);
    setErrorMessage(null);
    setStatusMessage(null);

    const nextSentenceText = targetSentence?.sentenceText ?? '';
    setSentenceText(nextSentenceText);
    setPrompt(targetSentence?.prompt ?? '');
    setNegativePrompt(targetSentence?.negativePrompt ?? '');
  }, [isOpen, lastLoadedKey, targetSentence]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const jobId = targetSentence?.jobId ?? null;
    const sentenceNumber = targetSentence?.sentenceNumber ?? null;
    if (!jobId || !sentenceNumber) {
      return;
    }
    let cancelled = false;
    fetchSentenceImageInfo(jobId, sentenceNumber)
      .then((info) => {
        if (cancelled || !isMountedRef.current) {
          return;
        }
        if (typeof info.sentence === 'string' && info.sentence.trim()) {
          setSentenceText((current) => (current.trim() ? current : info.sentence?.trim() ?? current));
        }
        if (typeof info.prompt === 'string' && info.prompt.trim()) {
          setPrompt((current) => (current.trim() ? current : info.prompt?.trim() ?? current));
        }
        if (typeof info.negative_prompt === 'string' && info.negative_prompt.trim()) {
          setNegativePrompt((current) =>
            current.trim() ? current : info.negative_prompt?.trim() ?? current,
          );
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [isOpen, targetSentence?.jobId, targetSentence?.sentenceNumber]);

  const previewUrl = useMemo(() => {
    const jobId = targetSentence?.jobId ?? null;
    if (!jobId) {
      return null;
    }
    const rel = targetSentence?.imagePath ?? null;
    if (!rel || rel.includes('://')) {
      return null;
    }
    const token = imageRefreshToken > 0 ? `?v=${encodeURIComponent(String(imageRefreshToken))}` : '';
    try {
      return resolveStoragePath(jobId, `${rel}${token}`);
    } catch {
      return null;
    }
  }, [imageRefreshToken, targetSentence?.imagePath, targetSentence?.jobId]);

  const resolvedJobIdLabel = useMemo(() => formatJobId(targetSentence?.jobId ?? null), [targetSentence?.jobId]);
  const resolvedSentenceNumber = targetSentence?.sentenceNumber ?? null;
  const resolvedRange = targetSentence?.rangeFragment ?? null;

  const canSubmit = Boolean(
    (targetSentence?.jobId ?? '').trim() &&
      typeof resolvedSentenceNumber === 'number' &&
      Number.isFinite(resolvedSentenceNumber) &&
      resolvedSentenceNumber > 0 &&
      prompt.trim(),
  );

  const handleUseCurrentSentence = useCallback(() => {
    setTargetSentence(playerSentence);
    setFollowPlayer(false);
  }, [playerSentence]);

  const handleRegenerate = useCallback(async () => {
    const jobId = (targetSentence?.jobId ?? '').trim();
    const sentenceNumber = targetSentence?.sentenceNumber ?? null;
    if (!jobId || !sentenceNumber) {
      return;
    }
    setFollowPlayer(false);
    const promptValue = prompt.trim();
    if (!promptValue) {
      setErrorMessage('Prompt is required.');
      return;
    }

    const payload: SentenceImageRegenerateRequestPayload = {
      prompt: promptValue,
      negative_prompt: negativePrompt.trim() ? negativePrompt.trim() : null,
      width: toNumberOrNull(width, 'int'),
      height: toNumberOrNull(height, 'int'),
      steps: toNumberOrNull(steps, 'int'),
      cfg_scale: toNumberOrNull(cfgScale, 'float'),
      sampler_name: samplerName.trim() ? samplerName.trim() : null,
      seed: toNumberOrNull(seed, 'int'),
    };

    setIsWorking(true);
    setErrorMessage(null);
    setStatusMessage('Generating…');
    try {
      const response = await regenerateSentenceImage(jobId, sentenceNumber, payload);
      if (!isMountedRef.current) {
        return;
      }
      bumpImageRefreshToken();
      setPrompt(response.prompt ?? promptValue);
      setNegativePrompt(response.negative_prompt ?? negativePrompt.trim());
      setStatusMessage(`Saved ${response.relative_path}`);
      setTargetSentence((current) => {
        if (!current) {
          return current;
        }
        if (current.jobId !== jobId || current.sentenceNumber !== sentenceNumber) {
          return current;
        }
        return {
          ...current,
          rangeFragment: response.range_fragment ?? current.rangeFragment,
          imagePath: response.relative_path ?? current.imagePath,
          prompt: response.prompt ?? current.prompt,
          negativePrompt: response.negative_prompt ?? current.negativePrompt,
        };
      });
    } catch (error) {
      if (!isMountedRef.current) {
        return;
      }
      const message = error instanceof Error ? error.message : 'Unable to regenerate image.';
      setErrorMessage(message);
      setStatusMessage(null);
    } finally {
      if (isMountedRef.current) {
        setIsWorking(false);
      }
    }
  }, [
    bumpImageRefreshToken,
    cfgScale,
    height,
    negativePrompt,
    prompt,
    samplerName,
    seed,
    steps,
    targetSentence?.jobId,
    targetSentence?.sentenceNumber,
    width,
  ]);

  if (!isOpen) {
    return (
      <div className={styles.launcher}>
        <button type="button" className={styles.launcherButton} onClick={() => open({})} aria-label="Open MyPainter">
          <span className={styles.launcherGlyph} aria-hidden="true">
            <svg viewBox="0 0 24 24" role="img" focusable="false">
              <path d="M7 14c-1.7 0-3 1.3-3 3v4h4c1.7 0 3-1.3 3-3v-4H7Z" />
              <path
                d="M20.7 7.3 16.7 3.3a1 1 0 0 0-1.4 0L7.8 10.8c-.5.5-.8 1.2-.8 1.9V14h1.3c.7 0 1.4-.3 1.9-.8l7.5-7.5a1 1 0 0 0 0-1.4Z"
                opacity="0.9"
              />
            </svg>
          </span>
          <span className={styles.launcherLabel}>MyPainter</span>
        </button>
      </div>
    );
  }

  return (
    <>
      <div className={styles.launcher}>
        <button type="button" className={styles.launcherButton} onClick={close} aria-label="Close MyPainter">
          <span className={styles.launcherGlyph} aria-hidden="true">
            <svg viewBox="0 0 24 24" role="img" focusable="false">
              <path d="M7 14c-1.7 0-3 1.3-3 3v4h4c1.7 0 3-1.3 3-3v-4H7Z" />
              <path
                d="M20.7 7.3 16.7 3.3a1 1 0 0 0-1.4 0L7.8 10.8c-.5.5-.8 1.2-.8 1.9V14h1.3c.7 0 1.4-.3 1.9-.8l7.5-7.5a1 1 0 0 0 0-1.4Z"
                opacity="0.9"
              />
            </svg>
          </span>
          <span className={styles.launcherLabel}>MyPainter</span>
        </button>
      </div>
      <section
        className={styles.panel}
        aria-label="MyPainter"
        ref={panelRef as unknown as React.RefObject<HTMLElement>}
        style={{ width: panelSize.width, height: panelSize.height }}
        onPointerMove={applyResize}
        onPointerUp={endResize}
        onPointerCancel={endResize}
      >
        <div className={styles.resizeHandles} aria-hidden="true">
          <div
            className={[styles.resizeHandle, styles.resizeHandleNw].join(' ')}
            onPointerDown={(e) => beginResize(e, 'nw')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleNe].join(' ')}
            onPointerDown={(e) => beginResize(e, 'ne')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleSw].join(' ')}
            onPointerDown={(e) => beginResize(e, 'sw')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleSe].join(' ')}
            onPointerDown={(e) => beginResize(e, 'se')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleN].join(' ')}
            onPointerDown={(e) => beginResize(e, 'n')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleS].join(' ')}
            onPointerDown={(e) => beginResize(e, 's')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleE].join(' ')}
            onPointerDown={(e) => beginResize(e, 'e')}
          />
          <div
            className={[styles.resizeHandle, styles.resizeHandleW].join(' ')}
            onPointerDown={(e) => beginResize(e, 'w')}
          />
        </div>
        <header className={styles.header}>
          <div className={styles.titleBlock}>
            <div className={styles.title}>MyPainter</div>
            <div className={styles.subtitle}>
              {resolvedJobIdLabel && resolvedSentenceNumber
                ? `Job ${resolvedJobIdLabel} · Sentence ${resolvedSentenceNumber}`
                : 'Select a sentence in the interactive reader'}
            </div>
          </div>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={styles.iconButton}
              onClick={() => setFollowPlayer((value) => !value)}
              aria-pressed={followPlayer}
            >
              {followPlayer ? 'Following' : 'Frozen'}
            </button>
            <button type="button" className={styles.iconButton} onClick={close} aria-label="Close MyPainter">
              ✕
            </button>
          </div>
        </header>
        <div className={styles.body}>
          <div className={styles.section}>
            <div className={styles.sectionTitle}>Target</div>
            <div className={styles.metaGrid}>
              <div>
                <strong>Job</strong>: {resolvedJobIdLabel || '—'}
              </div>
              <div>
                <strong>Range</strong>: {resolvedRange || '—'}
              </div>
              <div>
                <strong>Sentence</strong>: {resolvedSentenceNumber ?? '—'}
              </div>
              <div>
                <strong>Image</strong>: {targetSentence?.imagePath ?? '—'}
              </div>
            </div>
          </div>

          {previewUrl ? (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>Preview</div>
              <div className={styles.preview}>
                <img src={previewUrl} alt="Sentence image preview" loading="lazy" />
              </div>
            </div>
          ) : null}

          <div className={styles.section}>
            <div className={styles.labelRow}>
              <span className={styles.label}>Sentence</span>
              <span className={styles.hint}>Read-only</span>
            </div>
            <textarea className={styles.textarea} value={sentenceText} readOnly />
          </div>

          <div className={styles.section}>
            <div className={styles.labelRow}>
              <span className={styles.label}>Prompt</span>
              <span className={styles.hint}>LLM-adjusted</span>
            </div>
            <textarea
              className={styles.textarea}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Diffusion prompt…"
            />
          </div>

          <div className={styles.section}>
            <div className={styles.labelRow}>
              <span className={styles.label}>Negative prompt</span>
              <span className={styles.hint}>Optional</span>
            </div>
            <textarea
              className={styles.textarea}
              value={negativePrompt}
              onChange={(event) => setNegativePrompt(event.target.value)}
              placeholder="Negative prompt…"
            />
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Settings</div>
            <div className={styles.settingsGrid}>
              <div className={styles.fieldRow}>
                <div className={styles.label}>Width</div>
                <input className={styles.input} value={width} onChange={(e) => setWidth(e.target.value)} inputMode="numeric" />
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.label}>Height</div>
                <input className={styles.input} value={height} onChange={(e) => setHeight(e.target.value)} inputMode="numeric" />
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.label}>Steps</div>
                <input className={styles.input} value={steps} onChange={(e) => setSteps(e.target.value)} inputMode="numeric" />
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.label}>CFG</div>
                <input className={styles.input} value={cfgScale} onChange={(e) => setCfgScale(e.target.value)} inputMode="decimal" />
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.label}>Sampler</div>
                <input className={styles.input} value={samplerName} onChange={(e) => setSamplerName(e.target.value)} placeholder="optional" />
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.label}>Seed</div>
                <input className={styles.input} value={seed} onChange={(e) => setSeed(e.target.value)} inputMode="numeric" placeholder="optional" />
              </div>
            </div>
          </div>
        </div>
        <footer className={styles.footer}>
          <div className={styles.footerLeft}>
            <div className={[styles.status, errorMessage ? styles.error : null].filter(Boolean).join(' ')}>
              {errorMessage ? errorMessage : statusMessage ?? 'Ready'}
            </div>
          </div>
          <div className={styles.footerActions}>
            <button type="button" className={styles.iconButton} onClick={handleUseCurrentSentence} disabled={!playerSentence}>
              Use current
            </button>
            <button type="button" className={styles.primaryButton} onClick={handleRegenerate} disabled={!canSubmit || isWorking}>
              {isWorking ? 'Working…' : 'Regenerate'}
            </button>
          </div>
        </footer>
      </section>
    </>
  );
}
