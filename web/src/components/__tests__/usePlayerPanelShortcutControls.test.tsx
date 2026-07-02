import { act, render, renderHook, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MyLinguistProvider } from '../../context/MyLinguistProvider';
import { DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT } from '../player-panel/constants';
import { usePlayerPanelShortcutControls } from '../player-panel/usePlayerPanelShortcutControls';

type HookArgs = Parameters<typeof usePlayerPanelShortcutControls>[0];

function args(overrides: Partial<HookArgs> = {}): HookArgs {
  return {
    linguistEnabled: true,
    canToggleOriginalAudio: true,
    onToggleOriginalAudio: vi.fn(),
    canToggleTranslationAudio: true,
    onToggleTranslationAudio: vi.fn(),
    onToggleCueLayer: vi.fn(),
    onToggleReadingBed: vi.fn(),
    onToggleFullscreen: vi.fn(),
    onTogglePlayback: vi.fn(),
    onNavigate: vi.fn(),
    adjustTranslationSpeed: vi.fn(),
    adjustFontScale: vi.fn(),
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  return <MyLinguistProvider>{children}</MyLinguistProvider>;
}

function pressKey(init: KeyboardEventInit) {
  window.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, ...init }));
}

describe('usePlayerPanelShortcutControls', () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it('owns the shortcut help overlay state around the shared keyboard hook', () => {
    const { result } = renderHook(() => usePlayerPanelShortcutControls(args()), { wrapper });
    const view = render(<>{result.current.shortcutHelpOverlay}</>);

    expect(screen.queryByRole('dialog', { name: /keyboard shortcuts/i })).toBeNull();

    act(() => {
      pressKey({ key: 'h', code: 'KeyH' });
    });
    view.rerender(<>{result.current.shortcutHelpOverlay}</>);

    expect(screen.getByRole('dialog', { name: /keyboard shortcuts/i })).toBeInTheDocument();
    expect(screen.getByText(/Toggle MyLinguist chat window/i)).toBeInTheDocument();

    act(() => {
      pressKey({ key: 'Escape', code: 'Escape' });
    });
    view.rerender(<>{result.current.shortcutHelpOverlay}</>);

    expect(screen.queryByRole('dialog', { name: /keyboard shortcuts/i })).toBeNull();
  });

  it('keeps MyLinguist shortcuts and help rows disabled when the feature is unavailable', () => {
    const { result } = renderHook(
      () => usePlayerPanelShortcutControls(args({ linguistEnabled: false })),
      { wrapper },
    );
    const initialScale = result.current.baseFontScalePercent;
    const view = render(<>{result.current.shortcutHelpOverlay}</>);

    act(() => {
      pressKey({ key: '+', code: 'Equal', ctrlKey: true });
      pressKey({ key: 'h', code: 'KeyH' });
    });
    view.rerender(<>{result.current.shortcutHelpOverlay}</>);

    expect(result.current.baseFontScalePercent).toBe(initialScale);
    expect(screen.queryByText(/Toggle MyLinguist chat window/i)).toBeNull();
  });

  it('exposes the shared MyLinguist font scale reset used by layout reset', () => {
    const { result } = renderHook(() => usePlayerPanelShortcutControls(args()), { wrapper });

    act(() => {
      result.current.setBaseFontScalePercent(155);
    });
    expect(result.current.baseFontScalePercent).toBe(155);

    act(() => {
      result.current.resetMyLinguistFontScale();
    });
    expect(result.current.baseFontScalePercent).toBe(DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT);
  });
});
