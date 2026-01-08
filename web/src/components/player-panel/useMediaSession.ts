import { useEffect, useMemo } from 'react';

type SubtitleInfo = {
  title: string | null;
  meta: string | null;
  coverUrl: string | null;
  coverSecondaryUrl: string | null;
  coverAltText: string | null;
};

type UseMediaSessionActionsArgs = {
  inlineAudioSelection: string | null;
  onPlay: () => void;
  onPause: () => void;
  onTrackSkip: (direction: -1 | 1) => void;
  onSeekTo: (details: MediaSessionActionDetails) => void;
};

export function useMediaSessionActions({
  inlineAudioSelection,
  onPlay,
  onPause,
  onTrackSkip,
  onSeekTo,
}: UseMediaSessionActionsArgs): void {
  useEffect(() => {
    if (typeof navigator === 'undefined') {
      return;
    }
    const session = navigator.mediaSession;
    if (!session || typeof session.setActionHandler !== 'function') {
      return;
    }
    const setHandler = (action: MediaSessionAction, handler: MediaSessionActionHandler | null) => {
      try {
        session.setActionHandler(action, handler);
      } catch {
        // Ignore unsupported MediaSession actions.
      }
    };
    if (!inlineAudioSelection) {
      setHandler('play', null);
      setHandler('pause', null);
      setHandler('stop', null);
      setHandler('nexttrack', null);
      setHandler('previoustrack', null);
      setHandler('seekforward', null);
      setHandler('seekbackward', null);
      setHandler('seekto', null);
      return;
    }
    setHandler('play', () => {
      onPlay();
    });
    setHandler('pause', () => {
      onPause();
    });
    setHandler('stop', () => {
      onPause();
    });
    setHandler('nexttrack', () => {
      onTrackSkip(1);
    });
    setHandler('previoustrack', () => {
      onTrackSkip(-1);
    });
    setHandler('seekforward', () => {
      onTrackSkip(1);
    });
    setHandler('seekbackward', () => {
      onTrackSkip(-1);
    });
    setHandler('seekto', onSeekTo);
    return () => {
      setHandler('play', null);
      setHandler('pause', null);
      setHandler('stop', null);
      setHandler('nexttrack', null);
      setHandler('previoustrack', null);
      setHandler('seekforward', null);
      setHandler('seekbackward', null);
      setHandler('seekto', null);
    };
  }, [inlineAudioSelection, onPause, onPlay, onSeekTo, onTrackSkip]);
}

type UseMediaSessionMetadataArgs = {
  inlineAudioSelection: string | null;
  isActiveMediaPlaying: boolean;
  activeSentenceNumber: number | null;
  jobEndSentence: number | null;
  bookTitle: string | null;
  bookAuthor: string | null;
  subtitleInfo: SubtitleInfo;
  isSubtitleContext: boolean;
  displayCoverUrl: string | null;
  shouldShowCoverImage: boolean;
};

export function useMediaSessionMetadata({
  inlineAudioSelection,
  isActiveMediaPlaying,
  activeSentenceNumber,
  jobEndSentence,
  bookTitle,
  bookAuthor,
  subtitleInfo,
  isSubtitleContext,
  displayCoverUrl,
  shouldShowCoverImage,
}: UseMediaSessionMetadataArgs): void {
  const nowPlayingSentenceLabel = useMemo(() => {
    if (typeof activeSentenceNumber !== 'number' || !Number.isFinite(activeSentenceNumber)) {
      return null;
    }
    const current = Math.max(Math.trunc(activeSentenceNumber), 1);
    if (typeof jobEndSentence === 'number' && Number.isFinite(jobEndSentence) && jobEndSentence > 0) {
      const end = Math.max(Math.trunc(jobEndSentence), 1);
      return `Sentence ${Math.min(current, end)} of ${end}`;
    }
    return `Sentence ${current}`;
  }, [activeSentenceNumber, jobEndSentence]);
  const nowPlayingBaseTitle = useMemo(() => {
    if (isSubtitleContext) {
      const title = subtitleInfo.title?.trim();
      if (title) {
        return title;
      }
      const meta = subtitleInfo.meta?.trim();
      if (meta) {
        return meta;
      }
    }
    const title = bookTitle?.trim();
    return title || null;
  }, [bookTitle, isSubtitleContext, subtitleInfo.meta, subtitleInfo.title]);
  const nowPlayingTitle = useMemo(() => {
    const base = nowPlayingBaseTitle ?? 'Interactive Reader';
    if (nowPlayingSentenceLabel) {
      return `${base} · ${nowPlayingSentenceLabel}`;
    }
    return base;
  }, [nowPlayingBaseTitle, nowPlayingSentenceLabel]);
  const nowPlayingArtist = useMemo(() => {
    if (isSubtitleContext) {
      const meta = subtitleInfo.meta?.trim();
      return meta || null;
    }
    const author = bookAuthor?.trim();
    return author || null;
  }, [bookAuthor, isSubtitleContext, subtitleInfo.meta]);
  const nowPlayingAlbum = useMemo(() => {
    if (isSubtitleContext) {
      const title = subtitleInfo.title?.trim();
      return title || null;
    }
    const title = bookTitle?.trim();
    return title || null;
  }, [bookTitle, isSubtitleContext, subtitleInfo.title]);
  const nowPlayingCoverUrl = useMemo(() => {
    const candidate = isSubtitleContext
      ? subtitleInfo.coverUrl ?? subtitleInfo.coverSecondaryUrl ?? null
      : shouldShowCoverImage
        ? displayCoverUrl
        : null;
    if (!candidate) {
      return null;
    }
    if (typeof window === 'undefined') {
      return candidate;
    }
    try {
      return new URL(candidate, window.location.href).toString();
    } catch {
      return candidate;
    }
  }, [
    displayCoverUrl,
    isSubtitleContext,
    shouldShowCoverImage,
    subtitleInfo.coverSecondaryUrl,
    subtitleInfo.coverUrl,
  ]);

  useEffect(() => {
    if (typeof navigator === 'undefined' || typeof window === 'undefined') {
      return;
    }
    const session = navigator.mediaSession;
    if (!session) {
      return;
    }
    if (!inlineAudioSelection && !isActiveMediaPlaying) {
      try {
        session.metadata = null;
        session.playbackState = 'none';
      } catch {
        // Ignore metadata updates in unsupported environments.
      }
      return;
    }
    const metadata: MediaMetadataInit = {
      title: nowPlayingTitle,
    };
    if (nowPlayingArtist) {
      metadata.artist = nowPlayingArtist;
    }
    if (nowPlayingAlbum && nowPlayingAlbum !== nowPlayingTitle) {
      metadata.album = nowPlayingAlbum;
    }
    if (nowPlayingCoverUrl) {
      metadata.artwork = [
        { src: nowPlayingCoverUrl, sizes: '512x512' },
        { src: nowPlayingCoverUrl, sizes: '1024x1024' },
      ];
    }
    const Metadata = window.MediaMetadata;
    const applyMetadata = (payload: MediaMetadataInit) => {
      if (typeof Metadata === 'function') {
        session.metadata = new Metadata(payload);
        return;
      }
      session.metadata = payload as unknown as MediaMetadata;
    };
    try {
      applyMetadata(metadata);
    } catch {
      if (metadata.artwork) {
        const { artwork, ...fallback } = metadata;
        try {
          applyMetadata(fallback);
        } catch {
          try {
            session.metadata = null;
          } catch {
            // Ignore failures to clear metadata.
          }
        }
      }
    }
    try {
      session.playbackState = isActiveMediaPlaying ? 'playing' : 'paused';
    } catch {
      // Ignore unsupported playback state updates.
    }
  }, [
    inlineAudioSelection,
    isActiveMediaPlaying,
    nowPlayingAlbum,
    nowPlayingArtist,
    nowPlayingCoverUrl,
    nowPlayingSentenceLabel,
    nowPlayingTitle,
  ]);
}
