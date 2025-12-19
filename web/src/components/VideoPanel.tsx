import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaChunk } from '../hooks/useLiveMedia';
import { appendAccessToken, buildStorageUrl, fetchVideoStatus, generateVideo } from '../api/client';
import { isAudioFileType } from './player-panel/utils';
import { PanelHeader } from './player-panel/PanelHeader';
import { PanelMessage } from './player-panel/PanelMessage';
import type { VideoGenerationResponse } from '../api/dtos';

interface VideoPanelProps {
  jobId: string;
  chunks: LiveMediaChunk[];
  isLoading?: boolean;
}

type VideoStatus = VideoGenerationResponse | null;

function formatSentenceRange(start: number | null, end: number | null): string {
  if (typeof start === 'number' && typeof end === 'number') {
    return start === end ? `${start}` : `${start}-${end}`;
  }
  if (typeof start === 'number') {
    return `${start}`;
  }
  if (typeof end === 'number') {
    return `${end}`;
  }
  return '';
}

function buildVideoRequest(jobId: string, chunks: LiveMediaChunk[]): Record<string, unknown> | null {
  if (!jobId.trim()) {
    return null;
  }

  const slides: string[] = [];
  const audio: Array<Record<string, string>> = [];
  let firstStart: number | null = null;
  let lastEnd: number | null = null;

  chunks.forEach((chunk, index) => {
    const audioFile = chunk.files.find((file) => isAudioFileType(file.type) && file.relative_path);
    if (!audioFile || !audioFile.relative_path) {
      return;
    }

    const rangeLabel = chunk.rangeFragment || formatSentenceRange(chunk.startSentence ?? null, chunk.endSentence ?? null);
    const slideLabel = rangeLabel ? `Sentences ${rangeLabel}` : `Chunk ${index + 1}`;

    slides.push(slideLabel);
    audio.push({
      job_id: jobId,
      relative_path: audioFile.relative_path,
    });

    if (firstStart === null && typeof chunk.startSentence === 'number') {
      firstStart = chunk.startSentence;
    }
    if (typeof chunk.endSentence === 'number') {
      lastEnd = chunk.endSentence;
    }
  });

  if (slides.length === 0 || slides.length !== audio.length) {
    return null;
  }

  const batchStart = firstStart ?? 1;
  const batchEnd = lastEnd ?? (firstStart !== null ? firstStart + slides.length - 1 : slides.length);

  return {
    slides,
    audio,
    output_filename: 'regenerated-video.mp4',
    options: {
      batch_start: batchStart,
      batch_end: batchEnd,
      total_sentences: batchEnd,
      cleanup: true,
    },
  };
}

export default function VideoPanel({ jobId, chunks, isLoading = false }: VideoPanelProps) {
  const [status, setStatus] = useState<VideoStatus>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pollingRef = useRef<number | null>(null);

  const videoRequest = useMemo(() => buildVideoRequest(jobId, chunks), [jobId, chunks]);

  const previewUrl = useMemo(() => {
    if (!status?.output_path) {
      return null;
    }
    const baseUrl = buildStorageUrl(status.output_path, jobId);
    return appendAccessToken(baseUrl);
  }, [jobId, status]);

  const refreshStatus = useCallback(async () => {
    if (!jobId.trim()) {
      setStatus(null);
      return;
    }
    try {
      const latest = await fetchVideoStatus(jobId);
      setStatus(latest);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load video status.';
      setError(message);
    }
  }, [jobId]);

  useEffect(() => {
    refreshStatus();
    return () => {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [refreshStatus]);

  useEffect(() => {
    if (!status) {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }
    if (!['queued', 'running'].includes(status.status) || pollingRef.current !== null) {
      return;
    }
    pollingRef.current = window.setInterval(() => {
      refreshStatus();
    }, 5000);
    return () => {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [status, refreshStatus]);

  const handleRegenerate = useCallback(async () => {
    if (!videoRequest) {
      setError('Video regeneration is unavailable until audio tracks are ready.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await generateVideo(jobId, videoRequest);
      setStatus(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Video regeneration failed.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [jobId, videoRequest]);

  const currentStatus = status?.status ?? 'unknown';
  const disableRegenerate = isSubmitting || isLoading || !videoRequest;

  return (
    <section className="video-panel" aria-label="Video preview">
      <PanelHeader
        title="Video"
        status={currentStatus}
        className="video-panel__header"
        statusClassName="video-panel__status"
        statusClassNamePrefix="video-panel__status--"
      />
      {previewUrl ? (
        <video className="video-panel__preview" controls src={previewUrl}>
          Your browser does not support the video tag.
        </video>
      ) : (
        <PanelMessage as="div" className="video-panel__placeholder">
          No rendered video available yet.
        </PanelMessage>
      )}
      <div className="video-panel__actions">
        <button type="button" onClick={handleRegenerate} disabled={disableRegenerate}>
          {isSubmitting ? 'Regenerating…' : 'Regenerate'}
        </button>
        {videoRequest === null && !isLoading && (
          <PanelMessage className="video-panel__hint">
            Provide audio by running the pipeline to enable regeneration.
          </PanelMessage>
        )}
      </div>
      {error && <PanelMessage className="video-panel__error">{error}</PanelMessage>}
    </section>
  );
}
