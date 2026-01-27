type RawPayloadDetailsProps = {
  /** The payload object to display as JSON */
  payload: unknown;
  /** Summary text for the details element */
  summary?: string;
  /** Additional CSS class */
  className?: string;
};

/**
 * Collapsible details element for displaying raw JSON payloads.
 * Used for debugging and inspecting raw API responses.
 */
export function RawPayloadDetails({
  payload,
  summary = 'Raw payload',
  className,
}: RawPayloadDetailsProps) {
  if (payload == null) {
    return null;
  }

  const classes = ['raw-payload-details', className].filter(Boolean).join(' ');

  return (
    <details className={classes}>
      <summary>{summary}</summary>
      <pre>{JSON.stringify(payload, null, 2)}</pre>
    </details>
  );
}
