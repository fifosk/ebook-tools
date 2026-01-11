import styles from '../SubtitleToolPage.module.css';

type SubtitleTuningPanelProps = {
  workerCount: number | '';
  batchSize: number | '';
  translationBatchSize: number | '';
  onWorkerCountChange: (value: number | '') => void;
  onBatchSizeChange: (value: number | '') => void;
  onTranslationBatchSizeChange: (value: number | '') => void;
};

export default function SubtitleTuningPanel({
  workerCount,
  batchSize,
  translationBatchSize,
  onWorkerCountChange,
  onBatchSizeChange,
  onTranslationBatchSizeChange
}: SubtitleTuningPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Performance tuning</h2>
          <p className={styles.cardHint}>Adjust concurrency and LLM batching for subtitle jobs.</p>
        </div>
      </div>
      <div className={styles.formFields}>
        <label>
          Worker threads
          <input
            type="number"
            min={1}
            max={32}
            value={workerCount}
            onChange={(event) => {
              const raw = event.target.value;
              if (!raw.trim()) {
                onWorkerCountChange('');
                return;
              }
              const parsed = Number(raw);
              if (Number.isNaN(parsed)) {
                return;
              }
              onWorkerCountChange(Math.min(Math.max(1, parsed), 32));
            }}
          />
          <small>Parallel subtitle translation/render workers per batch.</small>
        </label>
        <label>
          Subtitle batch size
          <input
            type="number"
            min={1}
            max={500}
            value={batchSize}
            onChange={(event) => {
              const raw = event.target.value;
              if (!raw.trim()) {
                onBatchSizeChange('');
                return;
              }
              const parsed = Number(raw);
              if (Number.isNaN(parsed)) {
                return;
              }
              onBatchSizeChange(Math.min(Math.max(1, parsed), 500));
            }}
          />
          <small>Number of cues processed per render batch.</small>
        </label>
        <label>
          LLM batch size (sentences per request)
          <input
            type="number"
            min={1}
            max={50}
            value={translationBatchSize}
            onChange={(event) => {
              const raw = event.target.value;
              if (!raw.trim()) {
                onTranslationBatchSizeChange('');
                return;
              }
              const parsed = Number(raw);
              if (Number.isNaN(parsed)) {
                return;
              }
              onTranslationBatchSizeChange(Math.min(Math.max(1, parsed), 50));
            }}
          />
          <small>Batch multiple subtitle sentences into one LLM call.</small>
        </label>
      </div>
    </section>
  );
}
