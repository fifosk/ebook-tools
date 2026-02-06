export {
  resolveChunkKey,
  resolveStorageUrl,
  resolveChunkMetadataUrl,
} from './chunkResolver';

export {
  extractOriginalUrl,
  extractTranslationUrl,
  extractCombinedUrl,
  resolveChunkAudioUrl,
} from './audioUrlResolver';

export {
  resolveNumericValue,
  resolveDurationValue,
  readSentenceGate,
  readPhaseDuration,
  resolveSentenceGate,
  resolveSentenceDuration,
  type SequenceTrack,
  type SelectedAudioTrack,
} from './gateExtractor';

export {
  buildSentenceChunkIndex,
  lookupSentence,
  findChunkBySentence,
  type SentenceChunkEntry,
  type SentenceChunkIndex,
  type SentenceRange,
} from './sentenceChunkIndex';
