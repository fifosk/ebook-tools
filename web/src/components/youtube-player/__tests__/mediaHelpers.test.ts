import { describe, it, expect, vi, beforeEach } from 'vitest';
import { buildSiblingSubtitleTracks, createJobMediaResolver } from '../mediaHelpers';

describe('Media Helpers', () => {
  describe('buildSiblingSubtitleTracks', () => {
    const mockReplaceUrlExtension = vi.fn((url: string, suffix: string) => {
      return url.replace(/\.[^.]+$/, suffix);
    });
    const mockResolveSubtitleUrl = vi.fn((url: string) => `resolved:${url}`);
    const mockSubtitleFormatFromPath = vi.fn((path: string) => {
      if (path.endsWith('.vtt')) return 'vtt';
      if (path.endsWith('.srt')) return 'srt';
      if (path.endsWith('.ass')) return 'ass';
      return null;
    });

    beforeEach(() => {
      mockReplaceUrlExtension.mockClear();
      mockResolveSubtitleUrl.mockClear();
      mockSubtitleFormatFromPath.mockClear();
    });

    it('should build subtitle tracks for all formats', () => {
      const result = buildSiblingSubtitleTracks(
        'video.mp4',
        mockReplaceUrlExtension,
        mockResolveSubtitleUrl,
        mockSubtitleFormatFromPath
      );

      expect(result).toHaveLength(3);
      expect(result[0]).toMatchObject({
        url: 'resolved:video.ass',
        label: 'Subtitles',
        kind: 'subtitles',
        language: 'und',
        format: 'ass',
      });
      expect(result[1]).toMatchObject({
        url: 'resolved:video.vtt',
        label: 'Subtitles (2)',
        kind: 'subtitles',
        language: 'und',
        format: 'vtt',
      });
      expect(result[2]).toMatchObject({
        url: 'resolved:video.srt',
        label: 'Subtitles (3)',
        kind: 'subtitles',
        language: 'und',
        format: 'srt',
      });
    });

    it('should return empty array for null video URL', () => {
      const result = buildSiblingSubtitleTracks(
        null,
        mockReplaceUrlExtension,
        mockResolveSubtitleUrl,
        mockSubtitleFormatFromPath
      );
      expect(result).toEqual([]);
    });

    it('should return empty array for undefined video URL', () => {
      const result = buildSiblingSubtitleTracks(
        undefined,
        mockReplaceUrlExtension,
        mockResolveSubtitleUrl,
        mockSubtitleFormatFromPath
      );
      expect(result).toEqual([]);
    });

    it('should return empty array for empty string', () => {
      const result = buildSiblingSubtitleTracks(
        '',
        mockReplaceUrlExtension,
        mockResolveSubtitleUrl,
        mockSubtitleFormatFromPath
      );
      expect(result).toEqual([]);
    });

    it('should filter out null candidates from replaceUrlExtension', () => {
      const mockReplace = vi.fn((url: string, suffix: string) => {
        if (suffix === '.vtt') return null; // Simulate failure for .vtt
        return url.replace(/\.[^.]+$/, suffix);
      });

      const result = buildSiblingSubtitleTracks(
        'video.mp4',
        mockReplace,
        mockResolveSubtitleUrl,
        mockSubtitleFormatFromPath
      );

      expect(result).toHaveLength(2); // Only .ass and .srt
      expect(result.some((t) => t.format === 'vtt')).toBe(false);
    });

    it('should handle URLs with query parameters', () => {
      const result = buildSiblingSubtitleTracks(
        'video.mp4?token=abc',
        mockReplaceUrlExtension,
        mockResolveSubtitleUrl,
        mockSubtitleFormatFromPath
      );

      expect(result).toHaveLength(3);
      expect(mockResolveSubtitleUrl).toHaveBeenCalledWith('video.ass?token=abc', 'ass');
    });

    it('should use undefined format when subtitleFormatFromPath returns null', () => {
      const mockFormat = vi.fn(() => null);

      const result = buildSiblingSubtitleTracks(
        'video.mp4',
        mockReplaceUrlExtension,
        mockResolveSubtitleUrl,
        mockFormat
      );

      expect(result[0].format).toBeUndefined();
    });
  });

  describe('createJobMediaResolver', () => {
    const mockAppendAccessToken = vi.fn((url: string) => `${url}?token=xyz`);

    beforeEach(() => {
      mockAppendAccessToken.mockClear();
    });

    it('should append token to /api/ paths', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', '/api/media/video.mp4');

      expect(result).toBe('/api/media/video.mp4?token=xyz');
      expect(mockAppendAccessToken).toHaveBeenCalledWith('/api/media/video.mp4');
    });

    it('should append token to absolute paths', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', '/media/video.mp4');

      expect(result).toBe('/media/video.mp4?token=xyz');
      expect(mockAppendAccessToken).toHaveBeenCalledWith('/media/video.mp4');
    });

    it('should return URLs unchanged', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', 'https://example.com/video.mp4');

      expect(result).toBe('https://example.com/video.mp4');
      expect(mockAppendAccessToken).not.toHaveBeenCalled();
    });

    it('should handle http URLs', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', 'http://example.com/video.mp4');

      expect(result).toBe('http://example.com/video.mp4');
    });

    it('should handle ftp URLs', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', 'ftp://example.com/video.mp4');

      expect(result).toBe('ftp://example.com/video.mp4');
    });

    it('should return relative paths unchanged', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', 'video.mp4');

      expect(result).toBe('video.mp4');
      expect(mockAppendAccessToken).not.toHaveBeenCalled();
    });

    it('should return null for non-string values', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);

      expect(resolver('job-123', null)).toBeNull();
      expect(resolver('job-123', undefined)).toBeNull();
      expect(resolver('job-123', 123)).toBeNull();
      expect(resolver('job-123', {})).toBeNull();
      expect(resolver('job-123', [])).toBeNull();
    });

    it('should return null for empty string', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      expect(resolver('job-123', '')).toBeNull();
      expect(resolver('job-123', '   ')).toBeNull();
    });

    it('should trim whitespace', () => {
      const resolver = createJobMediaResolver(mockAppendAccessToken);
      const result = resolver('job-123', '  /api/video.mp4  ');

      expect(result).toBe('/api/video.mp4?token=xyz');
    });
  });
});
