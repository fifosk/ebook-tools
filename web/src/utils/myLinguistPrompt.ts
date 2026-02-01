export const MY_LINGUIST_SOURCE_START = '<<<BEGIN_SOURCE_TEXT>>>';
export const MY_LINGUIST_SOURCE_END = '<<<END_SOURCE_TEXT>>>';

export interface LinguistLookupResult {
  type: 'word' | 'phrase' | 'sentence';
  definition: string;
  part_of_speech?: string | null;
  pronunciation?: string | null;
  etymology?: string | null;
  example?: string | null;
  example_translation?: string | null;
  example_transliteration?: string | null;
  idioms?: string[] | null;
  related_languages?: Array<{
    language: string;
    word: string;
    transliteration?: string | null;
  }> | null;
}

/**
 * Attempt to parse a JSON response from the LLM answer string.
 * Returns null if the answer is not valid JSON or doesn't match the expected structure.
 */
export function parseLinguistLookupResult(answer: string): LinguistLookupResult | null {
  const trimmed = answer.trim();

  // Find JSON object bounds
  const startIndex = trimmed.indexOf('{');
  const endIndex = trimmed.lastIndexOf('}');

  if (startIndex === -1 || endIndex === -1 || endIndex <= startIndex) {
    return null;
  }

  const jsonString = trimmed.slice(startIndex, endIndex + 1);

  try {
    const parsed = JSON.parse(jsonString) as unknown;
    // Validate minimal required structure
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'definition' in parsed &&
      typeof (parsed as { definition: unknown }).definition === 'string'
    ) {
      return parsed as LinguistLookupResult;
    }
    return null;
  } catch {
    return null;
  }
}

export function buildMyLinguistSystemPrompt(inputLanguage: string, lookupLanguage: string): string {
  const resolvedInput = inputLanguage.trim() || 'the input language';
  const resolvedLookup = lookupLanguage.trim() || 'English';
  return [
    'You are MyLinguist, a fast lookup dictionary assistant.',
    `The user will provide a word, phrase, or sentence in ${resolvedInput}.`,
    `Respond in ${resolvedLookup}.`,
    `The user's text is between the markers ${MY_LINGUIST_SOURCE_START} and ${MY_LINGUIST_SOURCE_END}.`,
    'Never include those markers (or variations such as <<<, >>>, <<, >>) in your response.',
    'Be concise and helpful. Avoid filler, safety disclaimers, and meta commentary.',
    '',
    'You MUST respond with a valid JSON object. No text before or after the JSON.',
    'Use this exact structure:',
    '',
    '{',
    '  "type": "word" | "phrase" | "sentence",',
    '  "definition": "Main definition or meaning (required)",',
    '  "part_of_speech": "noun/verb/adj/etc or null",',
    '  "pronunciation": "IPA or common reading, or null",',
    '  "etymology": "Brief origin/root, or null if uncertain",',
    '  "example": "One short example usage, or null",',
    '  "example_translation": "Translation of example in the lookup language, or null",',
    '  "example_transliteration": "Romanized version of example if non-Latin, or null",',
    '  "idioms": ["List of idioms if sentence type, or null"],',
    '  "related_languages": [',
    '    {"language": "Persian", "word": "کتاب", "transliteration": "ketāb"},',
    '    {"language": "Turkish", "word": "kitap", "transliteration": null}',
    '  ]',
    '}',
    '',
    'Rules:',
    "- type: 'word' for single words, 'phrase' for short phrases, 'sentence' for full sentences",
    '- definition: REQUIRED. One-line definition for words/phrases, brief meaning/paraphrase for sentences',
    '- part_of_speech: Include when clear (noun, verb, adjective, adverb, etc.), null otherwise',
    '- pronunciation: IPA or common reading if known, null if not',
    '- etymology: Brief origin/root if you know it. If uncertain, use null (do NOT guess)',
    '- example: One short example usage, null if not needed',
    '- example_translation: Translation of the example sentence in the lookup language. Always provide when example is in a different language than the lookup language',
    '- example_transliteration: If the example sentence uses non-Latin script, provide the romanized transliteration here. null if Latin script or no example',
    '- idioms: For sentences only, list key idioms or tricky segments. null for words/phrases',
    '- related_languages: For words/phrases, show 3 related languages. Include transliteration for non-Latin scripts. null for sentences',
    '',
    'IMPORTANT: For any non-Latin scripts (Arabic, Chinese, Japanese, Korean, Hebrew, Russian, Greek, Thai, Hindi, etc.), ALWAYS include transliteration:',
    '- In the transliteration field for related_languages entries',
    '- In the example_transliteration field when the example sentence uses non-Latin script',
    '',
    'Keep the response concise. Omit fields that are not applicable by setting them to null.',
  ].join('\n');
}

