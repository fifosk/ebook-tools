type BookNarrationPerformanceSectionProps = {
  headingId: string;
  title: string;
  description: string;
  threadCount: string;
  queueSize: string;
  jobMaxWorkers: string;
  translationBatchSize: number;
  onThreadCountChange: (value: string) => void;
  onQueueSizeChange: (value: string) => void;
  onJobMaxWorkersChange: (value: string) => void;
  onTranslationBatchSizeChange: (value: number) => void;
};

const BookNarrationPerformanceSection = ({
  headingId,
  title,
  description,
  threadCount,
  queueSize,
  jobMaxWorkers,
  translationBatchSize,
  onThreadCountChange,
  onQueueSizeChange,
  onJobMaxWorkersChange,
  onTranslationBatchSizeChange
}: BookNarrationPerformanceSectionProps) => {
  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="pipeline-card__body">
        <div className="collapsible-group">
          <details>
            <summary>Translation threads</summary>
            <p className="form-help-text">
              Control how many translation and media workers run simultaneously. Leave blank to use
              the backend default.
            </p>
            <label htmlFor="thread_count">
              Worker threads
              <input
                id="thread_count"
                name="thread_count"
                type="number"
                min={1}
                step={1}
                value={threadCount}
                onChange={(event) => onThreadCountChange(event.target.value)}
                placeholder="Default"
              />
            </label>
            <label htmlFor="queue_size">
              Translation queue size
              <input
                id="queue_size"
                name="queue_size"
                type="number"
                min={1}
                step={1}
                value={queueSize}
                onChange={(event) => onQueueSizeChange(event.target.value)}
                placeholder="Default"
              />
            </label>
            <label htmlFor="job_max_workers">
              Maximum job workers
              <input
                id="job_max_workers"
                name="job_max_workers"
                type="number"
                min={1}
                step={1}
                value={jobMaxWorkers}
                onChange={(event) => onJobMaxWorkersChange(event.target.value)}
                placeholder="Default"
              />
            </label>
            <label htmlFor="translation_batch_size">
              LLM batch size (sentences per request)
              <input
                id="translation_batch_size"
                name="translation_batch_size"
                type="number"
                min={1}
                max={50}
                step={1}
                value={translationBatchSize}
                onChange={(event) => onTranslationBatchSizeChange(Number(event.target.value))}
              />
            </label>
            <p className="form-help-text">
              Batches multiple sentences into one LLM call. Use 1 to disable batching.
            </p>
          </details>
        </div>
      </div>
    </section>
  );
};

export default BookNarrationPerformanceSection;
