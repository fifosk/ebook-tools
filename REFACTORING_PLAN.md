# Component Refactoring Plan

## Overview
This document outlines the plan for refactoring large components in the ebook-tools web application.

## Component Analysis

### 1. YoutubeDubPlayer (1,808 lines) - PRIORITY 1

**Current Issues:**
- Too many responsibilities in one component
- 20+ helper functions that should be extracted
- Complex state management with 15+ useState/useRef hooks
- Difficult to test and maintain

**Proposed Refactoring:**

#### Extract to: `src/components/youtube-player/`

1. **`MetadataResolver.ts`** - Pure utility functions
   - `replaceUrlExtension`
   - `readNestedValue`
   - `extractYoutubeDubMetadata`
   - `resolveYoutubeThumbnail`
   - `resolveYoutubeTitle`
   - `resolveYoutubeChannel`
   - `resolveYoutubeSummary`
   - Estimated: ~150 lines

2. **`SubtitleMetadataResolver.ts`** - TV metadata utilities
   - `resolveTvMetadataThumbnail`
   - `resolveTvMetadataSummary`
   - `resolveTvMetadataEpisodeLabel`
   - Estimated: ~100 lines

3. **`useYoutubePlayerState.ts`** - Custom hook for player state
   - All useState/useRef hooks
   - Playback controls state
   - Subtitle state
   - Font scaling state
   - Estimated: ~200 lines

4. **`useYoutubeMetadata.ts`** - Custom hook for metadata fetching
   - Fetch youtube metadata
   - Fetch TV metadata
   - Process and cache metadata
   - Estimated: ~150 lines

5. **`YoutubePlayerControls.tsx`** - UI component
   - Navigation controls
   - Playback controls
   - Subtitle controls
   - Estimated: ~300 lines

6. **`YoutubeDubPlayer.tsx`** - Main component (refactored)
   - Composition of extracted parts
   - Estimated: ~400 lines (down from 1,808)

**Benefits:**
- Each module has single responsibility
- Easier to test individual utilities
- Easier to reuse code
- Better code organization

---

### 2. VideoPlayer (1,679 lines) - PRIORITY 2

**Current Issues:**
- Massive component with video/audio player logic
- Complex subtitle sync
- Multiple player modes (video/audio)

**Proposed Refactoring:**

#### Extract to: `src/components/video-player/`

1. **`useVideoPlayerState.ts`** - State management hook
2. **`useSubtitleSync.ts`** - Subtitle synchronization logic
3. **`VideoControls.tsx`** - Video-specific controls
4. **`AudioPlayer.tsx`** - Audio-only player
5. **`SubtitleOverlay.tsx`** - Subtitle display component
6. **`VideoPlayer.tsx`** - Main component (refactored)

**Estimated Reduction:** 1,679 → ~500 lines

---

### 3. InteractiveTextViewer (1,613 lines) - PRIORITY 3

**Current Issues:**
- Complex text rendering with word-level highlighting
- Sentence navigation
- Image reel integration

**Proposed Refactoring:**

#### Extract to: `src/components/interactive-text/`

1. **`useTextHighlighting.ts`** - Word/sentence highlighting logic
2. **`useSentenceNavigation.ts`** - Navigation between sentences
3. **`TextRenderer.tsx`** - Text display component
4. **`WordHighlighter.tsx`** - Individual word highlighting
5. **`InteractiveTextViewer.tsx`** - Main component (refactored)

**Estimated Reduction:** 1,613 → ~400 lines

---

### 4. API Client (1,563 lines) - PRIORITY 4

**Current Issues:**
- All API calls in single file
- No clear separation by domain
- Hard to find specific endpoints

**Proposed Refactoring:**

#### Split into: `src/api/`

1. **`client/base.ts`** - Core fetch utilities, auth
2. **`client/jobs.ts`** - Job-related endpoints
3. **`client/library.ts`** - Library endpoints
4. **`client/media.ts`** - Media streaming endpoints
5. **`client/admin.ts`** - Admin endpoints
6. **`client/auth.ts`** - Authentication endpoints
7. **`client/index.ts`** - Re-export all

**Estimated Split:** 1,563 → 6 files of ~250 lines each

---

## Implementation Strategy

### Phase 1: Extract Utilities (Week 1)
- Focus on pure functions first
- Create new directories
- Extract and test utilities
- No breaking changes to main components yet

### Phase 2: Extract Custom Hooks (Week 2)
- Extract state management hooks
- Create unit tests for hooks
- Still no changes to main components

### Phase 3: Create Sub-Components (Week 3)
- Extract UI sub-components
- Test rendering and interactions
- Components use new hooks internally

### Phase 4: Refactor Main Components (Week 4)
- Update main components to use extracted parts
- Remove old code
- Integration testing

### Phase 5: API Client Split (Week 5)
- Split API client by domain
- Update all imports
- Ensure no breaking changes

### Phase 6: Testing & Documentation (Week 6)
- Comprehensive testing of refactored code
- Update documentation
- Performance validation

---

## Success Metrics

- **Lines per file:** Max 500 lines per component
- **Test coverage:** >80% for extracted utilities/hooks
- **Build time:** No regression
- **Bundle size:** No significant increase
- **Type safety:** No new `any` types

---

## Risks & Mitigation

**Risk:** Breaking existing functionality
- **Mitigation:** Comprehensive testing at each step, incremental changes

**Risk:** Import path changes
- **Mitigation:** Use path aliases, update all imports atomically

**Risk:** Bundle size increase from more files
- **Mitigation:** Verify tree-shaking works, monitor bundle size

---

## Next Steps

1. Get approval for this plan
2. Start with Phase 1 - Extract YoutubeDubPlayer utilities
3. Create unit tests for extracted utilities
4. Continue with Phase 2

---

**Status:** Draft - Awaiting approval
**Created:** 2026-01-23
**Owner:** Development Team
