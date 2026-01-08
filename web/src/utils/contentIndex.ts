export type ContentIndexChapter = {
  id: string;
  title: string;
  startSentence: number;
  endSentence: number | null;
};

export const toFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.trunc(value);
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return Math.trunc(parsed);
    }
  }
  return null;
};

export const normaliseContentIndexChapters = (payload: unknown): ContentIndexChapter[] => {
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  const record = payload as Record<string, unknown>;
  const rawChapters = record.chapters;
  if (!Array.isArray(rawChapters)) {
    return [];
  }
  const chapters: ContentIndexChapter[] = [];
  rawChapters.forEach((entry, index) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const raw = entry as Record<string, unknown>;
    const start =
      toFiniteNumber(raw.start_sentence ?? raw.startSentence ?? raw.start) ?? null;
    if (!start || start <= 0) {
      return;
    }
    const sentenceCount =
      toFiniteNumber(raw.sentence_count ?? raw.sentenceCount) ?? null;
    let end = toFiniteNumber(raw.end_sentence ?? raw.endSentence ?? raw.end);
    if (end === null && sentenceCount !== null) {
      end = start + Math.max(sentenceCount - 1, 0);
    }
    const id =
      (typeof raw.id === 'string' && raw.id.trim()) || `chapter-${index + 1}`;
    const title =
      (typeof raw.title === 'string' && raw.title.trim()) ||
      (typeof raw.toc_label === 'string' && raw.toc_label.trim()) ||
      `Chapter ${index + 1}`;
    chapters.push({
      id,
      title,
      startSentence: start,
      endSentence: end ?? null,
    });
  });
  return chapters;
};

export const extractContentIndexTotalSentences = (payload: unknown): number | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const record = payload as Record<string, unknown>;
  const direct =
    toFiniteNumber(
      record.total_sentences ?? record.totalSentences ?? record.sentence_total ?? record.sentenceTotal,
    );
  if (direct && direct > 0) {
    return direct;
  }
  const alignment = record.alignment;
  if (alignment && typeof alignment === 'object') {
    const alignmentRecord = alignment as Record<string, unknown>;
    const aligned =
      toFiniteNumber(
        alignmentRecord.sentence_total ?? alignmentRecord.sentenceTotal ?? alignmentRecord.total_sentences,
      );
    if (aligned && aligned > 0) {
      return aligned;
    }
  }
  return null;
};
