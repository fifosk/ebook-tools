import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SleepTimerControl } from '../SleepTimerControl';

describe('SleepTimerControl', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-25T20:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts a countdown and expires once', () => {
    const onExpire = vi.fn();

    render(<SleepTimerControl onExpire={onExpire} />);

    fireEvent.click(screen.getByRole('button', { name: /set sleep timer/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: '5m' }));

    expect(screen.getByRole('button', { name: /5:00 remaining/i })).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(299_000);
    });
    expect(onExpire).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(onExpire).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /set sleep timer/i })).toBeInTheDocument();
  });

  it('cancels an active countdown when reset key changes', () => {
    const onExpire = vi.fn();
    const { rerender } = render(<SleepTimerControl onExpire={onExpire} resetKey="job-a" />);

    fireEvent.click(screen.getByRole('button', { name: /set sleep timer/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: '5m' }));

    rerender(<SleepTimerControl onExpire={onExpire} resetKey="job-b" />);

    act(() => {
      vi.advanceTimersByTime(300_000);
    });
    expect(onExpire).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /set sleep timer/i })).toBeInTheDocument();
  });
});
