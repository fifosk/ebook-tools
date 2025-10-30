import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { MediaSearchResponse, MediaSearchResult } from '../api/dtos';
import { searchMedia } from '../api/client';
import styles from './MediaSearchPanel.module.css';

type MediaCategory = 'text' | 'audio' | 'video';

interface MediaSearchPanelProps {
  onResultAction: (result: MediaSearchResult, category: MediaCategory) => void;
  currentJobId: string | null;
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

export default function MediaSearchPanel({ onResultAction, currentJobId }: MediaSearchPanelProps) {
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

  return (
    <div className={styles.searchPanel} aria-label="Search generated media">
      <form className={styles.searchHeader} onSubmit={handleSubmit}>
        <label className={styles.searchLabel} htmlFor="media-search-input">
          Search generated ebooks
        </label>
        <div className={styles.searchBar}>
          <input
            id="media-search-input"
            type="search"
            className={styles.searchInput}
            placeholder="Search by keyword, sentence, or phrase…"
            value={query}
            onChange={handleInputChange}
            autoComplete="off"
            disabled={!hasSelectedJob}
          />
          <button
            type="submit"
            className={styles.searchButton}
            disabled={!hasSelectedJob || (isSearching && activeQuery === query.trim())}
          >
            Search
          </button>
        </div>
      </form>

      {!hasSelectedJob ? (
        <div className={styles.status}>Select a job to enable media search.</div>
      ) : null}

      {showDropdown ? (
        <div className={styles.resultsDropdown} role="listbox">
          {isSearching ? <div className={styles.status}>Searching for matches…</div> : null}
          {error ? <div className={styles.error}>{error}</div> : null}
          {!isSearching && !error && hasResults ? (
            <div className={styles.resultsList}>
              {results.map((result) => {
                const categories: MediaCategory[] = (['text', 'audio', 'video'] as MediaCategory[]).filter(
                  (category) => Array.isArray(result.media?.[category]) && result.media?.[category]?.length,
                );
                const isActiveJob = currentJobId === result.job_id;

                return (
                  <article
                    key={`${result.job_id}-${result.chunk_id ?? result.base_id ?? result.snippet}`}
                    className={`${styles.resultItem} ${isActiveJob ? styles.resultItemActive : ''}`}
                    role="option"
                    aria-selected={isActiveJob}
                  >
                    <header className={styles.resultHeader}>
                      <div className={styles.resultTitle}>
                        {result.job_label ? result.job_label : `Job ${result.job_id}`}
                      </div>
                      <div className={styles.resultMeta}>
                        {result.range_fragment ? `Chunk ${result.range_fragment}` : 'Chunk'}
                        {typeof result.occurrence_count === 'number' && result.occurrence_count > 1
                          ? ` • ${result.occurrence_count} matches`
                          : ''}
                      </div>
                    </header>
                    <p className={styles.snippet}>{highlightSnippet(result.snippet, activeQuery)}</p>
                    {categories.length > 0 ? (
                      <div className={styles.resultActions}>
                        {categories.map((category) => (
                          <button
                            key={category}
                            type="button"
                            className={styles.actionButton}
                            onClick={() => {
                              onResultAction(result, category);
                              setQuery('');
                              setLastQuery('');
                              setResults([]);
                              setError(null);
                              setIsSearching(false);
                            }}
                          >
                            {category === 'text' ? 'Open text' : null}
                            {category === 'audio' ? 'Play audio' : null}
                            {category === 'video' ? 'Play video' : null}
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
