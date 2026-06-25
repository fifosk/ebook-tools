import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const SLEEP_TIMER_OPTIONS = [5, 15, 30, 45] as const;
const SECOND_MS = 1000;

type SleepTimerControlProps = {
  onExpire: () => void;
  className?: string;
  buttonClassName?: string;
  panelClassName?: string;
  resetKey?: string | number | null;
};

function formatRemaining(totalSeconds: number): string {
  const clamped = Math.max(0, Math.ceil(totalSeconds));
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

export function SleepTimerControl({
  onExpire,
  className,
  buttonClassName = 'player-panel__nav-button player-panel__nav-button--sleep-timer',
  panelClassName = 'sleep-timer-control__menu',
  resetKey = null,
}: SleepTimerControlProps) {
  const [open, setOpen] = useState(false);
  const [deadline, setDeadline] = useState<number | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const expireRef = useRef(onExpire);

  useEffect(() => {
    expireRef.current = onExpire;
  }, [onExpire]);

  const cancel = useCallback(() => {
    setDeadline(null);
    setRemainingSeconds(0);
    setOpen(false);
  }, []);

  const start = useCallback((minutes: number) => {
    const nextDeadline = Date.now() + minutes * 60 * SECOND_MS;
    setDeadline(nextDeadline);
    setRemainingSeconds(minutes * 60);
    setOpen(false);
  }, []);

  useEffect(() => {
    cancel();
  }, [cancel, resetKey]);

  useEffect(() => {
    if (deadline === null) {
      return undefined;
    }

    const update = () => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / SECOND_MS));
      setRemainingSeconds(remaining);
      if (remaining <= 0) {
        setDeadline(null);
        setOpen(false);
        expireRef.current();
      }
    };

    update();
    const interval = window.setInterval(update, SECOND_MS);
    return () => window.clearInterval(interval);
  }, [deadline]);

  const active = deadline !== null && remainingSeconds > 0;
  const label = active ? `Sleep timer ${formatRemaining(remainingSeconds)} remaining` : 'Set sleep timer';
  const display = active ? formatRemaining(remainingSeconds) : null;
  const rootClassName = useMemo(
    () => ['sleep-timer-control', className].filter(Boolean).join(' '),
    [className],
  );

  return (
    <div className={rootClassName}>
      <button
        type="button"
        className={buttonClassName}
        aria-label={label}
        aria-expanded={open}
        aria-haspopup="menu"
        title={label}
        onClick={() => setOpen((value) => !value)}
      >
        <span aria-hidden="true" className="sleep-timer-control__icon">
          ⏱
        </span>
        {display ? (
          <span aria-hidden="true" className="sleep-timer-control__remaining">
            {display}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className={panelClassName} role="menu" aria-label="Sleep timer options">
          {SLEEP_TIMER_OPTIONS.map((minutes) => (
            <button
              key={minutes}
              type="button"
              role="menuitem"
              className="sleep-timer-control__option"
              onClick={() => start(minutes)}
            >
              {minutes}m
            </button>
          ))}
          {active ? (
            <button
              type="button"
              role="menuitem"
              className="sleep-timer-control__option sleep-timer-control__option--cancel"
              onClick={cancel}
            >
              Cancel
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export { formatRemaining as formatSleepTimerRemaining };
