import { useMemo, useState } from 'react';
import { prefersNativeEmojiFlags, twemojiSvgUrlForEmoji } from '../utils/emojiIcons';

type Props = {
  emoji: string | null | undefined;
  className?: string;
  title?: string;
  ariaLabel?: string;
};

export function EmojiIcon({ emoji, className, title, ariaLabel }: Props) {
  const trimmed = (emoji ?? '').trim();
  const [fallbackToText, setFallbackToText] = useState(false);
  const shouldRenderNative = prefersNativeEmojiFlags();
  const twemojiUrl = useMemo(() => {
    if (!trimmed) {
      return null;
    }
    return twemojiSvgUrlForEmoji(trimmed);
  }, [trimmed]);

  if (!trimmed) {
    return null;
  }

  const resolvedClassName = ['emoji-icon', className].filter(Boolean).join(' ');
  const accessibilityProps = ariaLabel
    ? ({ role: 'img', 'aria-label': ariaLabel } as const)
    : ({ 'aria-hidden': true } as const);

  if (shouldRenderNative || !twemojiUrl || fallbackToText) {
    return (
      <span className={resolvedClassName} title={title} {...accessibilityProps}>
        {trimmed}
      </span>
    );
  }

  return (
    <span className={resolvedClassName} title={title} {...accessibilityProps}>
      <img
        className="emoji-icon__img"
        src={twemojiUrl}
        alt=""
        aria-hidden="true"
        loading="lazy"
        decoding="async"
        onError={() => setFallbackToText(true)}
      />
    </span>
  );
}

export default EmojiIcon;

