type MetadataLookupRowProps = {
  /** Current query value */
  query: string;
  /** Called when query input changes */
  onQueryChange: (value: string) => void;
  /** Called when lookup is triggered. force=true for refresh. */
  onLookup: (force: boolean) => void;
  /** Called when clear is triggered */
  onClear?: () => void;
  /** Whether a lookup operation is in progress */
  isLoading: boolean;
  /** Input placeholder text */
  placeholder?: string;
  /** Label for the input field */
  inputLabel?: string;
  /** Whether to show the clear button */
  showClear?: boolean;
  /** Whether buttons should be disabled (in addition to loading state) */
  disabled?: boolean;
  /** Whether lookup results exist (shows Refresh button) */
  hasResult?: boolean;
};

/**
 * A row containing a lookup query input and action buttons (Lookup, Refresh, Clear).
 * Provides consistent metadata lookup UX across all contexts.
 */
export function MetadataLookupRow({
  query,
  onQueryChange,
  onLookup,
  onClear,
  isLoading,
  placeholder = 'Enter query...',
  inputLabel = 'Lookup query',
  showClear = true,
  disabled = false,
  hasResult = false,
}: MetadataLookupRowProps) {
  const isDisabled = disabled || isLoading;
  const canLookup = !isDisabled && query.trim().length > 0;

  return (
    <div className="metadata-loader-row">
      <label style={{ marginBottom: 0 }}>
        {inputLabel}
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={placeholder}
          disabled={isDisabled}
        />
      </label>
      <div className="metadata-loader-actions">
        <button
          type="button"
          className="link-button"
          onClick={() => onLookup(false)}
          disabled={!canLookup}
          aria-busy={isLoading}
        >
          {isLoading ? 'Looking up…' : 'Lookup'}
        </button>
        {hasResult ? (
          <button
            type="button"
            className="link-button"
            onClick={() => onLookup(true)}
            disabled={isDisabled}
            aria-busy={isLoading}
          >
            Refresh
          </button>
        ) : null}
        {showClear && onClear ? (
          <button
            type="button"
            className="link-button link-button--danger"
            onClick={onClear}
            disabled={isDisabled}
          >
            Clear
          </button>
        ) : null}
      </div>
    </div>
  );
}
