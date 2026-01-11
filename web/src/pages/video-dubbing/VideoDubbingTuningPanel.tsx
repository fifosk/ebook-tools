import styles from '../VideoDubbingPage.module.css';

type VideoDubbingTuningPanelProps = {
  translationBatchSize: number;
  flushSentences: number;
  onTranslationBatchSizeChange: (value: number) => void;
  onFlushSentencesChange: (value: number) => void;
};

export default function VideoDubbingTuningPanel({
  translationBatchSize,
  flushSentences,
  onTranslationBatchSizeChange,
  onFlushSentencesChange
}: VideoDubbingTuningPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Performance tuning</h2>
          <p className={styles.cardHint}>Tune LLM batching and media flush cadence.</p>
        </div>
      </div>
      <div className={styles.formFields}>
        <label className={styles.field}>
          <span>LLM batch size (sentences per request)</span>
          <input
            className={styles.input}
            type="number"
            min={1}
            max={50}
            step={1}
            value={translationBatchSize}
            onChange={(event) => {
              const parsed = Number(event.target.value);
              if (Number.isNaN(parsed)) {
                return;
              }
              onTranslationBatchSizeChange(Math.min(Math.max(1, parsed), 50));
            }}
          />
          <p className={styles.fieldHint}>Batch multiple subtitle sentences into one LLM call.</p>
        </label>
        <label className={styles.field}>
          <span>Flush interval (sentences)</span>
          <div className={styles.rangeRow}>
            <input
              className={styles.input}
              type="number"
              min={1}
              step={1}
              value={flushSentences}
              onChange={(event) => onFlushSentencesChange(Math.max(1, Number(event.target.value)))}
            />
            <span className={styles.rangeValue}>{flushSentences} sentences</span>
          </div>
          <p className={styles.fieldHint}>Write/append the video every N sentences (default 10).</p>
        </label>
      </div>
    </section>
  );
}
