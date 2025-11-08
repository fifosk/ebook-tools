import React, { useEffect, useMemo, useState } from 'react';
import { timingStore } from '../stores/timingStore';
import type { TimingPayload, WordToken, Segment } from '../types/timing';

export type HLDebugState = {
  enabled?: boolean;
  showGates?: boolean;
  showPauses?: boolean;
  showDrift?: boolean;
};

declare global {
  interface Window {
    __HL_DEBUG__?: HLDebugState;
  }
}

const EMPTY_STATE: HLDebugState = { enabled: false };

function useHLDebug(): HLDebugState {
  const initial = typeof window === 'undefined' ? EMPTY_STATE : { ...(window.__HL_DEBUG__ ?? EMPTY_STATE) };
  const [state, setState] = useState<HLDebugState>(initial);
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handle = () => setState({ ...(window.__HL_DEBUG__ ?? EMPTY_STATE) });
    window.addEventListener('hl_debug_update', handle);
    return () => window.removeEventListener('hl_debug_update', handle);
  }, []);
  return state ?? EMPTY_STATE;
}

function useTimingSnapshot() {
  const [snapshot, setSnapshot] = useState(timingStore.get());
  useEffect(() => timingStore.subscribe(setSnapshot), []);
  return snapshot;
}

function getSentenceTokens(payload?: TimingPayload, sentenceIdx?: number): WordToken[] {
  if (!payload || sentenceIdx === undefined || sentenceIdx === null) {
    return [];
  }
  const segment = payload.segments.find((seg: Segment) => seg.sentenceIdx === sentenceIdx);
  return segment?.tokens ?? [];
}

export const DebugOverlay: React.FC<{ audioEl?: HTMLAudioElement | null }> = ({ audioEl }) => {
  const dbg = useHLDebug();
  const { payload, activeGate, last } = useTimingSnapshot();

  if (!dbg.enabled || !payload || !activeGate) {
    return null;
  }

  const lane: 'mix' | 'translation' = last?.lane ?? (payload.trackKind === 'translation_only' ? 'translation' : 'mix');
  const tokens = getSentenceTokens(payload, activeGate.sentenceIdx);

  const driftInfo = useMemo(() => {
    if (!tokens.length) {
      return null;
    }
    const validationToken = tokens.find((token) => token.validation);
    const lastToken = tokens[tokens.length - 1];
    return {
      backendDrift: validationToken?.validation?.drift ?? undefined,
      lastToken,
    };
  }, [tokens]);

  const pauseInfo = useMemo(() => {
    const before = tokens.find((token) => typeof token.pauseBeforeMs === 'number')?.pauseBeforeMs ?? 0;
    const after = tokens.find((token) => typeof token.pauseAfterMs === 'number')?.pauseAfterMs ?? 0;
    return { before, after };
  }, [tokens]);

  const startGate = activeGate.start ?? driftInfo?.lastToken?.startGate ?? 0;
  const endGate = activeGate.end ?? driftInfo?.lastToken?.endGate ?? startGate;
  const currentTime = audioEl?.currentTime ?? 0;
  const span = Math.max(endGate - startGate, 0.0001);
  const pct = (value: number) => Math.max(0, Math.min(100, ((value - startGate) / span) * 100));

  return (
    <div className="hl-debug-overlay" data-lane={lane}>
      <div className="hl-debug-panel">
        <div>
          <b>Lane:</b> {lane}
        </div>
        <div>
          <b>SentenceIdx:</b> {activeGate.sentenceIdx ?? '-'}
        </div>
        <div>
          <b>Gate:</b> {startGate.toFixed(3)} → {endGate.toFixed(3)} s
        </div>
        {dbg.showPauses ? (
          <div>
            <b>Pauses:</b> before {pauseInfo.before ?? 0} ms, after {pauseInfo.after ?? 0} ms
          </div>
        ) : null}
        {dbg.showDrift ? (
          <div>
            <b>Backend drift:</b>{' '}
            {driftInfo?.backendDrift !== undefined
              ? `${driftInfo.backendDrift.toFixed(3)} s`
              : '—'}
          </div>
        ) : null}
        <div>
          <b>Current time:</b> {currentTime.toFixed(3)} s
        </div>
      </div>
      <div className="hl-debug-ruler">
        {dbg.showGates ? <div className="gate gate-start" style={{ left: `${pct(startGate)}%` }} /> : null}
        {dbg.showGates ? <div className="gate gate-end" style={{ left: `${pct(endGate)}%` }} /> : null}
        {currentTime >= startGate && currentTime <= endGate ? (
          <div className="now" style={{ left: `${pct(currentTime)}%` }} />
        ) : null}
        {dbg.showPauses && pauseInfo.before ? (
          <div className="pause pause-before" style={{ width: `${(pauseInfo.before / 1000 / span) * 100}%` }} />
        ) : null}
        {dbg.showPauses && pauseInfo.after ? (
          <div className="pause pause-after" style={{ width: `${(pauseInfo.after / 1000 / span) * 100}%` }} />
        ) : null}
      </div>
    </div>
  );
};
