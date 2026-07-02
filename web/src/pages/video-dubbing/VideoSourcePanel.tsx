import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse,
  YoutubeInlineSubtitleStream,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import type {
  VideoDiscoveryProvider,
  VideoDiscoveryProviderOption
} from './videoDubbingDiscovery';
import VideoDiscoveryPanel from './VideoDiscoveryPanel';
import VideoDownloadedListPanel from './VideoDownloadedListPanel';
import styles from '../VideoDubbingPage.module.css';

type VideoSourcePanelProps = {
  baseDir: string;
  isLoading: boolean;
  loadError: string | null;
  videos: YoutubeNasVideo[];
  selectedVideoPath: string | null;
  selectedSubtitlePath: string | null;
  selectedVideo: YoutubeNasVideo | null;
  playableSubtitles: YoutubeNasSubtitle[];
  subtitleNotice: string | null;
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
  canExtractEmbedded: boolean;
  isExtractingSubtitles: boolean;
  isLoadingStreams: boolean;
  isChoosingStreams: boolean;
  availableSubtitleStreams: YoutubeInlineSubtitleStream[];
  selectedStreamLanguages: Set<string>;
  extractableStreams: YoutubeInlineSubtitleStream[];
  extractError: string | null;
  deletingSubtitlePath: string | null;
  deletingVideoPath: string | null;
  onBaseDirChange: (value: string) => void;
  onRefresh: () => void;
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
  onSelectVideo: (video: YoutubeNasVideo) => void;
  onSelectSubtitle: (path: string) => void;
  onDeleteVideo: (video: YoutubeNasVideo) => void;
  onDeleteSubtitle: (subtitle: YoutubeNasSubtitle) => void;
  onExtractSubtitles: () => void;
  onToggleSubtitleStream: (language: string, enabled: boolean) => void;
  onConfirmSubtitleStreams: () => void;
  onCancelStreamSelection: () => void;
  onExtractAllStreams: () => void;
};

export default function VideoSourcePanel({
  baseDir,
  isLoading,
  loadError,
  videos,
  selectedVideoPath,
  selectedSubtitlePath,
  selectedVideo,
  playableSubtitles,
  subtitleNotice,
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
  canExtractEmbedded,
  isExtractingSubtitles,
  isLoadingStreams,
  isChoosingStreams,
  availableSubtitleStreams,
  selectedStreamLanguages,
  extractableStreams,
  extractError,
  deletingSubtitlePath,
  deletingVideoPath,
  onBaseDirChange,
  onRefresh,
  onDiscoveryProviderChange,
  onDiscoveryQueryChange,
  onDiscoverVideos,
  onSelectDiscoveryCandidate,
  onDownloadStationSourceUriChange,
  onClearDownloadStationCandidate,
  onDownloadStationDestinationChange,
  onDownloadStationConfirmedChange,
  onSubmitDownloadStation,
  onPollDownloadStation,
  onSelectVideo,
  onSelectSubtitle,
  onDeleteVideo,
  onDeleteSubtitle,
  onExtractSubtitles,
  onToggleSubtitleStream,
  onConfirmSubtitleStreams,
  onCancelStreamSelection,
  onExtractAllStreams
}: VideoSourcePanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Discovered videos</h2>
          <p className={styles.cardHint}>
            Base path: <code>{baseDir}</code>
          </p>
        </div>
        <div className={styles.controlRow}>
          <input
            className={styles.input}
            value={baseDir}
            onChange={(event) => onBaseDirChange(event.target.value)}
            placeholder="NAS directory"
            aria-label="YouTube NAS directory"
          />
          <button className={styles.secondaryButton} type="button" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>
      {loadError ? <p className={styles.error}>{loadError}</p> : null}
      <VideoDiscoveryPanel
        discoveryProvider={discoveryProvider}
        discoveryProviderOptions={discoveryProviderOptions}
        discoveryQuery={discoveryQuery}
        discoveryCandidates={discoveryCandidates}
        discoveryError={discoveryError}
        discoveryPolicyNotes={discoveryPolicyNotes}
        acquisitionProviderError={acquisitionProviderError}
        youtubeSearchUnavailableMessage={youtubeSearchUnavailableMessage}
        manualDownloadsUnavailableMessage={manualDownloadsUnavailableMessage}
        downloadStationUnavailableMessage={downloadStationUnavailableMessage}
        isDownloadStationAvailable={isDownloadStationAvailable}
        indexerSearchUnavailableMessage={indexerSearchUnavailableMessage}
        downloadStationSourceUri={downloadStationSourceUri}
        downloadStationCandidate={downloadStationCandidate}
        downloadStationDestination={downloadStationDestination}
        downloadStationConfirmed={downloadStationConfirmed}
        downloadStationJob={downloadStationJob}
        downloadStationError={downloadStationError}
        isSubmittingDownloadStation={isSubmittingDownloadStation}
        isPollingDownloadStation={isPollingDownloadStation}
        isDiscoveryProviderAvailable={isDiscoveryProviderAvailable}
        isDiscoveringVideos={isDiscoveringVideos}
        onDiscoveryProviderChange={onDiscoveryProviderChange}
        onDiscoveryQueryChange={onDiscoveryQueryChange}
        onDiscoverVideos={onDiscoverVideos}
        onSelectDiscoveryCandidate={onSelectDiscoveryCandidate}
        onDownloadStationSourceUriChange={onDownloadStationSourceUriChange}
        onClearDownloadStationCandidate={onClearDownloadStationCandidate}
        onDownloadStationDestinationChange={onDownloadStationDestinationChange}
        onDownloadStationConfirmedChange={onDownloadStationConfirmedChange}
        onSubmitDownloadStation={onSubmitDownloadStation}
        onPollDownloadStation={onPollDownloadStation}
      />
      <VideoDownloadedListPanel
        isLoading={isLoading}
        videos={videos}
        selectedVideoPath={selectedVideoPath}
        selectedSubtitlePath={selectedSubtitlePath}
        selectedVideo={selectedVideo}
        playableSubtitles={playableSubtitles}
        subtitleNotice={subtitleNotice}
        canExtractEmbedded={canExtractEmbedded}
        isExtractingSubtitles={isExtractingSubtitles}
        isLoadingStreams={isLoadingStreams}
        isChoosingStreams={isChoosingStreams}
        availableSubtitleStreams={availableSubtitleStreams}
        selectedStreamLanguages={selectedStreamLanguages}
        extractableStreams={extractableStreams}
        extractError={extractError}
        deletingSubtitlePath={deletingSubtitlePath}
        deletingVideoPath={deletingVideoPath}
        onSelectVideo={onSelectVideo}
        onSelectSubtitle={onSelectSubtitle}
        onDeleteVideo={onDeleteVideo}
        onDeleteSubtitle={onDeleteSubtitle}
        onExtractSubtitles={onExtractSubtitles}
        onToggleSubtitleStream={onToggleSubtitleStream}
        onConfirmSubtitleStreams={onConfirmSubtitleStreams}
        onCancelStreamSelection={onCancelStreamSelection}
        onExtractAllStreams={onExtractAllStreams}
      />
    </section>
  );
}
