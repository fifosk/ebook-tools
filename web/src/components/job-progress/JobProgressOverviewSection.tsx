import { resolveImageNodeLabel } from '../../constants/imageNodes';
import { MetadataGrid, type MetadataRow } from '../metadata/MetadataGrid';
import type { JobParameterEntry } from './jobProgressParameters';
import {
  formatSecondsPerImage,
  formatTuningDescription,
  formatTuningLabel,
  formatTuningValue,
  type ImageClusterNodeSummary,
  type JobParallelismEntry,
} from './jobProgressUtils';

type JobProgressOverviewSectionProps = {
  jobParameterEntries: JobParameterEntry[];
  isBookJob: boolean;
  imageClusterNodes: ImageClusterNodeSummary[];
  statusError?: string | null;
  showLibraryReadyNotice: boolean;
  statusValue: string;
  mediaCompleted: boolean | null;
  batchStatEntries: Array<[string, string]>;
  parallelismEntries: JobParallelismEntry[];
  tuningEntries: Array<[string, unknown]>;
  fallbackEntries: Array<[string, string]>;
};

export function JobProgressOverviewSection({
  jobParameterEntries,
  isBookJob,
  imageClusterNodes,
  statusError,
  showLibraryReadyNotice,
  statusValue,
  mediaCompleted,
  batchStatEntries,
  parallelismEntries,
  tuningEntries,
  fallbackEntries,
}: JobProgressOverviewSectionProps) {
  const parameterRows: MetadataRow[] = jobParameterEntries.map((entry) => ({
    id: entry.key,
    label: entry.label,
    value: entry.value,
  }));
  const imageClusterRows: MetadataRow[] = imageClusterNodes.map((node) => {
    const label = resolveImageNodeLabel(node.baseUrl) ?? node.baseUrl;
    const processedCount = typeof node.processed === 'number' ? node.processed : 0;
    const processedLabel = `${processedCount} image${processedCount === 1 ? '' : 's'}`;
    const statusLabel = node.active ? 'Active' : 'Inactive';
    const speedLabel = formatSecondsPerImage(node.avgSecondsPerImage);
    return {
      id: node.baseUrl,
      label,
      value: (
        <>
          {statusLabel} &bull; {processedLabel} &bull; {speedLabel}
        </>
      ),
    };
  });

  return (
    <>
      {jobParameterEntries.length > 0 ? (
        <div className="job-card__section">
          <h4>Job parameters</h4>
          <MetadataGrid rows={parameterRows} />
        </div>
      ) : null}
      {isBookJob && imageClusterNodes.length > 0 ? (
        <div className="job-card__section">
          <h4>Image cluster</h4>
          <MetadataGrid rows={imageClusterRows} />
        </div>
      ) : null}
      {statusError ? <div className="alert">{statusError}</div> : null}
      {showLibraryReadyNotice ? (
        <div className="notice notice--success" role="status">
          Media generation finished. Move this job into the library when you're ready.
        </div>
      ) : null}
      {statusValue === 'pausing' ? (
        <div className="notice notice--info" role="status">
          Pause requested. Completing in-flight media generation before the job fully pauses.
        </div>
      ) : null}
      {statusValue === 'paused' && mediaCompleted === false ? (
        <div className="notice notice--warning" role="status">
          Some media is still finalizing. Generated files shown below reflect the latest available output.
        </div>
      ) : null}
      {batchStatEntries.length > 0 ? (
        <div>
          <h4>LLM batch stats</h4>
          <div className="progress-grid">
            {batchStatEntries.map(([label, value]) => (
              <div className="progress-metric" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {parallelismEntries.length > 0 ? (
        <div>
          <h4>Parallelism overview</h4>
          <div className="progress-grid">
            {parallelismEntries.map(({ label, value, hint }) => (
              <div className="progress-metric" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
                {hint ? <p className="progress-metric__hint">{hint}</p> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {!isBookJob && tuningEntries.length > 0 ? (
        <div>
          <h4>Performance tuning</h4>
          <div className="progress-grid">
            {tuningEntries.map(([key, value]) => {
              const description = formatTuningDescription(key);
              return (
                <div className="progress-metric" key={key}>
                  <strong>{formatTuningLabel(key)}</strong>
                  <span>{formatTuningValue(value)}</span>
                  {description ? <p className="progress-metric__hint">{description}</p> : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {fallbackEntries.length > 0 ? (
        <div>
          <h4>Fallbacks</h4>
          <div className="progress-grid">
            {fallbackEntries.map(([label, value]) => (
              <div className="progress-metric" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}
