import { describe, it, expect } from 'vitest';
import {
  normalizeInlineSubtitleKey,
  resolveInlineSubtitlePayload,
  buildSubtitleDataUrl,
  extractFileSuffix,
} from '../subtitleHelpers';

describe('Subtitle Helpers', () => {
  describe('normalizeInlineSubtitleKey', () => {
    it('should convert backslashes to forward slashes', () => {
      expect(normalizeInlineSubtitleKey('path\\to\\file.vtt')).toBe('path/to/file.vtt');
      expect(normalizeInlineSubtitleKey('folder\\\\subfolder\\file.srt')).toBe('folder/subfolder/file.srt');
    });

    it('should remove leading ./ and /', () => {
      expect(normalizeInlineSubtitleKey('./file.vtt')).toBe('file.vtt');
      expect(normalizeInlineSubtitleKey('/file.vtt')).toBe('file.vtt');
      expect(normalizeInlineSubtitleKey('./path/to/file.vtt')).toBe('path/to/file.vtt');
    });

    it('should remove query params and hash', () => {
      expect(normalizeInlineSubtitleKey('file.vtt?token=abc')).toBe('file.vtt');
      expect(normalizeInlineSubtitleKey('file.vtt#fragment')).toBe('file.vtt');
      expect(normalizeInlineSubtitleKey('file.vtt?token=abc#fragment')).toBe('file.vtt');
    });

    it('should decode URI components', () => {
      expect(normalizeInlineSubtitleKey('file%20name.vtt')).toBe('file name.vtt');
      expect(normalizeInlineSubtitleKey('path%2Fto%2Ffile.vtt')).toBe('path/to/file.vtt');
    });

    it('should handle invalid URI encoding gracefully', () => {
      expect(normalizeInlineSubtitleKey('file%ZZname.vtt')).toBe('file%ZZname.vtt');
    });

    it('should handle whitespace', () => {
      expect(normalizeInlineSubtitleKey('  file.vtt  ')).toBe('file.vtt');
    });

    it('should handle empty string', () => {
      expect(normalizeInlineSubtitleKey('')).toBe('');
    });
  });

  describe('resolveInlineSubtitlePayload', () => {
    it('should return payload for exact match', () => {
      const subtitles = {
        'file.vtt': 'WEBVTT\n\n1\n00:00:01.000',
      };
      expect(resolveInlineSubtitlePayload('file.vtt', subtitles)).toBe('WEBVTT\n\n1\n00:00:01.000');
    });

    it('should normalize key before lookup', () => {
      const subtitles = {
        'file.vtt': 'WEBVTT content',
      };
      expect(resolveInlineSubtitlePayload('./file.vtt', subtitles)).toBe('WEBVTT content');
      expect(resolveInlineSubtitlePayload('file.vtt?token=abc', subtitles)).toBe('WEBVTT content');
    });

    it('should try both normalized and slash-stripped keys', () => {
      const subtitles = {
        'path/file.vtt': 'content1',
      };
      expect(resolveInlineSubtitlePayload('/path/file.vtt', subtitles)).toBe('content1');
    });

    it('should return null if subtitle map is null', () => {
      expect(resolveInlineSubtitlePayload('file.vtt', null)).toBeNull();
    });

    it('should return null if key not found', () => {
      const subtitles = {
        'file.vtt': 'content',
      };
      expect(resolveInlineSubtitlePayload('other.vtt', subtitles)).toBeNull();
    });

    it('should handle backslash paths', () => {
      const subtitles = {
        'path/file.vtt': 'content',
      };
      expect(resolveInlineSubtitlePayload('path\\file.vtt', subtitles)).toBe('content');
    });
  });

  describe('buildSubtitleDataUrl', () => {
    it('should build data URL with vtt MIME type', () => {
      const result = buildSubtitleDataUrl('WEBVTT\n\n1', 'vtt');
      expect(result).toMatch(/^data:text\/vtt;charset=utf-8,/);
      expect(result).toContain(encodeURIComponent('WEBVTT\n\n1'));
    });

    it('should build data URL with plain text MIME type for non-vtt formats', () => {
      const result = buildSubtitleDataUrl('subtitle content', 'srt');
      expect(result).toMatch(/^data:text\/plain;charset=utf-8,/);
    });

    it('should use plain text for null format', () => {
      const result = buildSubtitleDataUrl('content', null);
      expect(result).toMatch(/^data:text\/plain;charset=utf-8,/);
    });

    it('should use plain text for undefined format', () => {
      const result = buildSubtitleDataUrl('content');
      expect(result).toMatch(/^data:text\/plain;charset=utf-8,/);
    });

    it('should be case-insensitive for format', () => {
      const result = buildSubtitleDataUrl('content', 'VTT');
      expect(result).toMatch(/^data:text\/vtt;charset=utf-8,/);
    });

    it('should encode special characters', () => {
      const result = buildSubtitleDataUrl('hello & goodbye', 'vtt');
      expect(result).toContain(encodeURIComponent('hello & goodbye'));
    });
  });

  describe('extractFileSuffix', () => {
    it('should extract file extension', () => {
      expect(extractFileSuffix('file.vtt')).toBe('vtt');
      expect(extractFileSuffix('file.srt')).toBe('srt');
      expect(extractFileSuffix('file.ass')).toBe('ass');
    });

    it('should extract from full path', () => {
      expect(extractFileSuffix('/path/to/file.vtt')).toBe('vtt');
      expect(extractFileSuffix('folder/subfolder/file.srt')).toBe('srt');
    });

    it('should ignore query params and hash', () => {
      expect(extractFileSuffix('file.vtt?token=abc')).toBe('vtt');
      expect(extractFileSuffix('file.vtt#fragment')).toBe('vtt');
      expect(extractFileSuffix('file.vtt?token=abc#fragment')).toBe('vtt');
    });

    it('should return lowercase', () => {
      expect(extractFileSuffix('file.VTT')).toBe('vtt');
      expect(extractFileSuffix('file.SRT')).toBe('srt');
    });

    it('should return empty string for no extension', () => {
      expect(extractFileSuffix('file')).toBe('');
      expect(extractFileSuffix('/path/to/file')).toBe('');
    });

    it('should return empty string for null/undefined', () => {
      expect(extractFileSuffix(null)).toBe('');
      expect(extractFileSuffix(undefined)).toBe('');
      expect(extractFileSuffix('')).toBe('');
    });

    it('should handle multiple dots', () => {
      expect(extractFileSuffix('file.backup.vtt')).toBe('vtt');
      expect(extractFileSuffix('archive.tar.gz')).toBe('gz');
    });

    it('should handle hidden files', () => {
      expect(extractFileSuffix('.htaccess')).toBe('htaccess');
    });
  });
});
