# Translation Engine Refactoring Plan

> **Note:** Historical plan retained for context. The refactor has been
> completed; see `REFACTORING_SUMMARY.md` for the status recap.

## Current State
- **File**: `modules/translation_engine.py`
- **Lines**: 2,211
- **Functions**: 46 (43 functions + 3 classes)
- **Issues**: Single massive file with multiple responsibilities

## Analysis

The file contains several distinct functional areas that can be extracted:

### 1. **Validation & Quality Checks** (~200 lines)
Functions that validate translation quality and detect issues:
- `_valid_translation()` - Check if translation is valid
- `_letter_count()` - Count letters in text
- `_has_non_latin_letters()` - Detect non-Latin characters
- `_latin_fraction()` - Calculate Latin character ratio
- `_is_probable_transliteration()` - Detect transliteration instead of translation
- `_is_translation_too_short()` - Detect truncated translations
- `_missing_required_diacritics()` - Check for missing diacritics (Arabic/Hebrew)
- `_script_counts()` - Count characters per script block
- `_unexpected_script_used()` - Detect wrong script in translation
- `_is_segmentation_ok()` - Validate word segmentation

**Extract to**: `modules/translation_validation.py` (~250 lines with tests)

### 2. **GoogleTrans Provider** (~150 lines)
All Google Translate-specific functionality:
- `_check_googletrans_health()` - Health check for GoogleTrans
- `_normalize_translation_provider()` - Normalize provider names
- `_strip_googletrans_pseudo_suffix()` - Strip pseudo suffixes
- `_resolve_googletrans_language()` - Resolve language codes
- `_get_googletrans_translator()` - Get translator instance
- `_translate_with_googletrans()` - Translation implementation

**Extract to**: `modules/translation_providers/googletrans_provider.py` (~180 lines)

### 3. **Batch Processing** (~600 lines)
LLM batch translation and transliteration:
- `_normalize_llm_batch_size()` - Normalize batch size
- `_build_translation_batches()` - Build batches from items
- `_chunk_batch_items()` - Chunk batches by size
- `_extract_batch_items()` - Extract items from payload
- `_coerce_batch_item_id()` - Coerce item IDs
- `_coerce_text_value()` - Coerce text values
- `_parse_batch_translation_payload()` - Parse translation results
- `_parse_batch_transliteration_payload()` - Parse transliteration results
- `_validate_batch_translation()` - Validate batch translations
- `_validate_batch_transliteration()` - Validate batch transliterations
- `_translate_llm_batch_items()` - Translate batch with LLM
- `_transliterate_llm_batch_items()` - Transliterate batch with LLM
- `_resolve_batch_transliterations()` - Resolve transliterations
- `translate_batch()` - Main batch translation entry point

**Extract to**: `modules/translation_batch.py` (~700 lines with restructuring)

### 4. **Logging & Stats** (~150 lines)
Batch logging and statistics:
- `_BatchStatsRecorder` class - Record batch statistics
- `_resolve_llm_batch_log_dir()` - Resolve log directory
- `_sanitize_batch_component()` - Sanitize filenames
- `_write_llm_batch_artifact()` - Write batch logs

**Extract to**: `modules/translation_logging.py` (~180 lines)

### 5. **Worker Pools** (~150 lines)
Thread and async worker management:
- `ThreadWorkerPool` class - Thread-based worker pool
- `AsyncWorkerPool` class - Async worker pool

**Extract to**: `modules/translation_workers.py` (~180 lines)

### 6. **Text Processing Utilities** (~80 lines)
Small text utilities:
- Pattern matching (diacritics, zero-width spaces, etc.)
- Language constants and patterns
- Segmentation language detection

**Extract to**: `modules/translation_utils.py` (~100 lines)

### 7. **Core Translation Logic** (~500 lines - remains in translation_engine.py)
Keep the main translation orchestration:
- `TranslationTask` class
- `configure_default_client()`
- `translate_sentence_simple()` - Main single translation
- `_translate_with_llm()` - LLM translation implementation
- `start_translation_pipeline()` - Pipeline orchestration
- `_enqueue_with_backpressure()` - Queue management
- `_log_translation_timing()` - Timing logs
- `_is_timeout_error()` - Timeout detection
- `_should_include_transliteration()` - Transliteration decision

---

## Proposed Module Structure

```
modules/
├── translation_engine.py           (~500 lines) - Core orchestration
├── translation_validation.py       (~250 lines) - Quality checks
├── translation_batch.py             (~700 lines) - Batch processing
├── translation_logging.py           (~180 lines) - Logging & stats
├── translation_workers.py           (~180 lines) - Worker pools
├── translation_utils.py             (~100 lines) - Text utilities
└── translation_providers/
    ├── __init__.py
    ├── googletrans_provider.py      (~180 lines) - GoogleTrans
    └── base_provider.py             (~50 lines)  - Provider interface
```

**Total**: 2,211 lines → ~2,040 lines (accounting for imports/docs)

---

## Implementation Plan

### Phase 1: Extract Validation (Week 1)
1. Create `translation_validation.py`
2. Move all validation functions
3. Add comprehensive unit tests
4. Update imports in `translation_engine.py`

### Phase 2: Extract GoogleTrans Provider (Week 1)
1. Create `translation_providers/` package
2. Move GoogleTrans-specific code
3. Add unit tests with mocks
4. Update imports

### Phase 3: Extract Utilities (Week 2)
1. Create `translation_utils.py`
2. Move pattern constants and small helpers
3. Add tests
4. Update imports

### Phase 4: Extract Workers (Week 2)
1. Create `translation_workers.py`
2. Move worker pool classes
3. Add tests
4. Update imports

### Phase 5: Extract Logging (Week 3)
1. Create `translation_logging.py`
2. Move logging and stats classes
3. Add tests
4. Update imports

### Phase 6: Extract Batch Processing (Week 3-4)
1. Create `translation_batch.py`
2. Move all batch-related functions
3. Add comprehensive tests
4. Update imports

### Phase 7: Testing & Integration (Week 4)
1. Run full integration tests
2. Verify all translation modes work
3. Performance testing
4. Documentation updates

---

## Benefits

### Code Organization
- **Single Responsibility**: Each module has one clear purpose
- **Easier Navigation**: Find validation code in validation module
- **Reduced Complexity**: Smaller files are easier to understand

### Testability
- **Isolated Testing**: Test validation separately from translation
- **Mock Providers**: Easy to mock GoogleTrans for testing
- **Unit Test Coverage**: Can achieve >90% coverage per module

### Maintainability
- **Easier Debugging**: Know exactly where to look
- **Safer Changes**: Changes to validation don't risk batch logic
- **Better Imports**: Clear dependency graph

### Performance
- **Lazy Loading**: Only import what's needed
- **Parallel Development**: Multiple developers can work on different modules
- **Code Reuse**: Validation can be used outside translation context

---

## Success Metrics

- **Lines per file**: Max 700 lines per module
- **Test coverage**: >85% for each extracted module
- **Performance**: No regression in translation speed
- **Type safety**: Full type hints in all modules
- **Import time**: No significant increase in startup time

---

## Risks & Mitigation

**Risk**: Breaking existing translation pipelines
- **Mitigation**: Comprehensive integration tests before merging

**Risk**: Circular import dependencies
- **Mitigation**: Clear dependency hierarchy (utils → validation → providers → batch → engine)

**Risk**: Performance regression from more imports
- **Mitigation**: Profile before/after, use lazy imports if needed

---

## Next Steps

1. **Get approval** for this refactoring plan
2. **Start with Phase 1** - Extract validation (lowest risk, high value)
3. **Iterative approach** - One phase at a time with testing between
4. **Documentation** - Update module docs as we extract

---

**Status**: Proposal - Awaiting approval
**Created**: 2026-01-23
**Estimated Effort**: 4 weeks
**Priority**: Medium (improves maintainability, not urgent)
