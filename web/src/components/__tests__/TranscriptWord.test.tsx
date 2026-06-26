import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Word from '../transcript/Word';
import type { WordToken } from '../../types/timing';

function token(overrides: Partial<WordToken> = {}): WordToken {
  return {
    id: 'word-1',
    text: 'Merhaba',
    t0: 1.2,
    t1: 1.6,
    lane: 'tran',
    segId: 'segment-1',
    ...overrides,
  };
}

describe('Transcript Word', () => {
  it('marks the active word for assistive technology', () => {
    render(<Word token={token()} status="now" />);

    expect(screen.getByRole('button', { name: 'Merhaba' })).toHaveAttribute('aria-current', 'true');
  });

  it('does not mark non-active words as current', () => {
    render(<Word token={token()} status="prev" />);

    expect(screen.getByRole('button', { name: 'Merhaba' })).not.toHaveAttribute('aria-current');
  });

  it('gives silent pause tokens an accessible name and remains clickable', () => {
    const onClick = vi.fn();
    const pause = token({ id: 'pause-1', text: '' });

    render(<Word token={pause} status="next" onClick={onClick} />);

    const button = screen.getByRole('button', { name: 'Pause' });
    expect(button).toHaveTextContent('•');

    fireEvent.click(button);

    expect(onClick).toHaveBeenCalledWith(pause);
  });
});
