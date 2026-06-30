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
          privateKey: 'drop-me',
          credential: 'drop-me',
          safe: true,
          list: [
            { access_token: 'drop-me', label: 'keep-me' },
            { password_hint: 'drop-me', count: 2 },
            { csrfHeader: 'drop-me', count: 3 }
          ]
        }
      })
    ).toEqual({
      title: 'Portable preset',
      nested: {
        safe: true,
        list: [
          { label: 'keep-me' },
          { count: 2 },
          { count: 3 }
        ]
      }
    });
  });

  it('recursively strips credential-bearing public URL parts', () => {
    expect(
      sanitizeTemplateValue({
        source_url:
          'https://user:secret@indexer.example.invalid/download/7?title=Demo&apikey=secret#name=Demo&access_token=secret',
        nested: {
          plain: 'not a url with access_token=left as ordinary text',
          magnet: 'magnet:?xt=urn:btih:abc&passkey=secret&dn=Demo'
        }
      })
    ).toEqual({
      source_url: 'https://indexer.example.invalid/download/7?title=Demo#name=Demo',
      nested: {
        plain: 'not a url with access_token=left as ordinary text',
        magnet: 'magnet:?xt=urn%3Abtih%3Aabc&dn=Demo'
      }
    });
  });
});
