import { useEffect, useMemo, useState } from 'react';

export interface PlayerChannelBugProps {
  glyph: string;
  label?: string | null;
}

function formatTwoDigits(value: number): string {
  return Math.trunc(value).toString().padStart(2, '0');
}

type ChannelLogoVariant = 'book' | 'subtitles' | 'video' | 'youtube' | 'nas' | 'dub' | 'job';

function resolveVariant(glyph: string): ChannelLogoVariant {
  const normalized = glyph.trim().toLowerCase();
  switch (normalized) {
    case 'bk':
    case 'book':
      return 'book';
    case 'sub':
    case 'subs':
    case 'subtitle':
    case 'subtitles':
    case 'cc':
      return 'subtitles';
    case 'yt':
    case 'youtube':
      return 'youtube';
    case 'nas':
      return 'nas';
    case 'tv':
    case 'vid':
    case 'video':
      return 'video';
    case 'dub':
      return 'dub';
    default:
      return 'job';
  }
}

function renderLogoIcon(variant: ChannelLogoVariant) {
  switch (variant) {
    case 'book':
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <path
            d="M12 6.2c-1.9-1.3-4-1.9-6.4-1.9H4.9c-1.1 0-1.9.8-1.9 1.9v12.3c0 1 .8 1.9 1.9 1.9h.7c2.4 0 4.5.6 6.4 1.9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M12 6.2c1.9-1.3 4-1.9 6.4-1.9h.7c1.1 0 1.9.8 1.9 1.9v12.3c0 1-.8 1.9-1.9 1.9h-.7c-2.4 0-4.5.6-6.4 1.9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M12 6v16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'subtitles':
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <rect
            x="4.5"
            y="6.5"
            width="15"
            height="11"
            rx="2.3"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M7.5 11h9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="M7.5 14h6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'youtube':
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <path
            d="M7.6 8.3h8.8c1.4 0 2.6 1.1 2.6 2.6v2.2c0 1.4-1.1 2.6-2.6 2.6H7.6c-1.4 0-2.6-1.1-2.6-2.6V10.9c0-1.4 1.1-2.6 2.6-2.6Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path d="M11 10.6l4 2.1-4 2.1v-4.2Z" fill="currentColor" />
        </svg>
      );
    case 'nas':
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <path
            d="M6 6.8h12c.7 0 1.2.5 1.2 1.2v2.8c0 .7-.5 1.2-1.2 1.2H6c-.7 0-1.2-.5-1.2-1.2V8c0-.7.5-1.2 1.2-1.2Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M6 12.2h12c.7 0 1.2.5 1.2 1.2v2.8c0 .7-.5 1.2-1.2 1.2H6c-.7 0-1.2-.5-1.2-1.2v-2.8c0-.7.5-1.2 1.2-1.2Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path d="M16.2 9.2h.01" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          <path d="M16.2 14.6h.01" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      );
    case 'video':
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <rect
            x="4.5"
            y="6.5"
            width="15"
            height="11"
            rx="2.3"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M11 10.1l4.2 2.4-4.2 2.4v-4.8Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'dub':
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <path
            d="M12 3.8c1.4 0 2.6 1.1 2.6 2.6v6c0 1.4-1.1 2.6-2.6 2.6s-2.6-1.1-2.6-2.6v-6c0-1.4 1.1-2.6 2.6-2.6Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M7.5 11.9v.6c0 2.5 2 4.5 4.5 4.5s4.5-2 4.5-4.5v-.6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path d="M12 17v3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M9.5 20h5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      );
    default:
      return (
        <svg className="player-panel__channel-logo-icon" viewBox="0 0 24 24" role="img" focusable="false">
          <path
            d="M7 7.5h10l1.5 4.4V19c0 .7-.6 1.3-1.3 1.3H6.8c-.7 0-1.3-.6-1.3-1.3v-7.1L7 7.5Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M7.8 7.5l.9-2.2c.2-.6.8-1 1.4-1h3.8c.6 0 1.1.4 1.4 1l.9 2.2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
        </svg>
      );
  }
}

export default function PlayerChannelBug({ glyph, label = null }: PlayerChannelBugProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const interval = window.setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => {
      window.clearInterval(interval);
    };
  }, []);

  const time = useMemo(() => {
    return { hh: formatTwoDigits(now.getHours()), mm: formatTwoDigits(now.getMinutes()) };
  }, [now]);

  const variant = useMemo(() => resolveVariant(glyph), [glyph]);

  return (
    <div className="player-panel__channel-bug" aria-hidden="true">
      <span className="player-panel__channel-logo" title={label ?? undefined} data-variant={variant}>
        {renderLogoIcon(variant)}
      </span>
      <span className="player-panel__channel-clock" title={label ?? undefined}>
        <span className="player-panel__channel-clock-hours">{time.hh}</span>
        <span className="player-panel__channel-clock-colon" aria-hidden="true">
          :
        </span>
        <span className="player-panel__channel-clock-minutes">{time.mm}</span>
      </span>
    </div>
  );
}
