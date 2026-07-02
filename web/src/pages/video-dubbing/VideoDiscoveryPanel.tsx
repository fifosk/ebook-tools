import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse
} from '../../api/dtos';
import type {
  VideoDiscoveryProvider,
  VideoDiscoveryProviderOption
} from './videoDubbingDiscovery';
import {
  formatDiscoveryCandidateMeta,
  resolveDiscoveryHint,
  resolveDiscoveryPlaceholder
} from './videoSourcePanelUtils';
import VideoDownloadStationPanel from './VideoDownloadStationPanel';
import styles from '../VideoDubbingPage.module.css';

type VideoDiscoveryPanelProps = {
  discoveryProvider: VideoDiscoveryProvider;
  discoveryProviderOptions: VideoDiscoveryProviderOption[];
  discoveryQuery: string;
  discoveryCandidates: AcquisitionCandidate[];
  discoveryError: string | null;
  discoveryPolicyNotes: string[];
  acquisitionProviderError: string | null;
  youtubeSearchUnavailableMessage: string | null;
  manualDownloadsUnavailableMessage: string | null;
  downloadStationUnavailableMessage: string | null;
  isDownloadStationAvailable: boolean;
  indexerSearchUnavailableMessage: string | null;
  downloadStationSourceUri: string;
  downloadStationCandidate: AcquisitionCandidate | null;
  downloadStationDestination: string;
  downloadStationConfirmed: boolean;
  downloadStationJob: AcquisitionJobStatusResponse | null;
  downloadStationError: string | null;
  isSubmittingDownloadStation: boolean;
  isPollingDownloadStation: boolean;
  isDiscoveryProviderAvailable: boolean;
  isDiscoveringVideos: boolean;
  onDiscoveryProviderChange: (provider: VideoDiscoveryProvider) => void;
  onDiscoveryQueryChange: (value: string) => void;
  onDiscoverVideos: () => void;
  onSelectDiscoveryCandidate: (candidate: AcquisitionCandidate) => void;
  onDownloadStationSourceUriChange: (value: string) => void;
  onClearDownloadStationCandidate: () => void;
  onDownloadStationDestinationChange: (value: string) => void;
  onDownloadStationConfirmedChange: (value: boolean) => void;
  onSubmitDownloadStation: () => void;
  onPollDownloadStation: () => void;
};

export default function VideoDiscoveryPanel({
  discoveryProvider,
  discoveryProviderOptions,
  discoveryQuery,
  discoveryCandidates,
  discoveryError,
  discoveryPolicyNotes,
  acquisitionProviderError,
  youtubeSearchUnavailableMessage,
  manualDownloadsUnavailableMessage,
  downloadStationUnavailableMessage,
  isDownloadStationAvailable,
  indexerSearchUnavailableMessage,
  downloadStationSourceUri,
  downloadStationCandidate,
  downloadStationDestination,
  downloadStationConfirmed,
  downloadStationJob,
  downloadStationError,
  isSubmittingDownloadStation,
  isPollingDownloadStation,
  isDiscoveryProviderAvailable,
  isDiscoveringVideos,
  onDiscoveryProviderChange,
  onDiscoveryQueryChange,
  onDiscoverVideos,
  onSelectDiscoveryCandidate,
  onDownloadStationSourceUriChange,
  onClearDownloadStationCandidate,
  onDownloadStationDestinationChange,
  onDownloadStationConfirmedChange,
  onSubmitDownloadStation,
  onPollDownloadStation
}: VideoDiscoveryPanelProps) {
  const discoveryPlaceholder = resolveDiscoveryPlaceholder(discoveryProvider);
  const discoveryHint = resolveDiscoveryHint(discoveryProvider);

  return (
    <div className={styles.discoveryPanel} aria-label="Video source discovery">
      <div className={styles.discoveryHeader}>
        <div>
          <h3 className={styles.sectionTitle}>Discover video sources</h3>
          <p className={styles.cardHint}>{discoveryHint}</p>
        </div>
        <div className={styles.discoveryControls}>
          <div className={styles.discoveryProviderToggle} role="group" aria-label="Video discovery source">
            {discoveryProviderOptions.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`${styles.discoveryProviderOption} ${
                  discoveryProvider === option.id ? styles.discoveryProviderOptionActive : ''
                }`}
                aria-pressed={discoveryProvider === option.id}
                onClick={() => onDiscoveryProviderChange(option.id)}
                disabled={!option.available}
              >
                {option.label}
              </button>
            ))}
          </div>
          <input
            className={styles.input}
            value={discoveryQuery}
            onChange={(event) => onDiscoveryQueryChange(event.target.value)}
            placeholder={discoveryPlaceholder}
            aria-label="Video discovery search"
          />
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={onDiscoverVideos}
            disabled={isDiscoveringVideos || !isDiscoveryProviderAvailable}
          >
            {isDiscoveringVideos ? 'Searching…' : 'Discover'}
          </button>
        </div>
      </div>
      {discoveryError ? <p className={styles.error}>{discoveryError}</p> : null}
      {discoveryPolicyNotes.map((note) => (
        <p className={styles.status} key={note}>
          {note}
        </p>
      ))}
      {acquisitionProviderError ? <p className={styles.error}>{acquisitionProviderError}</p> : null}
      {youtubeSearchUnavailableMessage ? (
        <p className={styles.status}>{youtubeSearchUnavailableMessage}</p>
      ) : null}
      {manualDownloadsUnavailableMessage ? (
        <p className={styles.status}>{manualDownloadsUnavailableMessage}</p>
      ) : null}
      {indexerSearchUnavailableMessage ? (
        <p className={styles.status}>{indexerSearchUnavailableMessage}</p>
      ) : null}
      {!isDiscoveringVideos && discoveryCandidates.length === 0 ? (
        <p className={styles.status}>No discovery results loaded yet.</p>
      ) : null}
      {discoveryCandidates.length > 0 ? (
        <div className={styles.discoveryList}>
          {discoveryCandidates.map((candidate) => (
            <button
              key={candidate.candidate_id}
              type="button"
              className={styles.discoveryOption}
              onClick={() => onSelectDiscoveryCandidate(candidate)}
            >
              <span className={styles.discoveryTitle}>{candidate.title}</span>
              <span className={styles.discoveryMeta}>{formatDiscoveryCandidateMeta(candidate)}</span>
            </button>
          ))}
        </div>
      ) : null}
      <VideoDownloadStationPanel
        unavailableMessage={downloadStationUnavailableMessage}
        isAvailable={isDownloadStationAvailable}
        sourceUri={downloadStationSourceUri}
        candidate={downloadStationCandidate}
        destination={downloadStationDestination}
        confirmed={downloadStationConfirmed}
        job={downloadStationJob}
        error={downloadStationError}
        isSubmitting={isSubmittingDownloadStation}
        isPolling={isPollingDownloadStation}
        onSourceUriChange={onDownloadStationSourceUriChange}
        onClearCandidate={onClearDownloadStationCandidate}
        onDestinationChange={onDownloadStationDestinationChange}
        onConfirmedChange={onDownloadStationConfirmedChange}
        onSubmit={onSubmitDownloadStation}
        onPoll={onPollDownloadStation}
      />
    </div>
  );
}
