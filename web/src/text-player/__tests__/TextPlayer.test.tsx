import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import TextPlayer, { type TextPlayerSentence } from '../TextPlayer';

const buildSentence = (overrides: Partial<TextPlayerSentence>): TextPlayerSentence => ({
  id: 's1',
  index: 0,
  state: 'active',
  sentenceNumber: 1,
  variants: [],
  ...overrides,
});

describe('TextPlayer', () => {
  it('renders tokens with appropriate highlight classes', () => {
    const sentences: TextPlayerSentence[] = [
      buildSentence({
        variants: [
          {
            label: 'Original',
            tokens: ['Alpha', 'beta', 'gamma'],
            revealedCount: 2,
            currentIndex: 1,
            baseClass: 'original',
          },
          {
            label: 'Translation',
            tokens: ['Uno', 'dos', 'tres'],
            revealedCount: 1,
            currentIndex: 0,
            baseClass: 'translation',
          },
        ],
      }),
    ];

    render(<TextPlayer sentences={sentences} />);

    expect(screen.getByText('Alpha').className).toMatch(/wordOriginalPast/);
    expect(screen.getByText('beta').className).toMatch(/wordOriginalCurrent/);
    expect(screen.getByText('gamma').className).toMatch(/wordOriginalFuture/);

    expect(screen.getByText('Uno').className).toMatch(/wordTranslationCurrent/);
    expect(screen.getByText('tres').className).toMatch(/wordTranslationFuture/);
  });

  it('invokes seek callback when a token is clicked', () => {
    const handleSeek = vi.fn();
    const sentences: TextPlayerSentence[] = [
      buildSentence({
        variants: [
          {
            label: 'Original',
            tokens: ['Alpha', 'beta'],
            revealedCount: 2,
            currentIndex: 1,
            baseClass: 'original',
            seekTimes: [0.5, 1.1],
          },
        ],
      }),
    ];

    render(<TextPlayer sentences={sentences} onSeek={handleSeek} />);

    fireEvent.click(screen.getByText('Alpha'));
    expect(handleSeek).toHaveBeenCalledWith(0.5);
  });
});
