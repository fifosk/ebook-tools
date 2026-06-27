import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StackedAdvancedControls } from '../player-panel/navigation/StackedAdvancedControls';

function renderControls(overrides: Partial<Parameters<typeof StackedAdvancedControls>[0]> = {}) {
  const onTranslationSpeedChange = vi.fn();
  const onSentenceJumpChange = vi.fn();
  const onSentenceJumpSubmit = vi.fn();
  const onFontScaleChange = vi.fn();

  render(
    <StackedAdvancedControls
      showAdvancedControls
      controlsLayout="stacked"
      showTranslationSpeed
      translationSpeed={1}
      translationSpeedMin={0.5}
      translationSpeedMax={1.5}
      translationSpeedStep={0.1}
      onTranslationSpeedChange={onTranslationSpeedChange}
      onSentenceJumpChange={onSentenceJumpChange}
      onSentenceJumpSubmit={onSentenceJumpSubmit}
      onFontScaleChange={onFontScaleChange}
      {...overrides}
    />,
  );

  return {
    onTranslationSpeedChange,
    onSentenceJumpChange,
    onSentenceJumpSubmit,
    onFontScaleChange,
  };
}

describe('StackedAdvancedControls', () => {
  it('renders stacked speed controls and reports numeric speed changes', () => {
    const { onTranslationSpeedChange } = renderControls();

    const speed = screen.getByRole('slider', { name: 'Speed' });
    expect(speed).toHaveAttribute('aria-valuetext', '1×');

    fireEvent.change(speed, { target: { value: '1.2' } });
    expect(onTranslationSpeedChange).toHaveBeenCalledWith(1.2);
  });

  it('submits sentence jumps on Enter and exposes range or error metadata', () => {
    const { onSentenceJumpChange, onSentenceJumpSubmit } = renderControls({
      showSentenceJump: true,
      sentenceJumpInputId: 'sentence-jump',
      sentenceJumpValue: '12',
      sentenceJumpMin: 1,
      sentenceJumpMax: 40,
      sentenceJumpPlaceholder: '1-40',
    });

    const input = screen.getByRole('spinbutton');
    expect(input).toHaveAttribute('aria-describedby', 'sentence-jump-range');
    expect(screen.getByText('Range 1–40')).toBeInTheDocument();

    fireEvent.change(input, { target: { value: '24' } });
    expect(onSentenceJumpChange).toHaveBeenCalledWith('24');

    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSentenceJumpSubmit).toHaveBeenCalledTimes(1);
  });

  it('disables subtitle background opacity when subtitle playback is unavailable', () => {
    renderControls({
      showSubtitleBackgroundOpacity: true,
      subtitleBackgroundOpacityPercent: 45,
      disableSubtitleToggle: true,
      subtitlesEnabled: false,
    });

    expect(screen.getByRole('slider', { name: 'Subtitle background opacity' })).toBeDisabled();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('hides all stacked controls for compact layouts or closed advanced groups', () => {
    const { rerender } = render(
      <StackedAdvancedControls
        showAdvancedControls
        controlsLayout="compact"
        showTranslationSpeed
        translationSpeed={1}
        translationSpeedMin={0.5}
        translationSpeedMax={1.5}
        translationSpeedStep={0.1}
        onTranslationSpeedChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole('slider', { name: 'Speed' })).not.toBeInTheDocument();

    rerender(
      <StackedAdvancedControls
        showAdvancedControls={false}
        controlsLayout="stacked"
        showTranslationSpeed
        translationSpeed={1}
        translationSpeedMin={0.5}
        translationSpeedMax={1.5}
        translationSpeedStep={0.1}
        onTranslationSpeedChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole('slider', { name: 'Speed' })).not.toBeInTheDocument();
  });

  it('clamps font labels while preserving unclamped input values', () => {
    const { onFontScaleChange } = renderControls({
      showFontScale: true,
      fontScalePercent: 180,
      fontScaleMin: 80,
      fontScaleMax: 160,
      fontScaleStep: 5,
    });

    const font = screen.getByRole('slider', { name: 'Adjust font size' });
    expect(font).toHaveAttribute('aria-valuetext', '160%');
    expect(screen.getByText('160%')).toBeInTheDocument();

    fireEvent.change(font, { target: { value: '120' } });
    expect(onFontScaleChange).toHaveBeenCalledWith(120);
  });
});
