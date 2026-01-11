import type { TimingPayload } from '../../types/timing';
import type { WordSyncLane } from './types';

export const WORD_SYNC_LANE_LABELS: Record<WordSyncLane, string> = {
  orig: 'Original',
  trans: 'Translation',
  xlit: 'Transliteration',
};

export const DICTIONARY_LOOKUP_LONG_PRESS_MS = 450;
export const MY_LINGUIST_BUBBLE_MAX_CHARS = 600;
export const MY_LINGUIST_EMPTY_SENTINEL = '__EMPTY__';
export const MY_LINGUIST_STORAGE_KEYS = {
  inputLanguage: 'ebookTools.myLinguist.inputLanguage',
  lookupLanguage: 'ebookTools.myLinguist.lookupLanguage',
  llmModel: 'ebookTools.myLinguist.llmModel',
  systemPrompt: 'ebookTools.myLinguist.systemPrompt',
  bubblePinned: 'ebookTools.myLinguist.bubblePinned',
  bubbleDocked: 'ebookTools.myLinguist.bubbleDocked',
  bubbleLocked: 'ebookTools.myLinguist.bubbleLocked',
  bubblePinnedPosition: 'ebookTools.myLinguist.bubblePinnedPosition',
  bubblePinnedSize: 'ebookTools.myLinguist.bubblePinnedSize',
} as const;
export const MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE = 'English';
export const MY_LINGUIST_DEFAULT_LLM_MODEL = 'ollama_cloud:gpt-oss:120b-cloud';

export const EMPTY_TIMING_PAYLOAD: TimingPayload = {
  trackKind: 'translation_only',
  segments: [],
};
