import { describe, expect, it, vi } from 'vitest';
import {
  extractOriginalUrl,
  extractTranslationUrl,
  extractCombinedUrl,
  resolveChunkAudioUrl,
  resolveSequenceAudioUrls,
} from '../audioUrlResolver';
import type { LiveMediaChunk } from '../../../hooks/useLiveMedia';

// Mock chunkResolver's resolveStorageUrl to pass through
vi.mock('../chunkResolver', () => ({
  resolveStorageUrl: (value: string | null, _jobId: string | null) => value,
}));

function makeTracks(config: {
  orig?: string;
  translation?: string;
  orig_trans?: string;
}): Record<string, { url: string }> {
  const tracks: Record<string, { url: string }> = {};
  if (config.orig) tracks.orig = { url: config.orig };
  if (config.translation) tracks.translation = { url: config.translation };
  if (config.orig_trans) tracks.orig_trans = { url: config.orig_trans };
  return tracks;
}

function makeChunk(audioTracks: Record<string, { url: string }> | null): LiveMediaChunk {
  return {
    chunkId: 'c1',
    rangeFragment: null,
    startSentence: 0,
    endSentence: 10,
    files: [],
    audioTracks: audioTracks as LiveMediaChunk['audioTracks'],
  };
}

// ─── URL extraction ───────────────────────────────────────────────────

describe('extractOriginalUrl', () => {
  it('extracts orig track URL', () => {
    expect(extractOriginalUrl(makeTracks({ orig: '/audio/orig.mp3' }))).toBe('/audio/orig.mp3');
  });

  it('extracts original track URL (alternative key)', () => {
    const tracks = { original: { url: '/audio/original.mp3' } } as Record<string, { url: string }>;
    expect(extractOriginalUrl(tracks)).toBe('/audio/original.mp3');
  });

  it('prefers orig over original key', () => {
    const tracks = {
      orig: { url: '/audio/orig.mp3' },
      original: { url: '/audio/original.mp3' },
    } as Record<string, { url: string }>;
    expect(extractOriginalUrl(tracks)).toBe('/audio/orig.mp3');
  });

  it('returns null when no orig track', () => {
    expect(extractOriginalUrl(makeTracks({ translation: '/audio/trans.mp3' }))).toBeNull();
  });

  it('returns null for null input', () => {
    expect(extractOriginalUrl(null)).toBeNull();
  });
});

describe('extractTranslationUrl', () => {
  it('extracts translation track URL', () => {
    expect(extractTranslationUrl(makeTracks({ translation: '/audio/trans.mp3' }))).toBe('/audio/trans.mp3');
  });

  it('returns null when no translation track', () => {
    expect(extractTranslationUrl(makeTracks({ orig: '/audio/orig.mp3' }))).toBeNull();
  });
});

describe('extractCombinedUrl', () => {
  it('extracts orig_trans track URL', () => {
    expect(extractCombinedUrl(makeTracks({ orig_trans: '/audio/mix.mp3' }))).toBe('/audio/mix.mp3');
  });

  it('returns null when no combined track', () => {
    expect(extractCombinedUrl(makeTracks({ orig: '/audio/orig.mp3' }))).toBeNull();
  });
});

// ─── resolveChunkAudioUrl ─────────────────────────────────────────────

describe('resolveChunkAudioUrl', () => {
  it('prefers translation when translation enabled', () => {
    const chunk = makeChunk(makeTracks({
      orig: '/orig.mp3',
      translation: '/trans.mp3',
    }));
    expect(resolveChunkAudioUrl(chunk, 'job1', false, true)).toBe('/trans.mp3');
  });

  it('uses original when only original enabled', () => {
    const chunk = makeChunk(makeTracks({
      orig: '/orig.mp3',
      translation: '/trans.mp3',
    }));
    expect(resolveChunkAudioUrl(chunk, 'job1', true, false)).toBe('/orig.mp3');
  });

  it('falls back to combined when direct track unavailable', () => {
    const chunk = makeChunk(makeTracks({
      orig_trans: '/mix.mp3',
    }));
    expect(resolveChunkAudioUrl(chunk, 'job1', false, true)).toBe('/mix.mp3');
  });

  it('falls back through all options when both enabled but only combined exists', () => {
    const chunk = makeChunk(makeTracks({
      orig_trans: '/mix.mp3',
    }));
    // Both enabled, no direct tracks → translation fallback to combined
    expect(resolveChunkAudioUrl(chunk, 'job1', true, true)).toBe('/mix.mp3');
  });

  it('returns null when no audio tracks', () => {
    const chunk = makeChunk(null);
    expect(resolveChunkAudioUrl(chunk, 'job1', true, true)).toBeNull();
  });

  it('uses ultimate fallback when neither enabled but tracks exist', () => {
    const chunk = makeChunk(makeTracks({
      orig: '/orig.mp3',
      translation: '/trans.mp3',
    }));
    // Both disabled → ultimate fallback: translation → original → combined
    expect(resolveChunkAudioUrl(chunk, 'job1', false, false)).toBe('/trans.mp3');
  });
});

// ─── resolveSequenceAudioUrls ─────────────────────────────────────────

describe('resolveSequenceAudioUrls', () => {
  it('returns both original and translation URLs', () => {
    const chunk = makeChunk(makeTracks({
      orig: '/orig.mp3',
      translation: '/trans.mp3',
    }));
    const urls = resolveSequenceAudioUrls(chunk, 'job1');
    expect(urls).toHaveLength(2);
    expect(urls).toContain('/orig.mp3');
    expect(urls).toContain('/trans.mp3');
  });

  it('returns only available URLs', () => {
    const chunk = makeChunk(makeTracks({
      orig: '/orig.mp3',
    }));
    const urls = resolveSequenceAudioUrls(chunk, 'job1');
    expect(urls).toHaveLength(1);
    expect(urls[0]).toBe('/orig.mp3');
  });

  it('deduplicates identical URLs', () => {
    const chunk = makeChunk(makeTracks({
      orig: '/same.mp3',
      translation: '/same.mp3',
    }));
    const urls = resolveSequenceAudioUrls(chunk, 'job1');
    expect(urls).toHaveLength(1);
  });

  it('returns empty array when no tracks', () => {
    const chunk = makeChunk(null);
    expect(resolveSequenceAudioUrls(chunk, 'job1')).toHaveLength(0);
  });
});
