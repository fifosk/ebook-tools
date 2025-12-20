import type {
  YoutubeInlineSubtitleStream,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import EmojiIcon from '../../components/EmojiIcon';
import { resolveSubtitleFlag, subtitleLanguageDetail } from '../../utils/subtitles';
import {
  formatBytes,
  formatDate,
  formatDateShort,
  subtitleLabel,
  subtitleStreamLabel,
  videoSourceBadge
} from './videoDubbingUtils';
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
      {isLoading && videos.length === 0 ? <p className={styles.status}>Loading videos…</p> : null}
      {!isLoading && videos.length === 0 ? (
        <p className={styles.status}>No downloaded videos found in this directory.</p>
      ) : null}
      <div className={styles.videoList}>
        {videos.map((video) => {
          const isActive = video.path === selectedVideoPath;
          const sourceBadge = videoSourceBadge(video);
          const hasLinkedJobs = (video.linked_job_ids ?? []).length > 0;
          const disableDelete = hasLinkedJobs || deletingVideoPath === video.path;
          const jobTitle = hasLinkedJobs
            ? `Linked jobs: ${(video.linked_job_ids ?? []).join(', ')}`
            : 'Delete downloaded video';
          return (
            <label key={video.path} className={`${styles.videoOption} ${isActive ? styles.videoOptionActive : ''}`}>
              <input
                type="radio"
                name="video"
                value={video.path}
                checked={isActive}
                onChange={() => onSelectVideo(video)}
              />
              <div className={styles.videoContent}>
                <div className={styles.videoTitle}>{video.filename}</div>
                <div className={styles.videoMeta}>
                  <span
                    className={`${styles.pill} ${styles.pillMeta} ${styles.pillSource}`}
                    title={`${sourceBadge.title} · ${video.folder || video.path}`}
                  >
                    <span aria-hidden="true">{sourceBadge.icon}</span>
                    <span>{sourceBadge.label}</span>
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
                    title={`Modified: ${formatDate(video.modified_at)}`}
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
                        aria-label={subtitleLabel(sub)}
                        title={subtitleLabel(sub)}
                      >
                        <EmojiIcon
                          emoji={resolveSubtitleFlag(sub.language, sub.path, sub.filename)}
                          className={styles.pillFlag}
                        />
                        <span>{(sub.format ?? '').toUpperCase()}</span>
                      </span>
                    ))
                  )}
                  <button
                    type="button"
                    className={`${styles.pill} ${styles.pillMeta} ${styles.pillAction}`}
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      if (!isActive) {
                        return;
                      }
                      void onExtractSubtitles();
                    }}
                    disabled={
                      !isActive ||
                      !canExtractEmbedded ||
                      isExtractingSubtitles ||
                      isLoadingStreams ||
                      Boolean(deletingSubtitlePath)
                    }
                    title="Inspect and extract subtitle streams from this video"
                    aria-label="Inspect and extract subtitle streams from this video"
                  >
                    ⬇️
                  </button>
                  <button
                    type="button"
                    className={`${styles.pill} ${styles.pillMeta} ${styles.pillAction}`}
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void onDeleteVideo(video);
                    }}
                    disabled={disableDelete}
                    title={jobTitle}
                    aria-label={jobTitle}
                  >
                    🗑️
                  </button>
                </div>
                {isActive ? (
                  <div className={styles.nestedSubtitleCard} aria-label="Subtitle selection">
                    <div className={styles.nestedHeader}>
                      <h3 className={styles.cardTitle}>Subtitle selection</h3>
                      <p className={styles.cardHint}>Pick a nearby subtitle file or extract embedded tracks before dubbing.</p>
                    </div>
                    <div>
                      <h4 className={styles.sectionTitle}>Choose subtitle</h4>
                      {subtitleNotice ? <p className={styles.status}>{subtitleNotice}</p> : null}
                      <div className={styles.subtitleList}>
                        {playableSubtitles.map((sub) => {
                          const isDeleting = deletingSubtitlePath === sub.path;
                          return (
                            <div
                              key={sub.path}
                              className={`${styles.subtitleCard} ${selectedSubtitlePath === sub.path ? styles.subtitleCardActive : ''}`}
                            >
                              <label className={styles.subtitleChoice}>
                                <input
                                  type="radio"
                                  name="subtitle"
                                  value={sub.path}
                                  checked={selectedSubtitlePath === sub.path}
                                  disabled={Boolean(deletingSubtitlePath)}
                                  onChange={() => onSelectSubtitle(sub.path)}
                                />
                                <div className={styles.subtitleBody}>
                                  <div className={styles.subtitleHeaderRow}>
                                    <div className={styles.subtitleName}>{sub.filename}</div>
                                    <div className={styles.subtitleBadges} aria-label="Subtitle details">
                                      <span className={`${styles.pill} ${styles.pillFormat}`}>
                                        {sub.format.toUpperCase()}
                                      </span>
                                      <span
                                        className={`${styles.pill} ${styles.pillMuted}`}
                                        title={subtitleLanguageDetail(sub.language, sub.path, sub.filename)}
                                        aria-label={subtitleLanguageDetail(sub.language, sub.path, sub.filename)}
                                      >
                                        <EmojiIcon
                                          emoji={resolveSubtitleFlag(sub.language, sub.path, sub.filename)}
                                          className={styles.pillFlag}
                                        />
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </label>
                              <div className={styles.subtitleActions}>
                                <button
                                  type="button"
                                  className={styles.dangerButton}
                                  onClick={() => void onDeleteSubtitle(sub)}
                                  disabled={Boolean(deletingSubtitlePath) || isExtractingSubtitles}
                                  title={`Delete ${sub.filename}`}
                                  aria-label={`Delete ${sub.filename}`}
                                >
                                  {isDeleting ? '…' : '🗑'}
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      {isChoosingStreams && extractableStreams.length > 0 ? (
                        <div className={styles.streamChooser}>
                          <div className={styles.streamHeader}>
                            <div className={styles.streamTitle}>Select which tracks to extract</div>
                            <p className={styles.streamHint}>Default selection prefers English when present.</p>
                          </div>
                          <div className={styles.streamList}>
                            {availableSubtitleStreams.map((stream) => {
                              const language = stream.language ?? '';
                              const selected = language ? selectedStreamLanguages.has(language) : false;
                              const disabled = !stream.can_extract || !language || isExtractingSubtitles;
                              return (
                                <label key={`${stream.index}-${language || 'unknown'}`} className={styles.streamItem}>
                                  <input
                                    type="checkbox"
                                    disabled={disabled}
                                    checked={selected}
                                    onChange={(event) => onToggleSubtitleStream(language, event.target.checked)}
                                  />
                                  <div className={styles.streamBody}>
                                    <div className={styles.streamLabel}>{subtitleStreamLabel(stream)}</div>
                                    <div className={styles.streamMeta}>
                                      <span>Stream #{stream.index}</span>
                                      <span aria-hidden="true">·</span>
                                      <span>{language || 'No language tag'}</span>
                                      {stream.codec ? <span className={styles.streamBadge}>{stream.codec}</span> : null}
                                      {!stream.can_extract ? (
                                        <span className={`${styles.streamBadge} ${styles.streamBadgeMuted}`}>Image-based</span>
                                      ) : null}
                                    </div>
                                    {!stream.can_extract ? (
                                      <p className={styles.streamHint}>Image-based subtitles (e.g. PGS/VobSub) need OCR.</p>
                                    ) : null}
                                    {!language ? (
                                      <p className={styles.streamHint}>
                                        No language tag detected; choose a tagged stream or extract all tracks.
                                      </p>
                                    ) : null}
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                          <div className={styles.streamActions}>
                            <button
                              className={styles.primaryButton}
                              type="button"
                              onClick={() => void onConfirmSubtitleStreams()}
                              disabled={isExtractingSubtitles}
                            >
                              {isExtractingSubtitles ? 'Extracting…' : 'Extract selected tracks'}
                            </button>
                            <button
                              className={styles.secondaryButton}
                              type="button"
                              onClick={onCancelStreamSelection}
                              disabled={isExtractingSubtitles}
                            >
                              Cancel
                            </button>
                            <button
                              className={styles.secondaryButton}
                              type="button"
                              onClick={() => void onExtractAllStreams()}
                              disabled={isExtractingSubtitles}
                            >
                              Extract all text tracks
                            </button>
                          </div>
                        </div>
                      ) : null}
                      <p className={styles.fieldHint}>
                        Pulls subtitle streams from the selected video (writes .srt files next to it).
                      </p>
                      {extractError ? <p className={styles.error}>{extractError}</p> : null}
                    </div>
                  </div>
                ) : null}
              </div>
            </label>
          );
        })}
      </div>
    </section>
  );
}
