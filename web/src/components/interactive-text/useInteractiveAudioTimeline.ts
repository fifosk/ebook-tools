import { useMemo, useRef } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { formatDurationLabel } from '../../utils/timeFormatters';
import {
  resolveTrackDuration,
  type SelectedAudioTrack,
  type SequenceSegment,
} from './useInteractiveAudioSequence';

type UseInteractiveAudioTimelineArgs = {
  chunk: LiveMediaChunk | null;
  chunks: LiveMediaChunk[] | null;
  activeChunkIndex: number | null;
  selectedTracks: SelectedAudioTrack[];
  chunkTime: number;
  sequenceEnabled: boolean;
  sequencePlan: SequenceSegment[];
  sequenceIndexRef: React.MutableRefObject<number>;
  jobId: string | null;
  isInlineAudioPlaying: boolean;
  isSeekingRef: React.MutableRefObject<boolean>;
};

type AudioTimelineState = {
  played: number;
  remaining: number;
  total: number;
  key: string;
};

export function useInteractiveAudioTimeline({
  chunk,
  chunks,
  activeChunkIndex,
  selectedTracks,
  chunkTime,
  sequenceEnabled,
  sequencePlan,
  sequenceIndexRef,
  jobId,
  isInlineAudioPlaying,
  isSeekingRef,
}: UseInteractiveAudioTimelineArgs) {
  const chunkList = useMemo(() => (Array.isArray(chunks) ? chunks : []), [chunks]);
  const resolvedActiveChunkIndex = useMemo(() => {
    if (typeof activeChunkIndex === 'number' && Number.isFinite(activeChunkIndex)) {
      return Math.max(Math.trunc(activeChunkIndex), -1);
    }
    if (!chunk || chunkList.length === 0) {
      return -1;
    }
    const key = chunk.chunkId ?? chunk.rangeFragment ?? chunk.metadataPath ?? chunk.metadataUrl ?? null;
    if (!key) {
      return -1;
    }
    return chunkList.findIndex((entry) => {
      if (!entry) {
        return false;
      }
      return (
        entry.chunkId === key ||
        entry.rangeFragment === key ||
        entry.metadataPath === key ||
        entry.metadataUrl === key
      );
    });
  }, [activeChunkIndex, chunk, chunkList]);

  const audioTimeline = useMemo(() => {
    if (!chunkList.length || selectedTracks.length === 0) {
      return null;
    }
    if (resolvedActiveChunkIndex < 0 || resolvedActiveChunkIndex >= chunkList.length) {
      return null;
    }
    const sumChunk = (target: LiveMediaChunk | null | undefined) =>
      selectedTracks.reduce((sum, track) => sum + (resolveTrackDuration(target, track) ?? 0), 0);
    let total = 0;
    let before = 0;
    chunkList.forEach((entry, index) => {
      const chunkDuration = sumChunk(entry);
      total += chunkDuration;
      if (index < resolvedActiveChunkIndex) {
        before += chunkDuration;
      }
    });
    if (!Number.isFinite(total) || total <= 0) {
      return null;
    }
    const currentChunk = chunkList[resolvedActiveChunkIndex] ?? chunk;
    const currentChunkDuration = sumChunk(currentChunk);
    let within = 0;
    if (sequenceEnabled && sequencePlan.length > 0) {
      const currentIndex = Math.max(0, Math.min(sequenceIndexRef.current, sequencePlan.length - 1));
      const segment = sequencePlan[currentIndex];
      if (segment) {
        let elapsed = 0;
        for (let idx = 0; idx < currentIndex; idx += 1) {
          const beforeSegment = sequencePlan[idx];
          if (beforeSegment) {
            elapsed += Math.max(beforeSegment.end - beforeSegment.start, 0);
          }
        }
        const segmentDuration = Math.max(segment.end - segment.start, 0);
        const progress = Math.min(Math.max(chunkTime - segment.start, 0), segmentDuration);
        within = elapsed + progress;
      }
    } else {
      const rawTime = Number.isFinite(chunkTime) ? chunkTime : 0;
      within =
        currentChunkDuration > 0
          ? Math.min(Math.max(rawTime, 0), currentChunkDuration)
          : Math.max(rawTime, 0);
    }
    const played = Math.min(before + within, total);
    const remaining = Math.max(total - played, 0);
    return { played, remaining, total };
  }, [
    chunk,
    chunkList,
    chunkTime,
    resolvedActiveChunkIndex,
    selectedTracks,
    sequenceEnabled,
    sequenceIndexRef,
    sequencePlan,
  ]);

  const audioTimelineKey = useMemo(() => {
    if (selectedTracks.length === 0) {
      return null;
    }
    const trackKey = selectedTracks.join('|');
    return `${jobId ?? 'job'}:${sequenceEnabled ? 'seq' : 'single'}:${trackKey}`;
  }, [jobId, selectedTracks, sequenceEnabled]);

  const audioTimelineRef = useRef<AudioTimelineState | null>(null);
  const audioTimelineDisplay = useMemo(() => {
    if (!audioTimeline || !audioTimelineKey) {
      // Keep previous state if available to avoid flickering when temporarily losing timeline
      if (audioTimelineRef.current && audioTimelineRef.current.key === audioTimelineKey) {
        return {
          played: audioTimelineRef.current.played,
          remaining: audioTimelineRef.current.remaining,
          total: audioTimelineRef.current.total,
        };
      }
      audioTimelineRef.current = null;
      return null;
    }
    const prev = audioTimelineRef.current;
    if (!prev || prev.key !== audioTimelineKey) {
      const next = { ...audioTimeline, key: audioTimelineKey };
      audioTimelineRef.current = next;
      return audioTimeline;
    }
    let played = audioTimeline.played;
    // Use the larger total to prevent flickering when chunks are being loaded/hydrated
    let total = Math.max(audioTimeline.total, prev.total);
    const backwards = played < prev.played;
    const backstep = prev.played - played;
    // Allow larger backsteps (up to 30 seconds) to prevent visible jumps during chunk transitions
    if (backwards && isInlineAudioPlaying && !isSeekingRef.current && backstep < 30) {
      played = prev.played;
    }
    played = Math.max(0, Math.min(played, total));
    const remaining = Math.max(total - played, 0);
    const next = { played, remaining, total, key: audioTimelineKey };
    audioTimelineRef.current = next;
    return { played, remaining, total };
  }, [audioTimeline, audioTimelineKey, isInlineAudioPlaying, isSeekingRef]);

  const audioTimelineText = audioTimelineDisplay
    ? `${formatDurationLabel(audioTimelineDisplay.played)} / ${formatDurationLabel(
        audioTimelineDisplay.remaining,
      )} remaining`
    : null;
  const audioTimelineTitle = audioTimelineDisplay
    ? `Total ${formatDurationLabel(audioTimelineDisplay.total)}`
    : null;

  return { audioTimelineText, audioTimelineTitle };
}
