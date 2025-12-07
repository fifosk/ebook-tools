import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  deleteYoutubeVideo,
  downloadYoutubeSubtitle,
  downloadYoutubeVideo,
  fetchYoutubeLibrary,
  fetchYoutubeSubtitleTracks
} from '../api/client';
import type {
  YoutubeNasLibraryResponse,
  YoutubeNasVideo,
  YoutubeSubtitleKind,
  YoutubeSubtitleListResponse,
  YoutubeSubtitleTrack,
  YoutubeVideoFormat
} from '../api/dtos';
import styles from './YoutubeSubtitlesPage.module.css';

const SUBTITLE_NAS_DIR = '/Volumes/Data/Download/Subtitles';
const VIDEO_NAS_DIR = '/Volumes/Data/Download/DStation';

function resolveDefaultTrack(tracks: YoutubeSubtitleTrack[]): YoutubeSubtitleTrack | null {
  if (!tracks.length) {
    return null;
  }
  const manualEnglish = tracks.find(
    (track) => track.kind === 'manual' && track.language.toLowerCase().startsWith('en')
  );
  if (manualEnglish) {
    return manualEnglish;
  }
  const firstManual = tracks.find((track) => track.kind === 'manual');
  return firstManual ?? tracks[0];
}

function trackKey(track: { language: string; kind: YoutubeSubtitleKind }): string {
  return `${track.language}__${track.kind}`;
}

function describeFormat(format: YoutubeVideoFormat): string {
  const parts: string[] = [];
  if (format.resolution) {
    parts.push(format.resolution);
  }
  if (format.fps) {
    parts.push(`${format.fps} fps`);
  }
  if (format.note) {
    parts.push(format.note);
  }
  if (format.bitrate_kbps) {
    parts.push(`${Math.round(format.bitrate_kbps)} kbps`);
  }
  if (format.filesize) {
    parts.push(format.filesize);
  }
  parts.push(`itag ${format.format_id}`);
  return `mp4 • ${parts.join(' • ')}`;
}

function isYoutubeSource(video: YoutubeNasVideo): boolean {
  return (video.source || '').toLowerCase() === 'youtube';
}

function videoSourceBadge(video: YoutubeNasVideo): { icon: string; label: string; title: string } {
  if (isYoutubeSource(video)) {
    return { icon: '📺', label: 'YT', title: 'YouTube download' };
  }
  return { icon: '🗃️', label: 'NAS', title: 'NAS video' };
}

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes < 0) {
    return '—';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`;
}

function formatDateShort(value?: string | null): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDateLong(value?: string | null): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  return date.toLocaleString();
}

function subtitleBadgeLabel(subtitle: YoutubeNasVideo['subtitles'][number]): string {
  const language = subtitle.language ? subtitle.language.toUpperCase() : '—';
  const format = subtitle.format ? subtitle.format.toUpperCase() : '';
  return `${language} ${format}`.trim();
}

export default function YoutubeSubtitlesPage() {
  const [url, setUrl] = useState('');
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null);
  const [listing, setListing] = useState<YoutubeSubtitleListResponse | null>(null);
  const [tracks, setTracks] = useState<YoutubeSubtitleTrack[]>([]);
  const [videoFormats, setVideoFormats] = useState<YoutubeVideoFormat[]>([]);
  const [selectedVideoFormat, setSelectedVideoFormat] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [isLoadingTracks, setIsLoadingTracks] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadVideo, setDownloadVideo] = useState(true);
  const [videoPath, setVideoPath] = useState(VIDEO_NAS_DIR);
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

  const handleFetchTracks = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedUrl = url.trim();
      if (!trimmedUrl) {
        setListError('Provide a YouTube video URL to inspect available subtitles.');
        return;
      }

      setIsLoadingTracks(true);
      setListError(null);
      setDownloadError(null);
      setDownloadMessage(null);
      setDownloadPaths([]);
      setVideoDownloadPath(null);
      setListing(null);
      setTracks([]);
      setVideoFormats([]);
      setSelectedVideoFormat(null);
      setSelectedKeys(new Set());

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
    [url]
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
  }, [refreshDownloads]);

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
    const resolvedVideoDir = videoPath.trim() || VIDEO_NAS_DIR;
    const timestamp = downloadVideo ? new Date().toISOString() : undefined;

    const savedFiles: string[] = [];
    try {
      for (const track of selectedTracks) {
        const payload = {
          url: activeUrl,
          language: track.language,
          kind: track.kind,
          video_output_dir: downloadVideo ? resolvedVideoDir : undefined,
          timestamp
        } as const;
        const response = await downloadYoutubeSubtitle(payload);
        savedFiles.push(response.filename);
      }
      setDownloadPaths(savedFiles);
      setDownloadMessage(`Saved ${savedFiles.length} file(s) to ${SUBTITLE_NAS_DIR}`);
      if (downloadVideo) {
        const videoResponse = await downloadYoutubeVideo({
          url: activeUrl,
          output_dir: resolvedVideoDir,
          format_id: selectedVideoFormat || undefined,
          timestamp
        });
        setVideoDownloadPath(videoResponse.output_path || videoResponse.filename);
      }
      await refreshDownloads();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message || 'Subtitle download failed.'
          : 'Subtitle download failed.';
      setDownloadError(message);
    } finally {
      setIsDownloading(false);
    }
  }, [resolvedUrl, url, selectedTracks, downloadVideo, videoPath, selectedVideoFormat, refreshDownloads]);

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

  const libraryBaseDir = library?.base_dir ?? VIDEO_NAS_DIR;

  return (
    <div className={styles.container}>
      <section className={styles.card}>
        <header className={styles.cardHeader}>
          <div>
            <p className={styles.kicker}>YouTube captions → NAS</p>
            <h2 className={styles.cardTitle}>Download subtitles as SRT</h2>
            <p className={styles.cardHint}>
              Probe a YouTube video with yt-dlp, select one or more languages, and write SRT files into the subtitle NAS directory.
            </p>
            <p className={styles.pathNote}>
              Target directory: <code>{SUBTITLE_NAS_DIR}</code>
            </p>
          </div>
          {listing ? (
            <div className={styles.videoBadge}>
              <span className={styles.badgeLabel}>Video ID</span>
              <strong className={styles.badgeValue}>{listing.video_id}</strong>
            </div>
          ) : null}
        </header>
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
              onChange={(event) => setUrl(event.target.value)}
              className={styles.input}
              required
            />
            <button type="submit" className={styles.primaryButton} disabled={isLoadingTracks}>
              {isLoadingTracks ? 'Inspecting…' : 'List subtitles'}
            </button>
          </div>
          {listError ? <p className={styles.error}>{listError}</p> : null}
          {listing ? (
            <p className={styles.status}>
              {listing.title ? <strong>{listing.title}</strong> : 'Subtitle tracks found'} ·{' '}
              {listing.tracks.length} track{listing.tracks.length === 1 ? '' : 's'} available
            </p>
          ) : null}
        </form>
      </section>

      <section className={styles.card}>
        <header className={styles.cardHeader}>
          <div>
            <p className={styles.kicker}>Languages</p>
            <h2 className={styles.cardTitle}>Select subtitle tracks</h2>
            <p className={styles.cardHint}>
              Use Cmd/Ctrl + click to pick multiple tracks (manual and auto). SRT output is generated for each selection.
            </p>
          </div>
          <div className={styles.selectionSummary}>{selectedLabel}</div>
        </header>
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
      </section>

      <section className={styles.card}>
        <header className={styles.cardHeader}>
          <div>
            <p className={styles.kicker}>Download</p>
            <h2 className={styles.cardTitle}>Save SRT files</h2>
            <p className={styles.cardHint}>
              Downloads run with yt-dlp and reuse the Android player client args for YouTube; we always convert to SRT before saving.
            </p>
          </div>
        </header>
        <div className={styles.actions}>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={downloadVideo}
              onChange={(event) => setDownloadVideo(event.target.checked)}
            />
            Also download video to NAS ({VIDEO_NAS_DIR})
          </label>
          {downloadVideo ? (
            <>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="video-path">
                  Video output directory
                </label>
                <input
                  id="video-path"
                  type="text"
                  className={styles.input}
                  value={videoPath}
                  onChange={(event) => setVideoPath(event.target.value)}
                  placeholder={VIDEO_NAS_DIR}
                />
                <p className={styles.helpText}>Folder will include video title and download timestamp.</p>
              </div>
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
            </>
          ) : null}
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => {
              void handleDownload();
            }}
            disabled={isDownloading || !selectedTracks.length || !tracks.length}
          >
            {isDownloading ? 'Downloading…' : 'Download subtitles'}
          </button>
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
          {downloadVideo && videoDownloadPath ? (
            <p className={styles.status}>
              Saved video to: <code>{videoDownloadPath}</code>
            </p>
          ) : null}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <p className={styles.kicker}>Downloads</p>
            <h2 className={styles.cardTitle}>Downloaded YouTube videos</h2>
            <p className={styles.cardHint}>
              Base path: <code>{libraryBaseDir}</code>
            </p>
          </div>
          <div>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => void refreshDownloads()}
              disabled={isLoadingLibrary}
            >
              {isLoadingLibrary ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </div>
        {libraryError ? <p className={styles.error}>{libraryError}</p> : null}
        {isLoadingLibrary && videos.length === 0 ? (
          <p className={styles.status}>Loading downloads…</p>
        ) : null}
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
                  </div>
                  <div className={styles.subtitleRow} aria-label="Subtitles next to video">
                    {video.subtitles.length === 0 ? (
                      <span className={`${styles.pill} ${styles.pillMuted}`}>No subtitles</span>
                    ) : (
                      video.subtitles.map((sub) => (
                        <span
                          key={sub.path}
                          className={`${styles.pill} ${
                            sub.format.toLowerCase() === 'ass' ? styles.pillAss : styles.pillMuted
                          }`}
                          title={sub.path}
                        >
                          {subtitleBadgeLabel(sub)}
                        </span>
                      ))
                    )}
                  </div>
                </div>
                <div className={styles.videoActions}>
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
            );
          })}
        </div>
      </section>
    </div>
  );
}
