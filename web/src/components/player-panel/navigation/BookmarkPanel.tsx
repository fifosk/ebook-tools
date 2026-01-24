import { useEffect, useRef, useState } from 'react';
import type { BookmarkProps } from './types';

/**
 * Bookmark panel with dropdown menu for managing playback bookmarks.
 */
export function BookmarkPanel({
  showBookmarks = false,
  bookmarks = [],
  onAddBookmark,
  onJumpToBookmark,
  onRemoveBookmark,
}: BookmarkProps) {
  const [bookmarkMenuOpen, setBookmarkMenuOpen] = useState(false);
  const bookmarkPanelRef = useRef<HTMLDivElement | null>(null);
  const hasBookmarks = bookmarks.length > 0;

  const bookmarkButtonClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--bookmark',
    hasBookmarks ? 'player-panel__nav-button--bookmark-active' : null,
  ]
    .filter(Boolean)
    .join(' ');

  useEffect(() => {
    if (!bookmarkMenuOpen) {
      return;
    }
    const handleClick = (event: MouseEvent) => {
      if (!bookmarkPanelRef.current) {
        return;
      }
      if (!bookmarkPanelRef.current.contains(event.target as Node)) {
        setBookmarkMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setBookmarkMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [bookmarkMenuOpen]);

  if (!showBookmarks) {
    return null;
  }

  return (
    <div className="player-panel__bookmark" ref={bookmarkPanelRef}>
      <button
        type="button"
        className={bookmarkButtonClassName}
        onClick={() => setBookmarkMenuOpen((current) => !current)}
        aria-label="Bookmarks"
        aria-expanded={bookmarkMenuOpen}
        title="Bookmarks"
      >
        <span aria-hidden="true">🔖</span>
      </button>
      {bookmarkMenuOpen ? (
        <div className="player-panel__bookmark-panel" role="menu">
          <div className="player-panel__bookmark-header">
            <span className="player-panel__bookmark-title">Bookmarks</span>
            <button
              type="button"
              className="player-panel__bookmark-add"
              onClick={() => onAddBookmark?.()}
              disabled={!onAddBookmark}
              title="Add bookmark"
            >
              Add
            </button>
          </div>
          {bookmarks.length === 0 ? (
            <p className="player-panel__bookmark-empty">No bookmarks yet.</p>
          ) : (
            <ul className="player-panel__bookmark-list">
              {bookmarks.map((bookmark) => (
                <li key={bookmark.id} className="player-panel__bookmark-item">
                  <button
                    type="button"
                    className="player-panel__bookmark-jump"
                    onClick={() => {
                      onJumpToBookmark?.(bookmark);
                      setBookmarkMenuOpen(false);
                    }}
                    title={`Jump to ${bookmark.label}`}
                  >
                    {bookmark.label}
                  </button>
                  <button
                    type="button"
                    className="player-panel__bookmark-remove"
                    onClick={() => onRemoveBookmark?.(bookmark)}
                    aria-label={`Remove ${bookmark.label}`}
                    title={`Remove ${bookmark.label}`}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default BookmarkPanel;
