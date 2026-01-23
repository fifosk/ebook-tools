import { describe, it, expect } from 'vitest';
import { replaceUrlExtension, readNestedValue, coerceRecord, readStringValue } from '../utils';

describe('Youtube Player Utils', () => {
  describe('replaceUrlExtension', () => {
    it('should replace file extension', () => {
      expect(replaceUrlExtension('video.mp4', '.webm')).toBe('video.webm');
    });

    it('should preserve query parameters', () => {
      expect(replaceUrlExtension('video.mp4?id=123', '.webm')).toBe('video.webm?id=123');
    });

    it('should preserve hash fragment', () => {
      expect(replaceUrlExtension('video.mp4#t=10', '.webm')).toBe('video.webm#t=10');
    });

    it('should preserve both query and hash', () => {
      expect(replaceUrlExtension('video.mp4?id=123#t=10', '.webm')).toBe('video.webm?id=123#t=10');
    });

    it('should return null for empty string', () => {
      expect(replaceUrlExtension('', '.webm')).toBeNull();
      expect(replaceUrlExtension('   ', '.webm')).toBeNull();
    });

    it('should return null for path without extension', () => {
      expect(replaceUrlExtension('video', '.webm')).toBeNull();
    });
  });

  describe('readNestedValue', () => {
    it('should read nested object values', () => {
      const obj = { a: { b: { c: 42 } } };
      expect(readNestedValue(obj, ['a', 'b', 'c'])).toBe(42);
    });

    it('should return null for missing paths', () => {
      const obj = { a: { b: {} } };
      expect(readNestedValue(obj, ['a', 'b', 'c'])).toBeNull();
    });

    it('should return null for non-object values in path', () => {
      const obj = { a: 'string' };
      expect(readNestedValue(obj, ['a', 'b'])).toBeNull();
    });

    it('should handle empty path', () => {
      const obj = { a: 42 };
      expect(readNestedValue(obj, [])).toEqual(obj);
    });
  });

  describe('coerceRecord', () => {
    it('should return object as Record', () => {
      const obj = { key: 'value' };
      expect(coerceRecord(obj)).toEqual(obj);
    });

    it('should return null for non-objects', () => {
      expect(coerceRecord('string')).toBeNull();
      expect(coerceRecord(42)).toBeNull();
      expect(coerceRecord(null)).toBeNull();
      expect(coerceRecord(undefined)).toBeNull();
    });

    it('should return null for arrays', () => {
      expect(coerceRecord([1, 2, 3])).toBeNull();
    });
  });

  describe('readStringValue', () => {
    it('should read string values from record', () => {
      const obj = { key: 'value' };
      expect(readStringValue(obj, 'key')).toBe('value');
    });

    it('should trim strings', () => {
      const obj = { key: '  value  ' };
      expect(readStringValue(obj, 'key')).toBe('value');
    });

    it('should return null for empty/whitespace strings', () => {
      expect(readStringValue({ key: '' }, 'key')).toBeNull();
      expect(readStringValue({ key: '   ' }, 'key')).toBeNull();
    });

    it('should return null for non-string values', () => {
      expect(readStringValue({ key: 42 }, 'key')).toBeNull();
      expect(readStringValue({ key: null }, 'key')).toBeNull();
      expect(readStringValue({ key: undefined }, 'key')).toBeNull();
    });

    it('should return null for missing keys', () => {
      expect(readStringValue({}, 'key')).toBeNull();
    });

    it('should return null for null/undefined source', () => {
      expect(readStringValue(null, 'key')).toBeNull();
      expect(readStringValue(undefined, 'key')).toBeNull();
    });
  });
});
