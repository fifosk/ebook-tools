export const MY_LINGUIST_EMPTY_SENTINEL = '__EMPTY__';

export const MY_LINGUIST_STORAGE_KEYS = {
  inputLanguage: 'ebookTools.myLinguist.inputLanguage',
  lookupLanguage: 'ebookTools.myLinguist.lookupLanguage',
  llmModel: 'ebookTools.myLinguist.llmModel',
  ttsVoice: 'ebookTools.myLinguist.ttsVoice',
  systemPrompt: 'ebookTools.myLinguist.systemPrompt',
  bubblePinned: 'ebookTools.myLinguist.bubblePinned',
  bubbleDocked: 'ebookTools.myLinguist.bubbleDocked',
  bubbleLocked: 'ebookTools.myLinguist.bubbleLocked',
  bubblePinnedPosition: 'ebookTools.myLinguist.bubblePinnedPosition',
  bubblePinnedSize: 'ebookTools.myLinguist.bubblePinnedSize',
  questionVoice: 'ebookTools.myLinguist.questionVoice',
  replyVoice: 'ebookTools.myLinguist.replyVoice',
  panelWidth: 'ebookTools.myLinguist.panelWidth',
  panelHeight: 'ebookTools.myLinguist.panelHeight',
} as const;

export const MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE = 'English';
export const MY_LINGUIST_DEFAULT_LLM_MODEL = 'ollama_cloud:mistral-large-3:675b-cloud';
export const MY_LINGUIST_BUBBLE_MAX_CHARS = 600;
export const DICTIONARY_LOOKUP_LONG_PRESS_MS = 450;
