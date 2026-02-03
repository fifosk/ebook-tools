import type { LookupCacheAudioRef, TrackTimingPayload, WordTiming } from '../../api/dtos';
import type { WordIndex } from '../../lib/timing/wordSync';
import type { TextPlayerSentence, TextPlayerVariantKind } from '../../text-player/TextPlayer';

export type SentenceFragment = {
  index: number;
  text: string;
  wordCount: number;
  parts: Array<{ content: string; isWord: boolean }>;
  translation: string | null;
  transliteration: string | null;
  weight: number;
};

export type ParagraphFragment = {
  id: string;
  sentences: SentenceFragment[];
};

export type WordSyncLane = WordTiming['lang'];

export type WordSyncRenderableToken = WordTiming & {
  displayText: string;
};

export type WordSyncSentence = {
  id: string;
  sentenceId: number;
  tokens: Record<WordSyncLane, WordSyncRenderableToken[]>;
};

export type WordSyncController = {
  setTrack: (track: TrackTimingPayload | null, index: WordIndex | null) => void;
  start: () => void;
  stop: () => void;
  destroy: () => void;
  snap: () => void;
  handleSeeking: () => void;
  handleSeeked: () => void;
  handleWaiting: () => void;
  handlePlaying: () => void;
  handleRateChange: () => void;
  handlePause: () => void;
  handlePlay: () => void;
  setFollowHighlight: (value: boolean) => void;
};

export type SentenceGate = {
  start: number;
  end: number;
  sentenceIdx: number;
  segmentIndex: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
};

type LinguistBubbleTtsStatus = 'idle' | 'loading' | 'ready' | 'error';

export type LinguistBubbleNavigation = {
  sentenceIndex: number;
  tokenIndex: number;
  variantKind: TextPlayerVariantKind;
};

export type LinguistBubbleLookupSource = 'cache' | 'live';

export type LinguistBubbleState = {
  query: string;
  fullQuery: string;
  status: 'loading' | 'ready' | 'error';
  answer: string;
  lookupLanguage: string;
  llmModel: string | null;
  ttsLanguage: string;
  ttsVoice: string | null;
  ttsStatus: LinguistBubbleTtsStatus;
  navigation: LinguistBubbleNavigation | null;
  lookupSource?: LinguistBubbleLookupSource;
  /** Audio reference from lookup cache - allows playing word from narration audio */
  cachedAudioRef?: LookupCacheAudioRef | null;
};

export type LinguistBubbleFloatingPlacement = 'above' | 'below' | 'free';

export type TimelineVariantRuntime = {
  tokens: string[];
  revealTimes: number[];
};

export type TimelineSentenceRuntime = {
  index: number;
  sentenceNumber?: number | null;
  startTime: number;
  endTime: number;
  variants: {
    original: TimelineVariantRuntime;
    translation?: TimelineVariantRuntime;
    transliteration?: TimelineVariantRuntime;
  };
};

export type TimelineDisplay = {
  sentences: TextPlayerSentence[];
  activeIndex: number;
  effectiveTime: number;
};
