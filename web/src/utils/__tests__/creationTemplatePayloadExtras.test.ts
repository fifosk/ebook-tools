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
      handoff_source: ' Apple ',
      source: 'malicious',
      version: 999,
      form_state: { input_file: 'wrong' },
      custom: true,
      nested: { api_token: 'drop-me', safe: 'keep-me' }
    })).toEqual({
      custom: true,
      nested: { safe: 'keep-me' },
      handoff_source: 'apple'
    });
  });

  it('canonicalizes camel-case handoff extras and drops invalid values', () => {
    expect(sanitizeCreationTemplatePayloadExtras({
      handoffSource: ' Apple ',
      source: 'malicious'
    })).toEqual({ handoff_source: 'apple' });
    expect(sanitizeCreationTemplatePayloadExtras({
      handoff_source: 'bad value',
      handoffSource: 'also bad'
    })).toEqual({});
  });
});
