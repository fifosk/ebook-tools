export const DEFAULT_VIDEO_DIR = '/Volumes/Data/Download/DStation';
export const DEFAULT_LLM_MODEL = 'ollama_cloud:mistral-large-3:675b-cloud';
export const DEFAULT_TRANSLATION_BATCH_SIZE = 10;
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
