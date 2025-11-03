type PipelineSubmitSectionProps = {
  headingId: string;
  title: string;
  description: string;
  missingRequirements: string[];
  missingRequirementText: string;
  isSubmitSection: boolean;
  error: string | null;
  externalError: string | null;
  inputFile: string;
  baseOutputFile: string;
  inputLanguage: string;
  targetLanguageSummary: string;
  outputFormats: string;
  isSubmitting: boolean;
  isSubmitDisabled: boolean;
};

const PipelineSubmitSection = ({
  headingId,
  title,
  description,
  missingRequirements,
  missingRequirementText,
  isSubmitSection,
  error,
  externalError,
  inputFile,
  baseOutputFile,
  inputLanguage,
  targetLanguageSummary,
  outputFormats,
  isSubmitting,
  isSubmitDisabled
}: PipelineSubmitSectionProps) => {
  const hasMissingRequirements = missingRequirements.length > 0;

  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="pipeline-card__body">
        {hasMissingRequirements ? (
          <div className="form-callout form-callout--warning" role="status">
            Provide {missingRequirementText} before submitting.
          </div>
        ) : (
          <div className="form-callout form-callout--success" role="status">
            All required settings are ready to submit.
          </div>
        )}
        {isSubmitSection && (error || externalError) ? (
          <div className="alert" role="alert">
            {error ?? externalError}
          </div>
        ) : null}
        <dl className="pipeline-summary">
          <div>
            <dt>Input file</dt>
            <dd>{inputFile || 'Not set'}</dd>
          </div>
          <div>
            <dt>Base output</dt>
            <dd>{baseOutputFile || 'Not set'}</dd>
          </div>
          <div>
            <dt>Input language</dt>
            <dd>{inputLanguage || 'Not set'}</dd>
          </div>
          <div>
            <dt>Target languages</dt>
            <dd>{targetLanguageSummary}</dd>
          </div>
          <div>
            <dt>Output formats</dt>
            <dd>{outputFormats}</dd>
          </div>
        </dl>
        <button type="submit" disabled={isSubmitDisabled}>
          {isSubmitting ? 'Submitting…' : 'Submit job'}
        </button>
      </div>
    </section>
  );
};

export default PipelineSubmitSection;
