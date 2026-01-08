import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { InteractiveTextTheme } from '../../types/interactiveTextTheme';
import { rgbaFromHex } from './utils';

type InteractiveTextVisualsInput = {
  isFullscreen: boolean;
  fontScale: number;
  theme: InteractiveTextTheme | null;
  backgroundOpacityPercent: number;
  sentenceCardOpacityPercent: number;
  infoGlyph: string | null;
  infoTitle: string | null;
  infoMeta: string | null;
  infoCoverUrl: string | null;
  infoCoverSecondaryUrl: string | null;
  infoCoverAltText: string | null;
  infoCoverVariant: 'book' | 'subtitles' | 'video' | 'youtube' | 'nas' | 'dub' | 'job' | null;
  bookTitle: string | null;
  bookAuthor: string | null;
  bookYear: string | null;
  bookGenre: string | null;
  bookCoverUrl: string | null;
  bookCoverAltText: string | null;
};

type InteractiveTextVisualsResult = {
  bodyStyle: CSSProperties;
  safeInfoGlyph: string;
  hasChannelBug: boolean;
  safeInfoTitle: string;
  safeInfoMeta: string;
  showInfoHeader: boolean;
  showTextBadge: boolean;
  showCoverArt: boolean;
  showSecondaryCover: boolean;
  resolvedCoverUrl: string | null;
  resolvedSecondaryCoverUrl: string | null;
  resolvedInfoCoverVariant: 'book' | 'subtitles' | 'video' | 'youtube' | 'nas' | 'dub' | 'job';
  coverAltText: string;
  handleCoverError: () => void;
  handleSecondaryCoverError: () => void;
};

const formatRem = (value: number) => `${Math.round(value * 1000) / 1000}rem`;

export function useInteractiveTextVisuals({
  isFullscreen,
  fontScale,
  theme,
  backgroundOpacityPercent,
  sentenceCardOpacityPercent,
  infoGlyph,
  infoTitle,
  infoMeta,
  infoCoverUrl,
  infoCoverSecondaryUrl,
  infoCoverAltText,
  infoCoverVariant,
  bookTitle,
  bookAuthor,
  bookYear,
  bookGenre,
  bookCoverUrl,
  bookCoverAltText,
}: InteractiveTextVisualsInput): InteractiveTextVisualsResult {
  const safeBookTitle = typeof bookTitle === 'string' ? bookTitle.trim() : '';
  const safeBookMeta = useMemo(() => {
    const parts: string[] = [];
    if (typeof bookAuthor === 'string' && bookAuthor.trim()) {
      parts.push(bookAuthor.trim());
    }
    if (typeof bookYear === 'string' && bookYear.trim()) {
      parts.push(bookYear.trim());
    }
    if (typeof bookGenre === 'string' && bookGenre.trim()) {
      parts.push(bookGenre.trim());
    }
    return parts.join(' · ');
  }, [bookAuthor, bookGenre, bookYear]);
  const safeInfoTitle = useMemo(() => {
    const trimmed = typeof infoTitle === 'string' ? infoTitle.trim() : '';
    if (trimmed) {
      return trimmed;
    }
    return safeBookTitle;
  }, [infoTitle, safeBookTitle]);
  const safeInfoMeta = useMemo(() => {
    const trimmed = typeof infoMeta === 'string' ? infoMeta.trim() : '';
    if (trimmed) {
      return trimmed;
    }
    return safeBookMeta;
  }, [infoMeta, safeBookMeta]);
  const safeFontScale = useMemo(() => {
    if (!Number.isFinite(fontScale) || fontScale <= 0) {
      return 1;
    }
    const clamped = Math.min(Math.max(fontScale, 0.5), 3);
    return Math.round(clamped * 100) / 100;
  }, [fontScale]);
  const safeBackgroundOpacity = useMemo(() => {
    const raw = Number(backgroundOpacityPercent);
    if (!Number.isFinite(raw)) {
      return 100;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  }, [backgroundOpacityPercent]);
  const safeSentenceCardOpacity = useMemo(() => {
    const raw = Number(sentenceCardOpacityPercent);
    if (!Number.isFinite(raw)) {
      return 100;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  }, [sentenceCardOpacityPercent]);
  const bodyStyle = useMemo<CSSProperties>(() => {
    const baseSentenceFont = (isFullscreen ? 1.32 : 1.08) * safeFontScale;
    const activeSentenceFont = (isFullscreen ? 1.56 : 1.28) * safeFontScale;
    const style: Record<string, string | number> = {
      '--interactive-font-scale': safeFontScale,
      '--tp-sentence-font-size': formatRem(baseSentenceFont),
      '--tp-sentence-active-font-size': formatRem(activeSentenceFont),
    };

    if (theme) {
      const alpha = safeBackgroundOpacity / 100;
      const resolvedBackground = rgbaFromHex(theme.background, alpha) ?? theme.background;
      style['--interactive-bg'] = resolvedBackground;
      style['--interactive-color-original'] = theme.original;
      style['--interactive-color-original-active'] = theme.originalActive;
      style['--interactive-color-translation'] = theme.translation;
      style['--interactive-color-transliteration'] = theme.transliteration;

      const originalMuted = rgbaFromHex(theme.original, 0.75);
      if (originalMuted) {
        style['--interactive-color-original-muted'] = originalMuted;
      }

      const highlightStrong = rgbaFromHex(theme.highlight, 0.85);
      const highlightSoft = rgbaFromHex(theme.highlight, 0.3);
      const highlightVerySoft = rgbaFromHex(theme.highlight, 0.2);
      const highlightSentenceBg = rgbaFromHex(theme.highlight, 0.45);
      const highlightOutline = rgbaFromHex(theme.highlight, 0.35);

      if (highlightStrong) {
        style['--interactive-highlight-strong'] = highlightStrong;
      }
      if (highlightSoft) {
        style['--interactive-highlight-soft'] = highlightSoft;
      }
      if (highlightVerySoft) {
        style['--interactive-highlight-very-soft'] = highlightVerySoft;
      }
      if (highlightSentenceBg) {
        style['--interactive-highlight-sentence-bg'] = highlightSentenceBg;
      }
      if (highlightOutline) {
        style['--interactive-highlight-outline'] = highlightOutline;
      }

      style['--tp-bg'] = resolvedBackground;
      style['--tp-original'] = theme.original;
      style['--tp-translit'] = theme.transliteration;
      style['--tp-translation'] = theme.translation;
      style['--tp-progress'] = theme.highlight;

      const cardScale = safeSentenceCardOpacity / 100;
      const sentenceBg = rgbaFromHex(theme.highlight, 0.06 * cardScale);
      const sentenceActiveBg = rgbaFromHex(theme.highlight, 0.16 * cardScale);
      const sentenceShadowColor = rgbaFromHex(theme.highlight, 0.22 * cardScale);
      if (sentenceBg) {
        style['--tp-sentence-bg'] = sentenceBg;
      }
      if (sentenceActiveBg) {
        style['--tp-sentence-active-bg'] = sentenceActiveBg;
      }
      if (sentenceShadowColor) {
        style['--tp-sentence-active-shadow'] = `0 6px 26px ${sentenceShadowColor}`;
      } else if (cardScale <= 0.01) {
        style['--tp-sentence-active-shadow'] = 'none';
      }
    }

    return style as CSSProperties;
  }, [isFullscreen, safeBackgroundOpacity, safeFontScale, safeSentenceCardOpacity, theme]);

  const safeInfoGlyph = useMemo(() => {
    if (typeof infoGlyph !== 'string') {
      return 'JOB';
    }
    const trimmed = infoGlyph.trim();
    return trimmed ? trimmed : 'JOB';
  }, [infoGlyph]);
  const hasChannelBug = typeof infoGlyph === 'string' && infoGlyph.trim().length > 0;

  const resolvedCoverUrlFromProps = useMemo(() => {
    const primary = typeof infoCoverUrl === 'string' ? infoCoverUrl.trim() : '';
    if (primary) {
      return primary;
    }
    const legacy = typeof bookCoverUrl === 'string' ? bookCoverUrl.trim() : '';
    return legacy || null;
  }, [bookCoverUrl, infoCoverUrl]);
  const resolvedSecondaryCoverUrlFromProps = useMemo(() => {
    const secondary = typeof infoCoverSecondaryUrl === 'string' ? infoCoverSecondaryUrl.trim() : '';
    return secondary || null;
  }, [infoCoverSecondaryUrl]);
  const [viewportCoverFailed, setViewportCoverFailed] = useState(false);
  const [viewportSecondaryCoverFailed, setViewportSecondaryCoverFailed] = useState(false);
  useEffect(() => {
    setViewportCoverFailed(false);
  }, [resolvedCoverUrlFromProps]);
  useEffect(() => {
    setViewportSecondaryCoverFailed(false);
  }, [resolvedSecondaryCoverUrlFromProps]);
  const resolvedCoverUrl = viewportCoverFailed ? null : resolvedCoverUrlFromProps;
  const resolvedSecondaryCoverUrl = viewportSecondaryCoverFailed ? null : resolvedSecondaryCoverUrlFromProps;
  const showSecondaryCover =
    Boolean(resolvedCoverUrl) && Boolean(resolvedSecondaryCoverUrl) && resolvedSecondaryCoverUrl !== resolvedCoverUrl;
  const showCoverArt = Boolean(resolvedCoverUrl);
  const showTextBadge = Boolean(safeInfoTitle || safeInfoMeta);
  const showInfoHeader = hasChannelBug || showCoverArt || showTextBadge;

  const resolvedInfoCoverVariant = useMemo(() => {
    const candidate = typeof infoCoverVariant === 'string' ? infoCoverVariant.trim().toLowerCase() : '';
    if (
      candidate === 'book' ||
      candidate === 'subtitles' ||
      candidate === 'video' ||
      candidate === 'youtube' ||
      candidate === 'nas' ||
      candidate === 'dub' ||
      candidate === 'job'
    ) {
      return candidate;
    }

    const glyph = safeInfoGlyph.trim().toLowerCase();
    if (glyph === 'bk' || glyph === 'book') {
      return 'book';
    }
    if (glyph === 'sub' || glyph === 'subtitle' || glyph === 'subtitles' || glyph === 'cc') {
      return 'subtitles';
    }
    if (glyph === 'yt' || glyph === 'youtube') {
      return 'youtube';
    }
    if (glyph === 'nas') {
      return 'nas';
    }
    if (glyph === 'dub') {
      return 'dub';
    }
    if (glyph === 'tv' || glyph === 'vid' || glyph === 'video') {
      return 'video';
    }
    return 'job';
  }, [infoCoverVariant, safeInfoGlyph]);

  const coverAltText =
    (typeof infoCoverAltText === 'string' && infoCoverAltText.trim() ? infoCoverAltText.trim() : null) ??
    (typeof bookCoverAltText === 'string' && bookCoverAltText.trim() ? bookCoverAltText.trim() : null) ??
    (safeInfoTitle ? `Cover for ${safeInfoTitle}` : 'Cover');

  return {
    bodyStyle,
    safeInfoGlyph,
    hasChannelBug,
    safeInfoTitle,
    safeInfoMeta,
    showInfoHeader,
    showTextBadge,
    showCoverArt,
    showSecondaryCover,
    resolvedCoverUrl,
    resolvedSecondaryCoverUrl,
    resolvedInfoCoverVariant,
    coverAltText,
    handleCoverError: () => setViewportCoverFailed(true),
    handleSecondaryCoverError: () => setViewportSecondaryCoverFailed(true),
  };
}
