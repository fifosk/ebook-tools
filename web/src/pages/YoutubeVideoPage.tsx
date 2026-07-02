import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  deleteYoutubeVideo,
  discoverAcquisitionCandidates,
  downloadYoutubeSubtitle,
  downloadYoutubeVideo,
  fetchAcquisitionProviders,
  fetchYoutubeLibrary,
  fetchYoutubeSubtitleTracks
} from '../api/client';
import type {
  AcquisitionCandidate,
  AcquisitionProvider,
  YoutubeNasLibraryResponse,
  YoutubeNasVideo,
  YoutubeSubtitleListResponse,
  YoutubeSubtitleTrack,
  YoutubeVideoFormat
} from '../api/dtos';
import EmojiIcon from '../components/EmojiIcon';
import styles from './YoutubeVideoPage.module.css';
import {
  describeFormat,
  findProvider,
  formatBytes,
  formatDateLong,
  formatDateShort,
  formatDiscoveryCandidateMeta,
  isYoutubeSource,
  resolveDefaultTrack,
  subtitleBadgeFlag,
  subtitleBadgeLabel,
  trackKey,
  videoSourceBadge
} from './youtube-video/youtubeVideoPageUtils';

// NAS paths are resolved by the backend — no hardcoded defaults needed.
// The API returns the configured base_dir in its response.
const SUBTITLE_NAS_DIR = '';
const VIDEO_NAS_DIR = '';

export default function YoutubeVideoPage() {
  const [activeTab, setActiveTab] = useState<'video' | 'downloads'>('video');
  const [url, setUrl] = useState('');
  const [discoveryQuery, setDiscoveryQuery] = useState('');
  const [discoveryCandidates, setDiscoveryCandidates] = useState<AcquisitionCandidate[]>([]);
  const [isDiscoveringVideos, setIsDiscoveringVideos] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [selectedDiscoveryMessage, setSelectedDiscoveryMessage] = useState<string | null>(null);
  const [acquisitionProviders, setAcquisitionProviders] = useState<AcquisitionProvider[]>([]);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null);
  const [listing, setListing] = useState<YoutubeSubtitleListResponse | null>(null);
  const [tracks, setTracks] = useState<YoutubeSubtitleTrack[]>([]);
  const [videoFormats, setVideoFormats] = useState<YoutubeVideoFormat[]>([]);
  const [selectedVideoFormat, setSelectedVideoFormat] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [isLoadingTracks, setIsLoadingTracks] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadMessage, setDownloadMessage] = useState<string | null>(null);
  const [downloadPaths, setDownloadPaths] = useState<string[]>([]);
  const [videoDownloadPath, setVideoDownloadPath] = useState<string | null>(null);
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [videos, setVideos] = useState<YoutubeNasVideo[]>([]);
  const [isLoadingLibrary, setIsLoadingLibrary] = useState(false);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [deletingVideoPath, setDeletingVideoPath] = useState<string | null>(null);
  const youtubeSearchProvider = useMemo(
    () => findProvider(acquisitionProviders, 'youtube_search'),
    [acquisitionProviders]
  );
  const isYoutubeSearchAvailable = youtubeSearchProvider?.available !== false;
  const youtubeSearchUnavailableMessage =
    youtubeSearchProvider && !youtubeSearchProvider.available
      ? `${youtubeSearchProvider.label} is ${youtubeSearchProvider.status.replace('_', ' ')}. Configure the YouTube Data API key to search here, or paste a direct URL below.`
      : null;

  const resetInspectionState = useCallback(() => {
    setResolvedUrl(null);
    setListing(null);
    setTracks([]);
    setVideoFormats([]);
    setSelectedVideoFormat(null);
    setSelectedKeys(new Set());
    setListError(null);
    setDownloadError(null);
    setDownloadMessage(null);
    setDownloadPaths([]);
    setVideoDownloadPath(null);
  }, []);

  const handleFetchTracks = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedUrl = url.trim();
      if (!trimmedUrl) {
        setListError('Provide a YouTube video URL to inspect available subtitles.');
        return;
      }

      setIsLoadingTracks(true);
      setSelectedDiscoveryMessage(null);
      resetInspectionState();

      try {
        const response = await fetchYoutubeSubtitleTracks(trimmedUrl);
        setListing(response);
        setResolvedUrl(trimmedUrl);
        const nextTracks = response.tracks ?? [];
        setTracks(nextTracks);
        const defaultTrack = resolveDefaultTrack(nextTracks);
        if (defaultTrack) {
          setSelectedKeys(new Set([trackKey(defaultTrack)]));
        }
        const formats = response.video_formats ?? [];
        setVideoFormats(formats);
        setSelectedVideoFormat(formats.length > 0 ? formats[0].format_id : null);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message || 'Unable to fetch subtitle languages.'
            : 'Unable to fetch subtitle languages.';
        setListError(message);
      } finally {
        setIsLoadingTracks(false);
      }
    },
    [resetInspectionState, url]
  );

  const handleDiscoverVideos = useCallback(async () => {
    if (!isYoutubeSearchAvailable) {
      setDiscoveryError(youtubeSearchUnavailableMessage ?? 'YouTube search is not available on this backend.');
      setDiscoveryCandidates([]);
      return;
    }
    setIsDiscoveringVideos(true);
    setDiscoveryError(null);
    try {
      const response = await discoverAcquisitionCandidates({
        mediaKind: 'video',
        provider: 'youtube_search',
        query: discoveryQuery,
        limit: 12
      });
      setDiscoveryCandidates(
        response.candidates.filter(
          (candidate) => candidate.provider === 'youtube_search' && Boolean(candidate.source_url?.trim())
        )
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to search YouTube.' : 'Unable to search YouTube.';
      setDiscoveryError(message);
      setDiscoveryCandidates([]);
    } finally {
      setIsDiscoveringVideos(false);
    }
  }, [discoveryQuery, isYoutubeSearchAvailable, youtubeSearchUnavailableMessage]);

  const refreshAcquisitionProviders = useCallback(async () => {
    setProviderError(null);
    try {
      const response = await fetchAcquisitionProviders();
      setAcquisitionProviders(response.providers);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to load discovery providers.' : 'Unable to load discovery providers.';
      setProviderError(message);
    }
  }, []);

  const handleSelectDiscoveryCandidate = useCallback(
    (candidate: AcquisitionCandidate) => {
      const sourceUrl = candidate.source_url?.trim();
      if (!sourceUrl) {
        setDiscoveryError('Selected YouTube result does not include a reviewable URL.');
        return;
      }
      setUrl(sourceUrl);
      resetInspectionState();
      setDiscoveryError(null);
      setSelectedDiscoveryMessage(
        `Selected "${candidate.title}". List subtitles to inspect available tracks before downloading.`
      );
    },
    [resetInspectionState]
  );

  const refreshDownloads = useCallback(async () => {
    setIsLoadingLibrary(true);
    setLibraryError(null);
    try {
      const response = await fetchYoutubeLibrary();
      const youtubeVideos = (response.videos ?? []).filter(isYoutubeSource);
      setLibrary(response);
      setVideos(youtubeVideos);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message || 'Unable to load downloaded videos.'
          : 'Unable to load downloaded videos.';
      setLibraryError(message);
    } finally {
      setIsLoadingLibrary(false);
    }
  }, []);

  useEffect(() => {
    void refreshDownloads();
    void refreshAcquisitionProviders();
  }, [refreshAcquisitionProviders, refreshDownloads]);

  const selectedTracks = useMemo(() => {
    const lookup = new Map(tracks.map((track) => [trackKey(track), track]));
    return Array.from(selectedKeys)
      .map((key) => lookup.get(key))
      .filter((track): track is YoutubeSubtitleTrack => Boolean(track));
  }, [selectedKeys, tracks]);

  const handleDeleteVideo = useCallback(
    async (video: YoutubeNasVideo) => {
      if (video.linked_job_ids && video.linked_job_ids.length > 0) {
        return;
      }
      const targetFolder = video.folder || video.path;
      const confirmed = window.confirm(
        `Delete the folder "${targetFolder}" and all dubbed outputs/subtitles inside it? This will remove the downloaded video and any generated artifacts.`
      );
      if (!confirmed) {
        return;
      }
      setDeletingVideoPath(video.path);
      setLibraryError(null);
      try {
        await deleteYoutubeVideo({ video_path: video.path });
        setVideos((prev) => prev.filter((entry) => entry.path !== video.path));
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to delete video.' : 'Unable to delete video.';
        setLibraryError(message);
      } finally {
        setDeletingVideoPath(null);
      }
    },
    []
  );

  const handleSelectionChange = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    const values = Array.from(event.target.selectedOptions).map((option) => option.value);
    setSelectedKeys(new Set(values));
  }, []);

  const handleDownload = useCallback(async () => {
    const activeUrl = (resolvedUrl || url).trim();
    if (!activeUrl) {
      setDownloadError('Fetch available subtitles before downloading.');
      return;
    }
    if (selectedTracks.length === 0) {
      setDownloadError('Select one or more subtitle languages to download.');
      return;
    }
    setIsDownloading(true);
    setDownloadError(null);
    setDownloadMessage(null);
    setDownloadPaths([]);
    setVideoDownloadPath(null);
    const resolvedVideoDir = VIDEO_NAS_DIR;
    const timestamp = new Date().toISOString();

    const savedFiles: string[] = [];
    try {
      for (const track of selectedTracks) {
        const payload = {
          url: activeUrl,
          language: track.language,
          kind: track.kind,
          video_output_dir: resolvedVideoDir,
          timestamp
        } as const;
        const response = await downloadYoutubeSubtitle(payload);
        savedFiles.push(response.filename);
      }
      setDownloadPaths(savedFiles);
      setDownloadMessage(`Saved ${savedFiles.length} file(s) to ${SUBTITLE_NAS_DIR}`);
      const videoResponse = await downloadYoutubeVideo({
        url: activeUrl,
        output_dir: resolvedVideoDir,
        format_id: selectedVideoFormat || undefined,
        timestamp
      });
      setVideoDownloadPath(videoResponse.output_path || videoResponse.filename);
      await refreshDownloads();
      setActiveTab('downloads');
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message || 'Subtitle download failed.'
          : 'Subtitle download failed.';
      setDownloadError(message);
    } finally {
      setIsDownloading(false);
    }
  }, [resolvedUrl, url, selectedTracks, selectedVideoFormat, refreshDownloads]);

  const selectedLabel = useMemo(() => {
    if (!selectedTracks.length) {
      return 'No subtitles selected';
    }
    const labels = selectedTracks.map((track) => {
      const kindLabel = track.kind === 'auto' ? 'auto' : 'manual';
      return `${track.language} (${kindLabel})`;
    });
    return labels.join(', ');
  }, [selectedTracks]);

  const libraryBaseDir = library?.base_dir ?? '';
  const canDownload = Boolean(
    !isDownloading && !isLoadingTracks && tracks.length > 0 && selectedTracks.length > 0
  );

  return (
    <div className={styles.container}>
      <div className={styles.tabsRow}>
        <div className={styles.tabs} role="tablist" aria-label="YouTube video tabs">
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${activeTab === 'video' ? styles.tabButtonActive : ''}`}
            aria-selected={activeTab === 'video'}
            onClick={() => setActiveTab('video')}
          >
            Source
          </button>
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${activeTab === 'downloads' ? styles.tabButtonActive : ''}`}
            aria-selected={activeTab === 'downloads'}
            onClick={() => setActiveTab('downloads')}
          >
            Downloads <span className={styles.sectionCount}>{videos.length}</span>
          </button>
        </div>
        <div className={styles.tabsActions}>
          {activeTab === 'downloads' ? (
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => void refreshDownloads()}
              disabled={isLoadingLibrary}
            >
              {isLoadingLibrary ? 'Refreshing…' : 'Refresh'}
            </button>
          ) : null}
          {activeTab === 'video' ? (
            <button
              type="button"
              className={`${styles.primaryButton} ${styles.primaryButtonCompact}`}
              onClick={() => void handleDownload()}
              disabled={!canDownload}
            >
              {isDownloading ? 'Downloading…' : '⬇️ Download selection'}
            </button>
          ) : null}
        </div>
      </div>

      {activeTab === 'video' ? (
        <section className={styles.card}>
          <header className={styles.cardHeader}>
            <div>
              <h2 className={styles.cardTitle}>YouTube video</h2>
              {libraryBaseDir ? (
                <p className={styles.pathNote}>
                  Videos: <code>{libraryBaseDir}</code>
                </p>
              ) : null}
            </div>
            {listing ? (
              <div className={styles.videoBadge}>
                <span className={styles.badgeLabel}>Video ID</span>
                <strong className={styles.badgeValue}>{listing.video_id}</strong>
              </div>
            ) : null}
          </header>
          <div className={styles.discoveryPanel} aria-label="YouTube discovery panel">
            <div className={styles.discoveryHeader}>
              <div>
                <h3 className={styles.sectionTitle}>Search YouTube</h3>
                <p className={styles.sectionHint}>
                  Use backend YouTube search, then review subtitles and video quality before downloading.
                </p>
              </div>
              <div className={styles.inputRow}>
                <input
                  type="search"
                  aria-label="YouTube discovery search"
                  placeholder="Search title or channel"
                  value={discoveryQuery}
                  onChange={(event) => setDiscoveryQuery(event.target.value)}
                  className={styles.input}
                />
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => void handleDiscoverVideos()}
                  disabled={isDiscoveringVideos || !isYoutubeSearchAvailable}
                >
                  {isDiscoveringVideos ? 'Searching…' : 'Search'}
                </button>
              </div>
            </div>
            {discoveryError ? <p className={styles.error}>{discoveryError}</p> : null}
            {providerError ? <p className={styles.error}>{providerError}</p> : null}
            {youtubeSearchUnavailableMessage ? (
              <p className={styles.status}>{youtubeSearchUnavailableMessage}</p>
            ) : null}
            {discoveryCandidates.length > 0 ? (
              <div className={styles.discoveryList}>
                {discoveryCandidates.map((candidate) => (
                  <button
                    key={candidate.candidate_id}
                    type="button"
                    className={styles.discoveryOption}
                    onClick={() => handleSelectDiscoveryCandidate(candidate)}
                  >
                    <span className={styles.discoveryTitle}>{candidate.title}</span>
                    <span className={styles.discoveryMeta}>{formatDiscoveryCandidateMeta(candidate)}</span>
                  </button>
                ))}
              </div>
            ) : null}
            {!isDiscoveringVideos && !discoveryError && discoveryCandidates.length === 0 ? (
              <p className={styles.status}>No search results loaded yet.</p>
            ) : null}
          </div>
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Inspect a video</h3>
            <form className={styles.form} onSubmit={handleFetchTracks}>
              <label className={styles.label} htmlFor="youtube-url">
                YouTube URL
              </label>
              <div className={styles.inputRow}>
                <input
                  id="youtube-url"
                  name="youtube-url"
                  type="url"
                  placeholder="https://youtu.be/..."
                  value={url}
                  onChange={(event) => {
                    setUrl(event.target.value);
                    setSelectedDiscoveryMessage(null);
                  }}
                  className={styles.input}
                  required
                />
                <button type="submit" className={styles.primaryButton} disabled={isLoadingTracks}>
                  {isLoadingTracks ? 'Inspecting…' : 'List subtitles'}
                </button>
              </div>
              {selectedDiscoveryMessage ? <p className={styles.status}>{selectedDiscoveryMessage}</p> : null}
              {listError ? <p className={styles.error}>{listError}</p> : null}
              {listing ? (
                <p className={styles.status}>
                  {listing.title ? <strong>{listing.title}</strong> : 'Subtitle tracks found'} ·{' '}
                  {listing.tracks.length} track{listing.tracks.length === 1 ? '' : 's'} available
                </p>
              ) : null}
            </form>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionHeaderRow}>
              <div>
                <h3 className={styles.sectionTitle}>Select subtitle tracks</h3>
              </div>
              <div className={styles.selectionSummary}>{selectedLabel}</div>
            </div>
            {tracks.length > 0 ? (
              <div className={styles.field}>
                <label className={styles.label} htmlFor="subtitle-track-list">
                  Subtitle tracks
                </label>
                <select
                  id="subtitle-track-list"
                  multiple
                  size={Math.min(10, Math.max(4, tracks.length))}
                  value={Array.from(selectedKeys)}
                  onChange={handleSelectionChange}
                  className={styles.select}
                >
                  {tracks.map((track) => {
                    const value = trackKey(track);
                    const kindLabel = track.kind === 'auto' ? 'Auto captions' : 'Manual captions';
                    const detail = track.name ? ` — ${track.name}` : '';
                    const formatLabel =
                      track.formats && track.formats.length > 0
                        ? ` (${track.formats.join(', ')})`
                        : '';
                    return (
                      <option key={value} value={value}>
                        {track.language} · {kindLabel}
                        {detail}
                        {formatLabel}
                      </option>
                    );
                  })}
                </select>
                <p className={styles.helpText}>
                  The list mirrors the classic subtitle UI. Hold Cmd/Ctrl (or Shift) to pick multiple tracks.
                </p>
              </div>
            ) : (
              <div className={styles.emptyState}>
                <p>No subtitle tracks listed yet. Inspect a YouTube URL to populate options.</p>
              </div>
            )}
          </div>

          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Download options</h3>
            <div className={styles.actions}>
              {videoFormats.length > 0 ? (
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="video-quality">
                    MP4 quality
                  </label>
                  <select
                    id="video-quality"
                    className={styles.input}
                    value={selectedVideoFormat ?? ''}
                    onChange={(event) => setSelectedVideoFormat(event.target.value || null)}
                  >
                    {videoFormats.map((format) => (
                      <option key={format.format_id} value={format.format_id}>
                        {describeFormat(format)}
                      </option>
                    ))}
                  </select>
                  <p className={styles.helpText}>
                    Format list is pulled when listing subtitles. Highest quality is preselected.
                  </p>
                </div>
              ) : (
                <p className={styles.helpText}>
                  {listing
                    ? 'No mp4 formats were detected for this video.'
                    : 'List subtitles to load available mp4 qualities.'}
                </p>
              )}
              {downloadError ? <p className={styles.error}>{downloadError}</p> : null}
              {downloadMessage ? (
                <p className={styles.success} aria-live="polite">
                  {downloadMessage}
                </p>
              ) : null}
              {downloadPaths.length > 0 ? (
                <div className={styles.downloadList}>
                  <p className={styles.status}>Saved files:</p>
                  <ul>
                    {downloadPaths.map((path) => (
                      <li key={path}>
                        <code>{path}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {videoDownloadPath ? (
                <p className={styles.status}>
                  Saved video to: <code>{videoDownloadPath}</code>
                </p>
              ) : null}
            </div>
          </div>
        </section>
      ) : (
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <h2 className={styles.cardTitle}>Downloads</h2>
              <p className={styles.cardHint}>
                Base path: <code>{libraryBaseDir}</code>
              </p>
            </div>
          </div>
          {libraryError ? <p className={styles.error}>{libraryError}</p> : null}
          {isLoadingLibrary && videos.length === 0 ? <p className={styles.status}>Loading downloads…</p> : null}
          {!isLoadingLibrary && videos.length === 0 ? (
            <p className={styles.status}>No downloaded YouTube videos found.</p>
          ) : null}
          <div className={styles.videoList}>
            {videos.map((video) => {
              const badge = videoSourceBadge(video);
              const hasLinkedJobs = (video.linked_job_ids ?? []).length > 0;
              const disableDelete = hasLinkedJobs || deletingVideoPath === video.path;
              const jobTitle = hasLinkedJobs
                ? `Linked jobs: ${(video.linked_job_ids ?? []).join(', ')}`
                : 'Delete downloaded video';
              return (
                <div key={video.path} className={`${styles.videoOption} ${styles.videoOptionStatic}`}>
                  <div className={styles.videoContent}>
                    <div className={styles.videoTitle}>{video.filename}</div>
                    <div className={styles.videoMeta}>
                      <span
                        className={`${styles.pill} ${styles.pillMeta} ${styles.pillSource}`}
                        title={`${badge.title} · ${video.folder || video.path}`}
                      >
                        <span aria-hidden="true">{badge.icon}</span>
                        <span>{badge.label}</span>
                      </span>
                      <span
                        className={`${styles.pill} ${styles.pillMeta}`}
                        title={`Size: ${formatBytes(video.size_bytes)}`}
                      >
                        <span aria-hidden="true">💾</span>
                        <span>{formatBytes(video.size_bytes)}</span>
                      </span>
                      <span
                        className={`${styles.pill} ${styles.pillMeta}`}
                        title={`Modified: ${formatDateLong(video.modified_at)}`}
                      >
                        <span aria-hidden="true">🕒</span>
                        <span>{formatDateShort(video.modified_at)}</span>
                      </span>
                      {hasLinkedJobs ? (
                        <span
                          className={`${styles.pill} ${styles.pillWarning}`}
                          title={`Linked jobs: ${(video.linked_job_ids ?? []).join(', ')}`}
                        >
                          🔗 {video.linked_job_ids?.length ?? 0} job
                          {(video.linked_job_ids?.length ?? 0) === 1 ? '' : 's'}
                        </span>
                      ) : null}
                      {video.subtitles.length === 0 ? (
                        <span className={`${styles.pill} ${styles.pillMeta} ${styles.pillMuted}`}>No subtitles</span>
                      ) : (
                        video.subtitles.map((sub) => (
                          <span
                            key={sub.path}
                            className={`${styles.pill} ${styles.pillMeta} ${
                              sub.format.toLowerCase() === 'ass' ? styles.pillAss : styles.pillMuted
                            }`}
                            title={sub.path}
                            aria-label={subtitleBadgeLabel(sub)}
                          >
                            <EmojiIcon
                              emoji={subtitleBadgeFlag(sub)}
                              className={styles.pillFlag}
                            />
                            <span>{(sub.format ?? '').toUpperCase()}</span>
                          </span>
                        ))
                      )}
                      <button
                        type="button"
                        className={`${styles.pill} ${styles.pillMeta} ${styles.pillAction}`}
                        onClick={() => void handleDeleteVideo(video)}
                        disabled={disableDelete}
                        title={jobTitle}
                        aria-label={jobTitle}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
