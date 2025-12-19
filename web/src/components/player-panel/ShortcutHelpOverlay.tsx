import { useEffect, useRef } from 'react';

type ShortcutHelpOverlayProps = {
  isOpen: boolean;
  onClose: () => void;
  canToggleOriginalAudio: boolean;
};

export function ShortcutHelpOverlay({ isOpen, onClose, canToggleOriginalAudio }: ShortcutHelpOverlayProps) {
  const shortcutHelpCardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    shortcutHelpCardRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) {
        return;
      }
      if (event.key === 'Escape' || event.key === 'Esc') {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.altKey || event.metaKey || event.ctrlKey) {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
          event.preventDefault();
          event.stopPropagation();
        }
        return;
      }
      if (event.shiftKey) {
        return;
      }
      if (event.key?.toLowerCase() === 'h') {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key === 'Tab') {
        return;
      }
      event.stopPropagation();
      const key = event.key?.toLowerCase();
      if (
        event.code === 'Space' ||
        event.key === ' ' ||
        event.key === 'ArrowLeft' ||
        event.key === 'ArrowRight' ||
        event.key === 'ArrowUp' ||
        event.key === 'ArrowDown' ||
        key === 'f' ||
        key === 'r' ||
        key === 'm' ||
        key === 'l' ||
        key === 'o' ||
        key === 'i' ||
        key === 'p' ||
        key === 'g' ||
        key === 'd' ||
        key === '+' ||
        key === '=' ||
        key === '-' ||
        key === '_'
      ) {
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="player-panel__shortcut-help-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div
        className="player-panel__shortcut-help-backdrop"
        onPointerDown={onClose}
      />
      <div
        className="player-panel__shortcut-help-card"
        ref={shortcutHelpCardRef}
        tabIndex={-1}
      >
        <header className="player-panel__shortcut-help-header">
          <h2 className="player-panel__shortcut-help-title">Keyboard shortcuts</h2>
          <button
            type="button"
            className="player-panel__shortcut-help-close"
            onClick={onClose}
          >
            Close
          </button>
        </header>
        <div className="player-panel__shortcut-help-body">
          <section className="player-panel__shortcut-help-section" aria-label="Playback and navigation">
            <h3>Playback &amp; navigation</h3>
            <ul>
              <li>
                <kbd>Space</kbd> Play/pause active track
              </li>
              <li>
                <kbd>←</kbd>/<kbd>→</kbd> Previous/next chunk (keeps play state)
              </li>
              <li>
                <kbd>M</kbd> Toggle background music
              </li>
              <li>
                <kbd>F</kbd> Toggle fullscreen
              </li>
              <li>
                <kbd>R</kbd> Toggle image reel
              </li>
            </ul>
          </section>
          <section className="player-panel__shortcut-help-section" aria-label="Text display">
            <h3>Text display</h3>
            <ul>
              <li>
                <kbd>O</kbd> Toggle original line
              </li>
              {canToggleOriginalAudio ? (
                <li>
                  <kbd>Shift</kbd>+<kbd>O</kbd> Toggle original audio
                </li>
              ) : null}
              <li>
                <kbd>I</kbd> Toggle transliteration line
              </li>
              <li>
                <kbd>P</kbd> Toggle translation line
              </li>
              <li>
                <kbd>+</kbd>/<kbd>-</kbd> Increase/decrease font size
              </li>
              <li>
                <kbd>↑</kbd>/<kbd>↓</kbd> Translation speed up/down
              </li>
            </ul>
          </section>
          <section className="player-panel__shortcut-help-section" aria-label="MyLinguist">
            <h3>MyLinguist</h3>
            <ul>
              <li>
                <kbd>L</kbd> Toggle MyLinguist chat window
              </li>
              <li>
                <kbd>Ctrl</kbd>+<kbd>+</kbd>/<kbd>Ctrl</kbd>+<kbd>-</kbd> Increase/decrease MyLinguist font size
              </li>
              <li>
                <kbd>Alt</kbd>+<kbd>←</kbd>/<kbd>Alt</kbd>+<kbd>→</kbd> Previous/next word (stays on current lane)
              </li>
              <li>
                <kbd>Esc</kbd> Close the bubble
              </li>
              <li>
                <kbd>Enter</kbd> or <kbd>Space</kbd> (on focused word) Seek to that word
              </li>
            </ul>
          </section>
          <section className="player-panel__shortcut-help-section" aria-label="Fullscreen controls">
            <h3>Fullscreen</h3>
            <ul>
              <li>
                <kbd>Shift</kbd>+<kbd>H</kbd> Collapse/expand fullscreen controls
              </li>
            </ul>
          </section>
          <section className="player-panel__shortcut-help-section" aria-label="Help and debug">
            <h3>Help &amp; debug</h3>
            <ul>
              <li>
                <kbd>H</kbd> Toggle this help overlay
              </li>
              <li>
                <kbd>Esc</kbd> Close dialogs/overlays
              </li>
              <li>
                <kbd>G</kbd>/<kbd>P</kbd>/<kbd>D</kbd> Toggle word-sync debug overlays (dev)
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
