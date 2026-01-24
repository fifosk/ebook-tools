import type { MutableRefObject, ReactNode } from 'react';
import type { AudioTrackMetadata, ChunkSentenceMetadata } from '../../../api/dtos';
import type { LiveMediaChunk } from '../../../hooks/useLiveMedia';
import type { TimelineSentenceRuntime } from '../types';
import type { ExportPlayerManifest } from '../../../types/exportPlayer';

export type UseSentenceImageReelArgs = {
  jobId: string | null;
  playerMode?: 'online' | 'export';
  chunk: LiveMediaChunk | null;
  activeSentenceNumber: number;
  activeSentenceIndex: number;
  jobStartSentence?: number | null;
  jobEndSentence?: number | null;
  totalSentencesInBook?: number | null;
  bookTotalSentences?: number | null;
  isFullscreen: boolean;
  imageRefreshToken: number;
  isLibraryMediaOrigin: boolean;
  timelineSentences: TimelineSentenceRuntime[] | null;
  audioDuration: number | null;
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  activeAudioUrl: string | null;
  effectiveAudioUrl: string | null;
  onRequestSentenceJump?: (sentenceNumber: number) => void;
  inlineAudioPlayingRef: MutableRefObject<boolean>;
  setActiveSentenceIndex: (index: number) => void;
  handleTokenSeek: (time: number) => void;
  seekInlineAudioToTime: (time: number) => void;
};

export type UseSentenceImageReelResult = {
  sentenceImageReelNode: ReactNode | null;
  activeSentenceImagePath: string | null;
  reelScale: number;
};

export interface ReelWindowBounds {
  base: number;
  start: number;
  end: number;
  boundedStart: number;
  boundedEnd: number | null;
}

export interface ReelImageFrame {
  sentenceNumber: number | null;
  url: string | null;
  imagePath: string | null;
  rangeFragment: string | null;
  sentenceText: string | null;
  prompt: string | null;
  negativePrompt: string | null;
  isActive: boolean;
  isMissing: boolean;
}

export interface ImagePromptPlanSummary {
  quality?: {
    prompt_batch_size?: number;
    promptBatchSize?: number;
  };
  start_sentence?: number;
  startSentence?: number;
  end_sentence?: number;
  endSentence?: number;
  [key: string]: unknown;
}

export { type ExportPlayerManifest, type ChunkSentenceMetadata };
