import { normaliseStringList } from './jobProgressUtils';

export type JobProgressCreationSummaryData = {
  messages: string[];
  warnings: string[];
  sentencesPreview: string[];
  epubPath: string | null;
};

export function parseJobProgressCreationSummary(value: unknown): JobProgressCreationSummaryData | null {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const summary = value as Record<string, unknown>;
  const messages = normaliseStringList(summary['messages']);
  const warnings = normaliseStringList(summary['warnings']);
  const sentencesPreview = normaliseStringList(summary['sentences_preview']);
  const rawEpubPath = typeof summary['epub_path'] === 'string' ? summary['epub_path'].trim() : null;
  const epubPath = rawEpubPath && rawEpubPath.length > 0 ? rawEpubPath : null;

  if (!messages.length && !warnings.length && !sentencesPreview.length && !epubPath) {
    return null;
  }

  return {
    messages,
    warnings,
    sentencesPreview,
    epubPath
  };
}

type JobProgressCreationSummaryProps = {
  summary: JobProgressCreationSummaryData;
};

export function JobProgressCreationSummary({ summary }: JobProgressCreationSummaryProps) {
  const hasWarnings = summary.warnings.length > 0;

  return (
    <div className="job-card__section">
      <h4>Book creation summary</h4>
      {summary.epubPath ? (
        <p>
          <strong>Seed EPUB:</strong> {summary.epubPath}
        </p>
      ) : null}
      {summary.messages.length ? (
        <ul className={`job-creation-summary__list ${hasWarnings ? 'job-creation-summary__list--before-warning' : ''}`}>
          {summary.messages.map((message, index) => (
            <li key={`creation-message-${index}`}>{message}</li>
          ))}
        </ul>
      ) : null}
      {summary.sentencesPreview.length ? (
        <p className={hasWarnings ? 'job-creation-summary__preview job-creation-summary__preview--before-warning' : 'job-creation-summary__preview'}>
          <strong>Sample sentences:</strong> {summary.sentencesPreview.join(' ')}
        </p>
      ) : null}
      {hasWarnings ? (
        <div className="notice notice--warning job-creation-summary__warnings" role="alert">
          <ul className="job-creation-summary__warning-list">
            {summary.warnings.map((warning, index) => (
              <li key={`creation-warning-${index}`}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
