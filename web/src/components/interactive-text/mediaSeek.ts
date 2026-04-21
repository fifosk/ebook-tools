/**
 * Shared helpers for robust audio seeking — mirror the iOS improvements:
 *
 *   - {@link seekWithDriftCheck} — set `currentTime` and, once the `seeked`
 *     event fires, verify the playhead actually landed near the target. If
 *     the buffered range couldn't satisfy the first request (so the element
 *     landed short) we re-seek once. Prevents the "audio lags one syllable
 *     behind text" drift observed on slow networks.
 *
 *   - {@link mutedTransition} — wrap a seek in volume=0 / volume=restore so
 *     listeners never hear a blip from the previous sentence while the
 *     playhead is moving. Volume is restored on the `seeked` event (or a
 *     safety timeout, so a missing event never leaves the audio muted).
 */

const DRIFT_THRESHOLD_SEC = 0.1;
const SEEKED_TIMEOUT_MS = 500;

function clampToValidRange(element: HTMLMediaElement, target: number): number {
  let clamped = Number.isFinite(target) ? target : 0;
  clamped = Math.max(0, clamped);
  if (Number.isFinite(element.duration) && element.duration > 0) {
    clamped = Math.min(clamped, Math.max(element.duration - 0.05, 0));
  }
  return clamped;
}

/**
 * Assign `element.currentTime` and verify the playhead lands near the target.
 * If the observed position drifts more than 100 ms after the `seeked` event,
 * re-seek once. Returns a Promise that resolves when the seek is complete.
 */
export function seekWithDriftCheck(
  element: HTMLMediaElement,
  target: number,
): Promise<void> {
  const clamped = clampToValidRange(element, target);
  return new Promise<void>((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    const onSeeked = () => {
      element.removeEventListener('seeked', onSeeked);
      const observed = element.currentTime ?? 0;
      if (Math.abs(observed - clamped) > DRIFT_THRESHOLD_SEC) {
        if (typeof window !== 'undefined' && import.meta.env?.DEV) {
          console.debug('[mediaSeek] drift re-seek', { target: clamped, observed });
        }
        // Re-seek once. Attach a short-lived listener for the corrected seek.
        const onReseeked = () => {
          element.removeEventListener('seeked', onReseeked);
          finish();
        };
        element.addEventListener('seeked', onReseeked, { once: true });
        try {
          element.currentTime = clamped;
        } catch {
          finish();
        }
        window.setTimeout(finish, SEEKED_TIMEOUT_MS);
        return;
      }
      finish();
    };
    element.addEventListener('seeked', onSeeked, { once: true });
    try {
      element.currentTime = clamped;
    } catch {
      element.removeEventListener('seeked', onSeeked);
      finish();
      return;
    }
    // Safety: browsers occasionally don't fire `seeked` for sub-frame seeks.
    window.setTimeout(() => {
      element.removeEventListener('seeked', onSeeked);
      finish();
    }, SEEKED_TIMEOUT_MS);
  });
}

/**
 * Temporarily mute the element, perform {@link seekWithDriftCheck}, then
 * restore the previous volume. Prevents a brief "bleed" of audio from the
 * previous position while the playhead is moving between sentences.
 */
export async function mutedTransition(
  element: HTMLMediaElement,
  target: number,
): Promise<void> {
  const previousVolume = element.volume;
  const previousMuted = element.muted;
  try {
    element.muted = true;
  } catch {
    // Some autoplay-restricted contexts forbid muted toggles; ignore.
  }
  try {
    await seekWithDriftCheck(element, target);
  } finally {
    try {
      element.muted = previousMuted;
      element.volume = previousVolume;
    } catch {
      // Ignore — the user can always fix volume manually.
    }
  }
}
