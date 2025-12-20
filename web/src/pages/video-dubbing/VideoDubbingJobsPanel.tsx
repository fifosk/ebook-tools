import type { JobState } from '../../components/JobList';
import { formatJobLabel, resolveOutputPath } from './videoDubbingUtils';
import styles from '../VideoDubbingPage.module.css';

type VideoDubbingJobsPanelProps = {
  jobs: JobState[];
  onSelectJob: (jobId: string) => void;
  onOpenJobMedia?: (jobId: string) => void;
};

export default function VideoDubbingJobsPanel({
  jobs,
  onSelectJob,
  onOpenJobMedia
}: VideoDubbingJobsPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Dubbing jobs</h2>
          <p className={styles.cardHint}>Monitor active and recent dubbing tasks.</p>
        </div>
      </div>
      {jobs.length === 0 ? (
        <p className={styles.status}>No dubbing jobs submitted yet.</p>
      ) : (
        <div className={styles.jobList}>
          {[...jobs]
            .sort((a, b) => new Date(b.status.created_at).getTime() - new Date(a.status.created_at).getTime())
            .map((job) => {
              const statusValue = job.status?.status ?? 'pending';
              const outputPath = resolveOutputPath(job);
              return (
                <div key={job.jobId} className={styles.jobRow}>
                  <div>
                    <div className={styles.jobTitle}>
                      <span className={styles.jobBadge}>{statusValue}</span>
                      <span>{formatJobLabel(job)}</span>
                    </div>
                    <div className={styles.jobMeta}>
                      <span>Job {job.jobId}</span>
                      {outputPath ? (
                        <>
                          <span aria-hidden="true">•</span>
                          <span className={styles.jobPath}>{outputPath}</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                  <div className={styles.jobActions}>
                    <button
                      type="button"
                      className={styles.primaryButton}
                      onClick={() => (onOpenJobMedia ? onOpenJobMedia(job.jobId) : onSelectJob(job.jobId))}
                    >
                      Play media
                    </button>
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      onClick={() => onSelectJob(job.jobId)}
                    >
                      View progress
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </section>
  );
}
