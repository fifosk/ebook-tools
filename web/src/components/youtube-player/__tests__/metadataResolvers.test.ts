import { describe, it, expect, vi } from 'vitest';
import {
  extractLanguagesFromResult,
  normaliseSummary,
  resolveYoutubeTitle,
  resolveYoutubeChannel,
  resolveYoutubeSummary,
  resolveTvSummary,
  formatTvEpisodeLabel,
} from '../metadataResolvers';

describe('Metadata Resolvers', () => {
  describe('extractLanguagesFromResult', () => {
    it('should extract languages from youtube_dub payload', () => {
      const result = {
        youtube_dub: {
          source_language: 'en',
          target_language: 'es',
        },
      };
      expect(extractLanguagesFromResult(result)).toEqual({
        original: 'en',
        translation: 'es',
      });
    });

    it('should fallback to book_metadata', () => {
      const result = {
        book_metadata: {
          original_language: 'en',
          target_language: 'fr',
        },
      };
      expect(extractLanguagesFromResult(result)).toEqual({
        original: 'en',
        translation: 'fr',
      });
    });

    it('should return nulls for empty result', () => {
      expect(extractLanguagesFromResult({})).toEqual({
        original: null,
        translation: null,
      });
    });

    it('should return nulls for non-object', () => {
      expect(extractLanguagesFromResult(null)).toEqual({
        original: null,
        translation: null,
      });
    });
  });

  describe('normaliseSummary', () => {
    it('should strip HTML tags', () => {
      const html = '<p>This is <b>bold</b> text</p>';
      expect(normaliseSummary(html)).toBe('This is bold text');
    });

    it('should normalize whitespace', () => {
      expect(normaliseSummary('Text   with    spaces')).toBe('Text with spaces');
    });

    it('should truncate long text', () => {
      const longText = 'a'.repeat(400);
      const result = normaliseSummary(longText);
      expect(result).toHaveLength(320);
      expect(result?.endsWith('...')).toBe(true);
    });

    it('should return null for non-string', () => {
      expect(normaliseSummary(123)).toBeNull();
      expect(normaliseSummary(null)).toBeNull();
      expect(normaliseSummary(undefined)).toBeNull();
    });

    it('should return null for empty string', () => {
      expect(normaliseSummary('')).toBeNull();
      expect(normaliseSummary('   ')).toBeNull();
    });
  });

  describe('resolveYoutubeTitle', () => {
    it('should return trimmed title', () => {
      const metadata = { title: '  My Video  ' };
      expect(resolveYoutubeTitle(metadata)).toBe('My Video');
    });

    it('should return null for non-string title', () => {
      expect(resolveYoutubeTitle({ title: 123 })).toBeNull();
      expect(resolveYoutubeTitle({ title: null })).toBeNull();
    });

    it('should return null for null metadata', () => {
      expect(resolveYoutubeTitle(null)).toBeNull();
    });

    it('should return null for empty title', () => {
      expect(resolveYoutubeTitle({ title: '' })).toBeNull();
      expect(resolveYoutubeTitle({ title: '   ' })).toBeNull();
    });
  });

  describe('resolveYoutubeChannel', () => {
    it('should return channel name', () => {
      const metadata = { channel: 'My Channel' };
      expect(resolveYoutubeChannel(metadata)).toBe('My Channel');
    });

    it('should fallback to uploader', () => {
      const metadata = { uploader: 'Uploader Name' };
      expect(resolveYoutubeChannel(metadata)).toBe('Uploader Name');
    });

    it('should prefer channel over uploader', () => {
      const metadata = { channel: 'Channel', uploader: 'Uploader' };
      expect(resolveYoutubeChannel(metadata)).toBe('Channel');
    });

    it('should return null if neither exists', () => {
      expect(resolveYoutubeChannel({})).toBeNull();
      expect(resolveYoutubeChannel(null)).toBeNull();
    });
  });

  describe('resolveYoutubeSummary', () => {
    it('should return normalised summary', () => {
      const metadata = { summary: '  <p>Summary</p>  ' };
      expect(resolveYoutubeSummary(metadata)).toBe('Summary');
    });

    it('should fallback to description', () => {
      const metadata = { description: 'Description text' };
      expect(resolveYoutubeSummary(metadata)).toBe('Description text');
    });

    it('should prefer summary over description', () => {
      const metadata = { summary: 'Summary', description: 'Description' };
      expect(resolveYoutubeSummary(metadata)).toBe('Summary');
    });

    it('should return null for null metadata', () => {
      expect(resolveYoutubeSummary(null)).toBeNull();
    });
  });

  describe('resolveTvSummary', () => {
    it('should return episode summary', () => {
      const metadata = {
        episode: { summary: 'Episode summary' },
      };
      expect(resolveTvSummary(metadata)).toBe('Episode summary');
    });

    it('should fallback to show summary', () => {
      const metadata = {
        show: { summary: 'Show summary' },
      };
      expect(resolveTvSummary(metadata)).toBe('Show summary');
    });

    it('should prefer episode over show summary', () => {
      const metadata = {
        episode: { summary: 'Episode' },
        show: { summary: 'Show' },
      };
      expect(resolveTvSummary(metadata)).toBe('Episode');
    });

    it('should return null for null metadata', () => {
      expect(resolveTvSummary(null)).toBeNull();
    });
  });

  describe('formatTvEpisodeLabel', () => {
    it('should format episode with season and number', () => {
      const metadata = {
        kind: 'tv_episode',
        episode: {
          season: 1,
          number: 5,
          name: 'Episode Name',
        },
      };
      expect(formatTvEpisodeLabel(metadata)).toBe('S01E05 - Episode Name');
    });

    it('should return just name if no season/number', () => {
      const metadata = {
        kind: 'tv_episode',
        episode: {
          name: 'Episode Name',
        },
      };
      expect(formatTvEpisodeLabel(metadata)).toBe('Episode Name');
    });

    it('should return just code if no name', () => {
      const metadata = {
        kind: 'tv_episode',
        episode: {
          season: 2,
          number: 10,
        },
      };
      expect(formatTvEpisodeLabel(metadata)).toBe('S02E10');
    });

    it('should return null for non-tv_episode kind', () => {
      const metadata = {
        kind: 'movie',
        episode: { name: 'Name' },
      };
      expect(formatTvEpisodeLabel(metadata)).toBeNull();
    });

    it('should return null for null metadata', () => {
      expect(formatTvEpisodeLabel(null)).toBeNull();
    });
  });
});
