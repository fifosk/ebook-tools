export const DEFAULT_VIDEO_DIR = '';
export const DEFAULT_LLM_MODEL = 'ollama_cloud:mistral-large-3:675b-cloud';
export const DEFAULT_ORIGINAL_MIX_PERCENT = 5;
export const DEFAULT_FLUSH_SENTENCES = 10;
export const DEFAULT_TRANSLATION_BATCH_SIZE = 10;
export const DEFAULT_TARGET_HEIGHT = 480;
export const DEFAULT_PRESERVE_ASPECT_RATIO = true;
export const DEFAULT_SPLIT_BATCHES = true;
export const DEFAULT_STITCH_BATCHES = true;
export const VIDEO_DUB_STORAGE_KEYS = {
  baseDir: 'ebookTools.youtubeDub.baseDir',
  selectedVideoPath: 'ebookTools.youtubeDub.selectedVideoPath',
  selectedSubtitlePath: 'ebookTools.youtubeDub.selectedSubtitlePath'
} as const;
export const RESOLUTION_OPTIONS = [
  { value: 320, label: '320p (lighter)' },
  { value: 480, label: '480p (default)' },
  { value: 720, label: '720p' }
];
