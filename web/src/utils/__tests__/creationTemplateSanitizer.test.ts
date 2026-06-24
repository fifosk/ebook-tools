import { describe, expect, it } from 'vitest';
import { sanitizeTemplateValue } from '../creationTemplateSanitizer';

describe('creationTemplateSanitizer', () => {
  it('recursively strips secret-like keys while preserving safe values', () => {
    expect(
      sanitizeTemplateValue({
        title: 'Portable preset',
        api_key: 'drop-me',
        nested: {
          authHeader: 'drop-me',
          safe: true,
          list: [
            { access_token: 'drop-me', label: 'keep-me' },
            { password_hint: 'drop-me', count: 2 }
          ]
        }
      })
    ).toEqual({
      title: 'Portable preset',
      nested: {
        safe: true,
        list: [
          { label: 'keep-me' },
          { count: 2 }
        ]
      }
    });
  });
});
