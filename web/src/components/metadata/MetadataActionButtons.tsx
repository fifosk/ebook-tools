type MetadataActionButtonsProps = {
  /** Called when lookup is triggered (force=false) */
  onLookup?: (force: boolean) => void;
  /** Called when clear is triggered */
  onClear?: () => void;
  /** Whether an operation is in progress */
  isLoading: boolean;
  /** Whether lookup results exist */
  hasResult: boolean;
  /** Whether buttons should be disabled */
  disabled?: boolean;
  /** Custom label for the lookup button */
  lookupLabel?: string;
};

/**
 * Action buttons for metadata operations (Lookup, Refresh, Clear).
 * Used in job cards and other contexts where the query input is separate or auto-populated.
 */
export function MetadataActionButtons({
  onLookup,
  onClear,
  isLoading,
  hasResult,
  disabled = false,
  lookupLabel = 'Lookup',
}: MetadataActionButtonsProps) {
  const isDisabled = disabled || isLoading;

  return (
    <div className="job-card__tab-actions">
      {onLookup ? (
        <button
          type="button"
          className="link-button"
          onClick={() => onLookup(false)}
          disabled={isDisabled}
          aria-busy={isLoading}
        >
          {isLoading ? 'Looking up…' : lookupLabel}
        </button>
      ) : null}
      {onLookup && hasResult ? (
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
      {onClear && hasResult ? (
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
  );
}
