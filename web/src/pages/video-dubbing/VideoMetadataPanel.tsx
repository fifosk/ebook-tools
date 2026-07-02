import type { SubtitleTvMetadataPreviewResponse, YoutubeVideoMetadataPreviewResponse } from '../../api/dtos';
import type { VideoMetadataSection } from './videoDubbingTypes';
import {
  coerceRecord,
  formatCount,
  formatDurationSeconds,
  normalizeTextValue
} from './videoDubbingUtils';
import styles from '../VideoDubbingPage.module.css';
import { MetadataGrid } from '../../components/metadata/MetadataGrid';
import { MetadataLookupRow } from '../../components/metadata/MetadataLookupRow';
import { RawPayloadDetails } from '../../components/metadata/RawPayloadDetails';
import VideoTvMetadataPreview from './VideoTvMetadataPreview';

type VideoMetadataPanelProps = {
  metadataSourceName: string;
  metadataSection: VideoMetadataSection;
  metadataLookupSourceName: string;
  metadataPreview: SubtitleTvMetadataPreviewResponse | null;
  metadataLoading: boolean;
  metadataError: string | null;
  youtubeLookupSourceName: string;
  youtubeMetadataPreview: YoutubeVideoMetadataPreviewResponse | null;
  youtubeMetadataLoading: boolean;
  youtubeMetadataError: string | null;
  mediaMetadataDraft: Record<string, unknown> | null;
  onMetadataSectionChange: (section: VideoMetadataSection) => void;
  onMetadataLookupSourceNameChange: (value: string) => void;
  onYoutubeLookupSourceNameChange: (value: string) => void;
  onLookupMetadata: (sourceName: string, force: boolean) => void;
  onLookupYoutubeMetadata: (sourceName: string, force: boolean) => void;
  onClearTvMetadata: () => void;
  onClearYoutubeMetadata: () => void;
  onUpdateMediaMetadataDraft: (updater: (draft: Record<string, unknown>) => void) => void;
  onUpdateMediaMetadataSection: (sectionKey: string, updater: (section: Record<string, unknown>) => void) => void;
};

export default function VideoMetadataPanel({
  metadataSourceName,
  metadataSection,
  metadataLookupSourceName,
  metadataPreview,
  metadataLoading,
  metadataError,
  youtubeLookupSourceName,
  youtubeMetadataPreview,
  youtubeMetadataLoading,
  youtubeMetadataError,
  mediaMetadataDraft,
  onMetadataSectionChange,
  onMetadataLookupSourceNameChange,
  onYoutubeLookupSourceNameChange,
  onLookupMetadata,
  onLookupYoutubeMetadata,
  onClearTvMetadata,
  onClearYoutubeMetadata,
  onUpdateMediaMetadataDraft,
  onUpdateMediaMetadataSection
}: VideoMetadataPanelProps) {
  const hasMetadataSource = Boolean(
    metadataSourceName.trim() || (metadataSection === 'youtube' && youtubeLookupSourceName.trim())
  );

  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Metadata loader</h2>
          <p className={styles.cardHint}>
            {metadataSection === 'tv'
              ? 'Load TV episode metadata from TVMaze (no API key) and edit it before submitting the job.'
              : 'Load YouTube video metadata via yt-dlp (no API key) using the video id in brackets.'}
          </p>
        </div>
        <div className={styles.tabs} role="tablist" aria-label="Metadata sections">
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${metadataSection === 'tv' ? styles.tabButtonActive : ''}`}
            aria-selected={metadataSection === 'tv'}
            onClick={() => onMetadataSectionChange('tv')}
          >
            TVMaze
          </button>
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${metadataSection === 'youtube' ? styles.tabButtonActive : ''}`}
            aria-selected={metadataSection === 'youtube'}
            onClick={() => onMetadataSectionChange('youtube')}
          >
            YouTube
          </button>
        </div>
      </div>

      {!hasMetadataSource ? (
        <p className={styles.status}>Select a video/subtitle to load metadata.</p>
      ) : (
        <>
          {metadataSection === 'tv' ? (
            <>
              {metadataError ? <div className="alert" role="alert">{metadataError}</div> : null}
              <MetadataLookupRow
                query={metadataLookupSourceName}
                onQueryChange={onMetadataLookupSourceNameChange}
                onLookup={(force) => void onLookupMetadata(metadataLookupSourceName, force)}
                onClear={onClearTvMetadata}
                isLoading={metadataLoading}
                placeholder="Filename containing series/episode info"
                inputLabel="Lookup filename"
                hasResult={!!metadataPreview}
                disabled={!metadataLookupSourceName.trim()}
              />

              {metadataLoading ? <p className={styles.status}>Loading metadata…</p> : null}
              {!metadataLoading && metadataPreview ? (
                <VideoTvMetadataPreview
                  metadataSourceName={metadataSourceName}
                  metadataPreview={metadataPreview}
                  mediaMetadataDraft={mediaMetadataDraft}
                  onUpdateMediaMetadataDraft={onUpdateMediaMetadataDraft}
                  onUpdateMediaMetadataSection={onUpdateMediaMetadataSection}
                />
              ) : null}

              {!metadataLoading && !metadataPreview ? <p className={styles.status}>Metadata is not available yet.</p> : null}
            </>
          ) : null}

          {metadataSection === 'youtube' ? (
            <>
              {youtubeMetadataError ? <div className="alert" role="alert">{youtubeMetadataError}</div> : null}
              <MetadataLookupRow
                query={youtubeLookupSourceName}
                onQueryChange={onYoutubeLookupSourceNameChange}
                onLookup={(force) => void onLookupYoutubeMetadata(youtubeLookupSourceName, force)}
                onClear={onClearYoutubeMetadata}
                isLoading={youtubeMetadataLoading}
                placeholder="Example: Title [dQw4w9WgXcQ].mp4"
                inputLabel="Lookup video id / filename"
                hasResult={!!youtubeMetadataPreview}
                disabled={!youtubeLookupSourceName.trim()}
              />

              {youtubeMetadataLoading ? <p className={styles.status}>Loading metadata…</p> : null}
              {!youtubeMetadataLoading && youtubeMetadataPreview ? (
                (() => {
                  const youtube = mediaMetadataDraft ? coerceRecord(mediaMetadataDraft['youtube']) : null;
                  const title = normalizeTextValue(youtube ? youtube['title'] : null);
                  const channel =
                    normalizeTextValue(youtube ? youtube['channel'] : null) ??
                    normalizeTextValue(youtube ? youtube['uploader'] : null);
                  const webpageUrl = normalizeTextValue(youtube ? youtube['webpage_url'] : null);
                  const thumbnailUrl = normalizeTextValue(youtube ? youtube['thumbnail'] : null);
                  const summary = normalizeTextValue(youtube ? youtube['summary'] : null);
                  const description = normalizeTextValue(youtube ? youtube['description'] : null);
                  const views = formatCount(youtube ? youtube['view_count'] : null);
                  const likes = formatCount(youtube ? youtube['like_count'] : null);
                  const uploaded = normalizeTextValue(youtube ? youtube['upload_date'] : null);
                  const duration = formatDurationSeconds(youtube ? youtube['duration_seconds'] : null);
                  const rawErrorMessage = normalizeTextValue(youtube ? youtube['error'] : null);
                  // Don't show the "no video ID" error - it's expected for TV content without YouTube IDs
                  const isExpectedNoIdError = rawErrorMessage?.includes('Unable to locate a YouTube video id');
                  const errorMessage = isExpectedNoIdError ? null : rawErrorMessage;
                  const rawPayload = youtube ? youtube['raw_payload'] : null;

                  return (
                    <>
                      {thumbnailUrl ? (
                        <div className="tv-metadata-media" aria-label="YouTube thumbnail">
                          <a
                            href={webpageUrl ?? thumbnailUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="tv-metadata-media__still"
                          >
                            <img
                              src={thumbnailUrl}
                              alt={title ? `${title} thumbnail` : 'YouTube thumbnail'}
                              loading="lazy"
                              decoding="async"
                            />
                          </a>
                        </div>
                      ) : null}

                      <MetadataGrid
                        rows={[
                          { label: 'Source', value: youtubeMetadataPreview.source_name ?? youtubeLookupSourceName },
                          { label: 'Video id', value: youtubeMetadataPreview.parsed?.video_id },
                          { label: 'Title', value: title },
                          { label: 'Channel', value: channel },
                          { label: 'Duration', value: duration },
                          { label: 'Uploaded', value: uploaded },
                          { label: 'Views', value: views ? `${views}${likes ? ` · 👍 ${likes}` : ''}` : undefined },
                          { label: 'Link', value: webpageUrl ? 'Open on YouTube' : undefined, href: webpageUrl ?? undefined },
                          { label: 'Status', value: errorMessage },
                        ]}
                      />

                      {summary ? <p className={styles.status}>{summary}</p> : null}
                      {description ? (
                        <details>
                          <summary>Description</summary>
                          <pre style={{ whiteSpace: 'pre-wrap' }}>{description}</pre>
                        </details>
                      ) : null}
                      <RawPayloadDetails payload={rawPayload} />
                    </>
                  );
                })()
              ) : null}

              {!youtubeMetadataLoading && !youtubeMetadataPreview ? (
                <p className={styles.status}>Metadata is not available yet.</p>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </section>
  );
}
