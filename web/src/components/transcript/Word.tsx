import { memo, useCallback } from 'react';
import type { WordToken } from '../../types/timing';

type WordStatus = 'prev' | 'now' | 'next';

export interface WordProps {
  token: WordToken;
  status: WordStatus;
  onClick?: (token: WordToken) => void;
}

function WordComponent({ token, status, onClick }: WordProps) {
  const handleClick = useCallback(() => {
    if (!onClick) {
      return;
    }
    onClick(token);
  }, [onClick, token]);

  const className = [
    'transcript-word',
    status === 'prev' ? 'wh-prev' : null,
    status === 'now' ? 'wh-now' : null,
    status === 'next' ? 'wh-next' : null,
    token.lane === 'orig' ? 'lane-orig' : 'lane-tran',
    token.text === '' ? 'word-pause' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const displayText = token.text && token.text.trim().length > 0 ? token.text : '•';
  const accessibleText = token.text && token.text.trim().length > 0 ? token.text : 'Pause';

  return (
    <button
      type="button"
      className={className}
      onClick={handleClick}
      aria-current={status === 'now' ? 'true' : undefined}
      aria-label={accessibleText}
      data-token-id={token.id}
      data-lane={token.lane}
    >
      {displayText}
    </button>
  );
}

export const Word = memo(WordComponent);

export default Word;
