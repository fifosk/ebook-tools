import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse
} from '../../api/dtos';
import {
  basenameFromPath
} from './videoDubbingUtils';
import { resolveDownloadStationCompletedFiles } from './videoDubbingDownloadStationUtils';
import styles from '../VideoDubbingPage.module.css';

type VideoDownloadStationPanelProps = {
  unavailableMessage: string | null;
  isAvailable: boolean;
  sourceUri: string;
  candidate: AcquisitionCandidate | null;
  destination: string;
  confirmed: boolean;
  job: AcquisitionJobStatusResponse | null;
  error: string | null;
  isSubmitting: boolean;
  isPolling: boolean;
  onSourceUriChange: (value: string) => void;
  onClearCandidate: () => void;
  onDestinationChange: (value: string) => void;
  onConfirmedChange: (value: boolean) => void;
  onSubmit: () => void;
  onPoll: () => void;
};

export default function VideoDownloadStationPanel({
  unavailableMessage,
  isAvailable,
  sourceUri,
  candidate,
  destination,
  confirmed,
  job,
  error,
  isSubmitting,
  isPolling,
  onSourceUriChange,
  onClearCandidate,
  onDestinationChange,
  onConfirmedChange,
  onSubmit,
  onPoll
}: VideoDownloadStationPanelProps) {
  const completedFiles = resolveDownloadStationCompletedFiles(job);

  return (
    <div className={styles.downloadStationPanel} aria-label="Download Station handoff">
      <div className={styles.downloadStationHeader}>
        <div>
          <h4 className={styles.sectionTitle}>Download Station</h4>
          <p className={styles.cardHint}>Queue a reviewed URL or magnet link, then refresh manual downloads.</p>
        </div>
        {job ? (
          <span className={`${styles.pill} ${styles.pillMeta}`}>
            {job.status}
            {typeof job.progress === 'number' ? ` · ${Math.round(job.progress * 100)}%` : ''}
          </span>
        ) : null}
      </div>
      {unavailableMessage ? <p className={styles.status}>{unavailableMessage}</p> : null}
      {error ? <p className={styles.error}>{error}</p> : null}
      {candidate ? (
        <div className={styles.status} aria-label="Selected Download Station candidate">
          Selected indexer result: {candidate.title}
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={onClearCandidate}
            disabled={isSubmitting}
          >
            Clear
          </button>
        </div>
      ) : null}
      <div className={styles.downloadStationControls}>
        <input
          className={styles.input}
          value={sourceUri}
          onChange={(event) => onSourceUriChange(event.target.value)}
          placeholder="https://... or magnet:?"
          aria-label="Download Station source URI"
          disabled={!isAvailable || isSubmitting}
        />
        <input
          className={styles.input}
          value={destination}
          onChange={(event) => onDestinationChange(event.target.value)}
          placeholder="Destination"
          aria-label="Download Station destination"
          disabled={!isAvailable || isSubmitting}
        />
        <button
          className={styles.secondaryButton}
          type="button"
          onClick={onSubmit}
          disabled={
            !isAvailable ||
            isSubmitting ||
            !confirmed ||
            (!sourceUri.trim() && !candidate?.candidate_token?.trim())
          }
        >
          {isSubmitting ? 'Submitting...' : 'Send'}
        </button>
        <button
          className={styles.secondaryButton}
          type="button"
          onClick={onPoll}
          disabled={!job || isPolling}
        >
          {isPolling ? 'Polling...' : 'Poll'}
        </button>
      </div>
      <label className={styles.downloadStationConfirm}>
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(event) => onConfirmedChange(event.target.checked)}
          disabled={!isAvailable || isSubmitting}
        />
        <span>I am authorized to download and process this source.</span>
      </label>
      {job?.message ? <p className={styles.status}>{job.message}</p> : null}
      {completedFiles.length ? (
        <p className={styles.status}>
          Completed: {completedFiles.map(basenameFromPath).join(', ')}
        </p>
      ) : null}
    </div>
  );
}
