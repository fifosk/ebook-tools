import { useEffect } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { MyPainterSentenceContext } from '../../context/MyPainterProvider';

type UseMyPainterSentenceArgs = {
  jobId: string | null;
  chunk: LiveMediaChunk | null;
  activeSentenceIndex: number;
  activeSentenceNumber: number;
  activeSentenceImagePath: string | null;
  isLibraryMediaOrigin: boolean;
  setPlayerSentence?: ((value: MyPainterSentenceContext | null) => void) | null;
};

export function useMyPainterSentence({
  jobId,
  chunk,
  activeSentenceIndex,
  activeSentenceNumber,
  activeSentenceImagePath,
  isLibraryMediaOrigin,
  setPlayerSentence,
}: UseMyPainterSentenceArgs): void {
  useEffect(() => {
    if (!setPlayerSentence) {
      return;
    }
    if (!jobId) {
      setPlayerSentence(null);
      return;
    }

    const entries = chunk?.sentences ?? null;
    const entry =
      entries && entries.length > 0
        ? entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))]
        : null;
    const imagePayload = entry?.image ?? null;
    const prompt = typeof imagePayload?.prompt === 'string' ? imagePayload.prompt.trim() : null;
    const negative = typeof imagePayload?.negative_prompt === 'string' ? imagePayload.negative_prompt.trim() : null;
    const sentenceTextRaw = typeof entry?.original?.text === 'string' ? entry.original.text : null;
    const sentenceText =
      typeof sentenceTextRaw === 'string' && sentenceTextRaw.trim() ? sentenceTextRaw.trim() : null;

    setPlayerSentence({
      jobId,
      mediaOrigin: isLibraryMediaOrigin ? 'library' : 'job',
      rangeFragment: chunk?.rangeFragment ?? null,
      sentenceNumber: activeSentenceNumber,
      sentenceText,
      prompt,
      negativePrompt: negative,
      imagePath: activeSentenceImagePath,
    });
  }, [
    activeSentenceImagePath,
    activeSentenceIndex,
    activeSentenceNumber,
    chunk?.rangeFragment,
    chunk?.sentences,
    isLibraryMediaOrigin,
    jobId,
    setPlayerSentence,
  ]);
}
