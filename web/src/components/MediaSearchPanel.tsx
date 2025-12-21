import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent
} from 'react';
import { MediaSearchResponse, MediaSearchResult } from '../api/dtos';
import { searchMedia } from '../api/client';
import styles from './MediaSearchPanel.module.css';

type MediaCategory = 'text' | 'video' | 'library';
const BASE_MEDIA_CATEGORIES: Array<Exclude<MediaCategory, 'library'>> = ['text', 'video'];

interface MediaSearchPanelProps {
  onResultAction: (result: MediaSearchResult, category: MediaCategory) => void;
  currentJobId: string | null;
  variant?: 'panel' | 'compact';
}

interface SearchQueueEntry {
  query: string;
  requestId: number;
}

const SEARCH_LIMIT = 25;
const DEBOUNCE_MS = 300;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightSnippet(snippet: string, term: string): Array<string | JSX.Element> {
  if (!snippet || !term) {
    return [snippet];
  }

  const highlights: Array<string | JSX.Element> = [];
  const regex = new RegExp(escapeRegExp(term), 'gi');

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(snippet)) !== null) {
    const start = match.index;
    const end = start + match[0].length;

    if (start > lastIndex) {
      highlights.push(snippet.slice(lastIndex, start));
    }

    highlights.push(
      <mark key={`${start}-${end}`}>
        {snippet.slice(start, end)}
      </mark>,
    );

    lastIndex = end;
  }

  if (lastIndex < snippet.length) {
    highlights.push(snippet.slice(lastIndex));
  }

  return highlights;
}

export default function MediaSearchPanel({
  onResultAction,
  currentJobId,
  variant = 'panel',
}: MediaSearchPanelProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<MediaSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState('');
  const requestRef = useRef<SearchQueueEntry>({ query: '', requestId: 0 });
  const debounceRef = useRef<number | undefined>(undefined);
  const hasSelectedJob = Boolean(currentJobId);

  const clearDebounce = useCallback(() => {
    if (debounceRef.current !== undefined) {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = undefined;
    }
  }, []);

  const runSearch = useCallback(async (jobId: string, term: string, requestId: number) => {
    try {
      const response: MediaSearchResponse = await searchMedia(jobId, term, SEARCH_LIMIT);
      if (requestRef.current.requestId !== requestId) {
        return;
      }
      setResults(response.results ?? []);
      setError(null);
      setLastQuery(response.query ?? term);
    } catch (searchError) {
      if (requestRef.current.requestId !== requestId) {
        return;
      }
      const message =
        searchError instanceof Error ? searchError.message : 'Unable to search generated media.';
      setResults([]);
      setError(message);
    } finally {
      if (requestRef.current.requestId === requestId) {
        setIsSearching(false);
      }
    }
  }, []);

  useEffect(() => {
    const trimmed = query.trim();
    clearDebounce();

    if (!currentJobId) {
      setResults([]);
      setError(null);
      setIsSearching(false);
      setLastQuery('');
      return undefined;
    }

    if (!trimmed) {
      setResults([]);
      setError(null);
      setIsSearching(false);
      setLastQuery('');
      return undefined;
    }

    const nextRequestId = requestRef.current.requestId + 1;
    requestRef.current = { query: trimmed, requestId: nextRequestId };
    setIsSearching(true);

    debounceRef.current = window.setTimeout(() => {
      runSearch(currentJobId, trimmed, nextRequestId);
    }, DEBOUNCE_MS);

    return clearDebounce;
  }, [currentJobId, query, clearDebounce, runSearch]);

  useEffect(() => () => clearDebounce(), [clearDebounce]);

  useEffect(() => {
    if (!currentJobId) {
      setQuery('');
      setLastQuery('');
      setResults([]);
      setIsSearching(false);
      setError(null);
    }
  }, [currentJobId]);

  const handleInputChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value);
  }, []);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = query.trim();
      if (!trimmed || !currentJobId) {
        setResults([]);
        setError(null);
        setIsSearching(false);
        setLastQuery('');
        return;
      }
      clearDebounce();
      const nextRequestId = requestRef.current.requestId + 1;
      requestRef.current = { query: trimmed, requestId: nextRequestId };
      setIsSearching(true);
      void runSearch(currentJobId, trimmed, nextRequestId);
    },
    [currentJobId, query, clearDebounce, runSearch],
  );

  const hasResults = results.length > 0;
  const activeQuery = useMemo(() => lastQuery || query.trim(), [lastQuery, query]);
  const trimmedQuery = query.trim();
  const showDropdown = hasSelectedJob && trimmedQuery.length > 0;
  const applyResultAction = useCallback(
    (result: MediaSearchResult, category: MediaCategory) => {
      onResultAction(result, category);
      setQuery('');
      setLastQuery('');
      setResults([]);
      setError(null);
      setIsSearching(false);
    },
    [onResultAction],
  );

  const isCompact = variant === 'compact';
  const panelClassName = [styles.searchPanel, isCompact ? styles.searchPanelCompact : null]
    .filter(Boolean)
    .join(' ');
  const headerClassName = [styles.searchHeader, isCompact ? styles.searchHeaderCompact : null]
    .filter(Boolean)
    .join(' ');
  const barClassName = [styles.searchBar, isCompact ? styles.searchBarCompact : null]
    .filter(Boolean)
    .join(' ');
  const inputClassName = [styles.searchInput, isCompact ? styles.searchInputCompact : null]
    .filter(Boolean)
    .join(' ');
  const buttonClassName = [styles.searchButton, isCompact ? styles.searchButtonCompact : null]
    .filter(Boolean)
    .join(' ');
  const dropdownClassName = [styles.resultsDropdown, isCompact ? styles.resultsDropdownCompact : null]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={panelClassName} aria-label="Search generated media">
      <form className={headerClassName} onSubmit={handleSubmit}>
        <div className={barClassName}>
          <input
            type="search"
            className={inputClassName}
            placeholder="Search"
            value={query}
            onChange={handleInputChange}
            autoComplete="off"
            disabled={!hasSelectedJob}
            aria-label="Search generated ebooks"
          />
          <button
            type="submit"
            className={buttonClassName}
            disabled={!hasSelectedJob || (isSearching && activeQuery === query.trim())}
          >
            {isCompact ? 'Go' : 'Search'}
          </button>
        </div>
      </form>

      {!hasSelectedJob ? (
        <div className={styles.status}>Select a job to enable media search.</div>
      ) : null}

      {showDropdown ? (
        <div className={dropdownClassName} role="listbox">
          {isSearching ? <div className={styles.status}>Searching for matches…</div> : null}
          {error ? <div className={styles.error}>{error}</div> : null}
          {!isSearching && !error && hasResults ? (
            <div className={styles.resultsList}>
              {results.map((result) => {
                const isLibraryResult = result.source === 'library';
                const categories: MediaCategory[] = [];
                const canOpenText =
                  !isLibraryResult &&
                  (Boolean(result.base_id) ||
                    Boolean(result.chunk_id) ||
                    Boolean(result.range_fragment) ||
                    typeof result.chunk_index === 'number' ||
                    typeof result.start_sentence === 'number' ||
                    typeof result.end_sentence === 'number' ||
                    typeof result.offset_ratio === 'number' ||
                    (Array.isArray(result.media?.text) && (result.media?.text?.length ?? 0) > 0));
                if (isLibraryResult) {
                  categories.push('library');
                } else if (canOpenText) {
                  categories.push('text');
                }
                BASE_MEDIA_CATEGORIES.forEach((category) => {
                  if (category === 'text' && categories.includes('text')) {
                    return;
                  }
                  if (Array.isArray(result.media?.[category]) && (result.media?.[category]?.length ?? 0) > 0) {
                    categories.push(category);
                  }
                });
                const isActiveJob = currentJobId === result.job_id;
                const chunkIndexValue =
                  typeof result.chunk_index === 'number' && Number.isFinite(result.chunk_index)
                    ? result.chunk_index
                    : null;
                const chunkTotalValue =
                  typeof result.chunk_total === 'number' && Number.isFinite(result.chunk_total)
                    ? result.chunk_total
                    : null;
                const chunkPositionLabel = (() => {
                  if (chunkIndexValue === null) {
                    return null;
                  }
                  const humanIndex = chunkIndexValue + 1;
                  if (chunkTotalValue && chunkTotalValue > 0) {
                    return `Chunk ${humanIndex} of ${chunkTotalValue}`;
                  }
                  return `Chunk ${humanIndex}`;
                })();
                const chunkRangeLabel = result.range_fragment ? `Sentences ${result.range_fragment}` : null;

                let metaText: string;
                if (isLibraryResult) {
                  const libraryParts = [
                    result.libraryAuthor ? `Author ${result.libraryAuthor}` : null,
                    result.libraryLanguage ? `Language ${result.libraryLanguage}` : null,
                    result.libraryGenre ? `Genre ${result.libraryGenre}` : null
                  ].filter((entry): entry is string => Boolean(entry));

                  const chunkSummary =
                    chunkPositionLabel && chunkRangeLabel
                      ? `${chunkPositionLabel} (${chunkRangeLabel})`
                      : chunkPositionLabel ?? chunkRangeLabel;
                  if (chunkSummary) {
                    libraryParts.push(chunkSummary);
                  }

                  metaText = libraryParts.join(' · ');
                  if (!metaText) {
                    metaText = 'Library entry';
                  }
                } else {
                  const pipelineParts: string[] = [];
                  if (chunkPositionLabel) {
                    pipelineParts.push(chunkPositionLabel);
                  }
                  if (chunkRangeLabel) {
                    pipelineParts.push(chunkRangeLabel);
                  }
                  let pipelineMeta = pipelineParts.join(' • ');
                  if (!pipelineMeta) {
                    pipelineMeta = 'Chunk';
                  }
                  if (
                    typeof result.occurrence_count === 'number' &&
                    result.occurrence_count > 1
                  ) {
                    pipelineMeta = `${pipelineMeta} • ${result.occurrence_count} matches`;
                  }
                  metaText = pipelineMeta;
                }

                const primaryCategory: MediaCategory | null = categories.includes('text')
                  ? 'text'
                  : categories.includes('library')
                  ? 'library'
                  : categories.includes('video')
                  ? 'video'
                  : null;
                const isClickable = primaryCategory !== null;
                const primaryActionLabel =
                  primaryCategory === 'text'
                    ? 'Jump to sentence'
                    : primaryCategory === 'video'
                    ? 'Play video'
                    : primaryCategory === 'library'
                    ? 'Open in Reader'
                    : undefined;

                return (
                  <article
                    key={`${result.job_id}-${result.chunk_id ?? result.base_id ?? result.snippet}`}
                    className={`${styles.resultItem} ${isActiveJob ? styles.resultItemActive : ''} ${isClickable ? styles.resultItemClickable : ''}`}
                    role="option"
                    aria-selected={isActiveJob}
                    tabIndex={isClickable ? 0 : -1}
                    title={primaryActionLabel}
                    onClick={() => {
                      if (primaryCategory) {
                        applyResultAction(result, primaryCategory);
                      }
                    }}
                    onKeyDown={(event) => {
                      if (!primaryCategory) {
                        return;
                      }
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        applyResultAction(result, primaryCategory);
                      }
                    }}
                  >
                    <header className={styles.resultHeader}>
                      <div className={styles.resultTitle}>
                        {isLibraryResult
                          ? result.job_label ?? `Library ${result.job_id}`
                          : result.job_label ?? `Job ${result.job_id}`}
                      </div>
                      <div className={styles.resultMeta}>{metaText}</div>
                    </header>
                    <p className={styles.snippet}>{highlightSnippet(result.snippet, activeQuery)}</p>
                    {categories.length > 0 ? (
                      <div className={styles.resultActions}>
                        {categories.map((category) => (
                          <button
                            key={category}
                            type="button"
                            className={styles.actionButton}
                            onClick={(event) => {
                              event.stopPropagation();
                              applyResultAction(result, category);
                            }}
                          >
                            {category === 'text' ? 'Jump to sentence' : null}
                            {category === 'video' ? 'Play video' : null}
                            {category === 'library' ? 'Open in Reader' : null}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          ) : null}
          {!isSearching && !error && !hasResults ? (
            <div className={styles.emptyState}>No matches yet. Try a different keyword.</div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
