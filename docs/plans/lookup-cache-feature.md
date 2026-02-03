# Lookup Cache Feature Implementation Plan

## Overview

Add a **word lookup cache** feature that pre-computes dictionary definitions for each unique word during batch translation, storing results in job metadata for instant access in the MyLinguist UI and iOS apps.

## Feature Specification

### User-Facing Changes

1. **New Toggle in Book Job UI** (Language Translation section):
   - Checkbox: "Cache word lookups during translation" (default: ON)
   - Help text: "Pre-compute dictionary lookups for unique words to enable instant definitions in the reader"

2. **MyLinguist Bubble Enhancement**:
   - When clicking a word, check cache first before making LLM call
   - Display cache indicator (subtle icon) when showing cached result
   - Fallback to live lookup if word not in cache

3. **Audio Seek Integration**:
   - Each cached word entry includes audio timing info (`t0`, `t1`) from the timing track
   - UI can play word pronunciation directly from existing audio track instead of TTS

---

## Technical Architecture

### 1. New Modules

#### `modules/lookup_cache/` - Core lookup cache logic

```
modules/lookup_cache/
├── __init__.py
├── models.py          # Data structures for cache entries
├── batch_lookup.py    # Batch lookup execution
├── cache_manager.py   # Cache loading/saving/querying
├── tokenizer.py       # Word extraction and normalization
└── prompt_builder.py  # LLM prompts for batch lookups
```

### 2. Data Structures

#### `LookupCacheEntry` (stored per word)

```python
@dataclass
class LookupCacheEntry:
    """A single cached word lookup result."""
    word: str                          # Normalized word form
    word_original: str                 # Original form as seen in text
    input_language: str                # Source language
    definition_language: str           # Language of the definition
    lookup_result: Dict[str, Any]      # Full LinguistLookupResult JSON
    audio_references: List[AudioRef]   # Where this word appears in audio
    created_at: float                  # Unix timestamp

@dataclass
class AudioRef:
    """Reference to word occurrence in audio."""
    chunk_id: str
    sentence_idx: int
    token_idx: int
    track: str           # 'original' | 'translation'
    t0: float            # Start time in seconds
    t1: float            # End time in seconds
```

#### `LookupCache` (per job)

```python
@dataclass
class LookupCache:
    """Job-level lookup cache container."""
    job_id: str
    input_language: str
    definition_language: str           # Target translation language
    entries: Dict[str, LookupCacheEntry]  # key = normalized word
    stats: LookupCacheStats
    version: str = "1.0"
```

### 3. Storage Location

```
storage/jobs/{job_id}/metadata/
├── lookup_cache.json              # Main cache file
├── lookup_cache_stats.json        # Statistics (hit rates, etc.)
└── llm_batches/
    └── lookup/                    # Batch request/response logs
        ├── batch_0001.json
        └── batch_0002.json
```

### 4. Integration Points

#### 4.1 Pipeline Integration

Modify `modules/translation_engine.py` to call lookup cache builder:

```python
# In translation_engine.py, after successful batch translation:
if config.enable_lookup_cache:
    from modules.lookup_cache import build_lookup_cache_batch

    unique_words = extract_unique_words(
        translated_sentences,
        input_language=input_language,
        existing_cache=current_cache
    )

    if unique_words:
        cache_entries = build_lookup_cache_batch(
            words=unique_words,
            input_language=input_language,
            definition_language=target_language,
            llm_client=resolved_client,
            batch_size=10,  # 10 words per LLM call
            batch_log_dir=batch_log_dir,
        )
        current_cache.update(cache_entries)
```

#### 4.2 Word Extraction Flow

```
Sentence Batch (10 sentences, ~100 words)
    │
    ▼
extract_unique_words()
    │ - Tokenize all sentences
    │ - Normalize (lowercase, strip punctuation)
    │ - Remove stopwords (configurable)
    │ - Deduplicate
    │ - Filter already-cached words
    ▼
Unique Words (~60 words after dedup)
    │
    ▼
chunk_into_batches(batch_size=10)
    │
    ▼
6 LLM Batch Calls
    │
    ▼
Merge into LookupCache
```

#### 4.3 Audio Reference Building

After audio timing is generated, link words to their audio positions:

```python
# In audio_pipeline.py or timeline.py, after word timing is computed:
def link_audio_references(
    lookup_cache: LookupCache,
    timing_tracks: Dict[str, List[TimingToken]],
    chunk_id: str,
) -> None:
    """Add audio references to cached words."""
    for track_name, tokens in timing_tracks.items():
        for token in tokens:
            normalized = normalize_word(token.text)
            if normalized in lookup_cache.entries:
                lookup_cache.entries[normalized].audio_references.append(
                    AudioRef(
                        chunk_id=chunk_id,
                        sentence_idx=token.sentence_idx,
                        token_idx=token.word_idx,
                        track=track_name,
                        t0=token.t0,
                        t1=token.t1,
                    )
                )
```

---

## API Changes

### 5.1 New Endpoint: Get Cached Lookup

```
GET /api/pipelines/jobs/{job_id}/lookup-cache/{word}
```

**Response:**
```json
{
  "word": "كتاب",
  "word_normalized": "كتاب",
  "cached": true,
  "lookup_result": {
    "type": "word",
    "definition": "book",
    "part_of_speech": "noun",
    "pronunciation": "kitāb",
    "etymology": "From Arabic root k-t-b (to write)",
    "example": "هذا كتاب جميل",
    "example_translation": "This is a beautiful book",
    "related_languages": [
      {"language": "Persian", "word": "کتاب", "transliteration": "ketāb"},
      {"language": "Turkish", "word": "kitap"}
    ]
  },
  "audio_references": [
    {
      "chunk_id": "chunk_0001",
      "sentence_idx": 5,
      "token_idx": 2,
      "track": "translation",
      "t0": 12.45,
      "t1": 13.02
    }
  ]
}
```

### 5.2 Bulk Cache Endpoint

```
POST /api/pipelines/jobs/{job_id}/lookup-cache/bulk
```

**Request:**
```json
{
  "words": ["كتاب", "مكتبة", "كاتب"]
}
```

**Response:**
```json
{
  "results": {
    "كتاب": { /* LookupCacheEntry */ },
    "مكتبة": { /* LookupCacheEntry */ },
    "كاتب": null  // Not in cache
  },
  "cache_hits": 2,
  "cache_misses": 1
}
```

### 5.3 Extended Media Endpoint

Modify existing `/api/pipelines/jobs/{job_id}/media` to include cache availability:

```json
{
  "media": { ... },
  "chunks": [ ... ],
  "lookup_cache": {
    "available": true,
    "word_count": 847,
    "input_language": "Arabic",
    "definition_language": "English"
  }
}
```

---

## Frontend Changes

### 6.1 Job Creation Form

**File:** `web/src/components/book-narration/BookNarrationLanguageSection.tsx`

Add new checkbox after transliteration mode:

```tsx
<label className="checkbox">
  <input
    type="checkbox"
    name="enable_lookup_cache"
    checked={enableLookupCache}
    onChange={(e) => onEnableLookupCacheChange(e.target.checked)}
  />
  Cache word lookups during translation
</label>
<small className="form-help-text">
  Pre-compute dictionary lookups for unique words. Enables instant definitions
  in the interactive reader without additional LLM calls.
</small>
```

### 6.2 MyLinguist Bubble Enhancement

**File:** `web/src/components/interactive-text/useLinguistBubbleLookup.ts`

```typescript
async function lookupWord(word: string, jobId: string): Promise<LookupResult> {
  // 1. Check cache first
  if (jobId) {
    const cacheResult = await fetchCachedLookup(jobId, word);
    if (cacheResult) {
      return {
        ...cacheResult.lookup_result,
        source: 'cache',
        audioRef: cacheResult.audio_references[0] ?? null,
      };
    }
  }

  // 2. Fallback to live LLM lookup
  const liveResult = await assistantLookup({
    query: word,
    input_language: inputLanguage,
    lookup_language: lookupLanguage,
  });

  return {
    ...parseLinguistLookupResult(liveResult.answer),
    source: 'live',
    audioRef: null,
  };
}
```

### 6.3 Audio Playback from Cache

**File:** `web/src/components/interactive-text/MyLinguistBubble.tsx`

Add "Play from audio" button when audio reference is available:

```tsx
{audioRef && (
  <button
    type="button"
    className="player-panel__my-linguist-bubble-play-audio"
    onClick={() => onPlayAudioRef(audioRef)}
    title="Play word from narration audio"
  >
    🔊
  </button>
)}
```

The `onPlayAudioRef` handler seeks the audio player to `audioRef.t0` and plays until `audioRef.t1`.

---

## iOS Changes

### 7.1 New Model File

**File:** `ios/InteractiveReader/InteractiveReader/Models/LookupCache.swift`

```swift
struct LookupCacheEntry: Codable, Equatable {
    let word: String
    let wordOriginal: String
    let inputLanguage: String
    let definitionLanguage: String
    let lookupResult: LinguistLookupResult
    let audioReferences: [AudioRef]
    let createdAt: Double
}

struct AudioRef: Codable, Equatable, Hashable {
    let chunkId: String
    let sentenceIdx: Int
    let tokenIdx: Int
    let track: String
    let t0: Double
    let t1: Double
}

struct LookupCache: Codable {
    let jobId: String
    let inputLanguage: String
    let definitionLanguage: String
    let entries: [String: LookupCacheEntry]
    let version: String
}
```

### 7.2 Cache Manager

**File:** `ios/InteractiveReader/InteractiveReader/Services/LookupCacheManager.swift`

```swift
actor LookupCacheManager {
    private var cache: LookupCache?
    private let apiService: APIServiceProtocol

    func loadCache(for jobId: String) async throws {
        // Fetch from /api/pipelines/jobs/{jobId}/media and extract lookup_cache
        // Or fetch dedicated endpoint
    }

    func lookup(_ word: String) -> LookupCacheEntry? {
        let normalized = normalizeWord(word)
        return cache?.entries[normalized]
    }

    private func normalizeWord(_ word: String) -> String {
        word.lowercased()
            .trimmingCharacters(in: .punctuationCharacters)
            .trimmingCharacters(in: .whitespaces)
    }
}
```

### 7.3 Linguist Bubble Integration

Modify `InteractivePlayerView+Linguist.swift`:

```swift
func performLookup(for word: String) async {
    // Check cache first
    if let cached = lookupCacheManager.lookup(word) {
        await MainActor.run {
            self.linguistBubbleState = LinguistBubbleState(
                query: word,
                status: .ready,
                answer: nil,  // Use parsedResult directly
                model: "cached"
            )
            self.linguistBubbleParsedResult = cached.lookupResult
            self.linguistAudioRef = cached.audioReferences.first
        }
        return
    }

    // Fallback to live API call
    // ... existing implementation
}
```

---

## LLM Batch Prompt for Lookups

### 8.1 System Prompt

**File:** `modules/lookup_cache/prompt_builder.py`

```python
def build_batch_lookup_system_prompt(
    input_language: str,
    definition_language: str,
) -> str:
    return f"""You are MyLinguist, a dictionary assistant.
You will receive a batch of words in {input_language}.
For each word, provide a dictionary entry in {definition_language}.

Return ONLY valid JSON in this exact format:
{{
  "items": [
    {{
      "id": 0,
      "word": "original word",
      "type": "word",
      "definition": "Main definition (required)",
      "part_of_speech": "noun/verb/adj/etc or null",
      "pronunciation": "IPA or common reading, or null",
      "etymology": "Brief origin/root, or null",
      "example": "Short example usage, or null",
      "example_translation": "Translation of example, or null",
      "related_languages": [
        {{"language": "Persian", "word": "کتاب", "transliteration": "ketāb"}}
      ]
    }}
  ]
}}

Rules:
- Keep definitions concise (one line)
- Include pronunciation for non-Latin scripts
- Include transliteration for related_languages entries with non-Latin scripts
- If uncertain about etymology, use null (do NOT guess)
- For Arabic: include full tashkīl/harakāt (diacritics)
- For Hebrew: include full niqqud (vowel points)
"""
```

### 8.2 Batch Request Format

```json
{
  "items": [
    {"id": 0, "text": "كتاب"},
    {"id": 1, "text": "مكتبة"},
    {"id": 2, "text": "كاتب"},
    {"id": 3, "text": "كتابة"},
    {"id": 4, "text": "مكتوب"}
  ]
}
```

---

## Configuration

### 9.1 Pipeline Input Payload

**File:** `web/src/api/dtos.ts`

```typescript
export interface PipelineInputPayload {
  // ... existing fields
  enable_lookup_cache?: boolean;
  lookup_cache_batch_size?: number;  // Default: 10
  lookup_cache_skip_stopwords?: boolean;  // Default: true
}
```

### 9.2 Backend Config

**File:** `conf/config.json`

```json
{
  "lookup_cache": {
    "enabled": true,
    "batch_size": 10,
    "skip_stopwords": true,
    "min_word_length": 2,
    "max_words_per_job": 10000,
    "timeout_seconds": 30
  }
}
```

---

## Implementation Order

### Phase 1: Backend Foundation
1. Create `modules/lookup_cache/` module structure
2. Implement `models.py` with data structures
3. Implement `tokenizer.py` for word extraction
4. Implement `prompt_builder.py` for LLM prompts
5. Implement `batch_lookup.py` for LLM batch calls
6. Implement `cache_manager.py` for persistence

### Phase 2: Pipeline Integration
7. Add `enable_lookup_cache` to pipeline input schema
8. Integrate lookup cache building into `translation_engine.py`
9. Add audio reference linking in `audio_pipeline.py`
10. Add cache persistence to job metadata

### Phase 3: API Endpoints
11. Create `/api/pipelines/jobs/{job_id}/lookup-cache/{word}` endpoint
12. Create `/api/pipelines/jobs/{job_id}/lookup-cache/bulk` endpoint
13. Extend `/api/pipelines/jobs/{job_id}/media` with cache info

### Phase 4: Web Frontend
14. Add checkbox to `BookNarrationLanguageSection.tsx`
15. Update `useLinguistBubbleLookup.ts` to check cache
16. Add audio playback button to `MyLinguistBubble.tsx`
17. Wire up cache status display

### Phase 5: iOS Integration
18. Add `LookupCache.swift` model
19. Create `LookupCacheManager.swift` service
20. Integrate into `InteractivePlayerView+Linguist.swift`
21. Add audio seek functionality

### Phase 6: Testing & Polish
22. Add unit tests for tokenizer and cache manager
23. Add integration tests for batch lookup
24. Test iOS and web end-to-end
25. Performance tuning and documentation

---

## Migration & Compatibility

- **Existing jobs**: Cache will be `null` - fallback to live lookup works
- **New jobs**: Cache is built during translation if enabled
- **Partial cache**: Missing words fall back to live lookup seamlessly
- **Backward compatible**: No breaking changes to existing APIs

---

## Performance Considerations

1. **Batch size**: 10 words/call balances latency vs throughput
2. **Deduplication**: Cache lookup before each batch prevents redundant calls
3. **Lazy loading**: iOS/web load cache on demand, not at app start
4. **Memory**: For 10K words × ~500 bytes = ~5MB per job (acceptable)
5. **Audio refs**: Only store first occurrence to limit growth

---

## Open Questions

1. Should we cache transliterated words separately or together?
2. Should we expose cache statistics in the UI?
3. Should we allow manual cache refresh/rebuild?
4. Should we cache phrases (multi-word) in addition to single words?
