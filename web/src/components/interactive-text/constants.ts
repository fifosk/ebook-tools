import type { TimingPayload } from '../../types/timing';
import type { WordSyncLane } from './types';

export const WORD_SYNC_LANE_LABELS: Record<WordSyncLane, string> = {
  orig: 'Original',
  trans: 'Translation',
  xlit: 'Transliteration',
};

// Re-export linguist constants from canonical location for backward compatibility
export {
  DICTIONARY_LOOKUP_LONG_PRESS_MS,
  MY_LINGUIST_BUBBLE_MAX_CHARS,
  MY_LINGUIST_EMPTY_SENTINEL,
  MY_LINGUIST_STORAGE_KEYS,
  MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
  MY_LINGUIST_DEFAULT_LLM_MODEL,
} from '../../lib/linguist';

export const EMPTY_TIMING_PAYLOAD: TimingPayload = {
  trackKind: 'translation_only',
  segments: [],
};
