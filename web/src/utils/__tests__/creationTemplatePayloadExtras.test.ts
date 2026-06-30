import { describe, expect, it } from 'vitest';
import {
  buildHandoffPayloadExtras,
  sanitizeCreationTemplatePayloadExtras
} from '../creationTemplatePayloadExtras';

describe('creationTemplatePayloadExtras', () => {
  it('normalizes safe handoff sources for template payloads', () => {
    expect(buildHandoffPayloadExtras(' Apple ')).toEqual({ handoff_source: 'apple' });
    expect(buildHandoffPayloadExtras('bad value')).toBeNull();
    expect(buildHandoffPayloadExtras('')).toBeNull();
  });

  it('drops reserved payload keys from extras', () => {
    expect(sanitizeCreationTemplatePayloadExtras({
      handoff_source: 'apple',
      source: 'malicious',
      version: 999,
      form_state: { input_file: 'wrong' },
      custom: true,
      nested: { api_token: 'drop-me', safe: 'keep-me' }
    })).toEqual({
      handoff_source: 'apple',
      custom: true,
      nested: { safe: 'keep-me' }
    });
  });
});
