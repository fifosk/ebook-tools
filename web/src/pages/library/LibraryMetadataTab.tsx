import type { LibraryItem } from '../../api/dtos';
import JobTypeGlyphBadge from '../../components/JobTypeGlyphBadge';
import type { JobTypeGlyph } from '../../utils/jobGlyphs';
import styles from '../LibraryPage.module.css';
import {
  formatCount,
  formatLibraryTimestamp,
  formatYoutubeUploadDate,
  type LibraryItemType,
} from './libraryPageMetadata';

type LibraryMetadataTabProps = {
  item: LibraryItem;
  itemType: LibraryItemType;
  jobGlyph: JobTypeGlyph;
  jobType: string | null;
  youtubeMetadata: Record<string, unknown> | null;
};

export default function LibraryMetadataTab({
  item,
  itemType,
  jobGlyph,
  jobType,
  youtubeMetadata,
}: LibraryMetadataTabProps) {
  const youtubeChannel = resolveYoutubeChannel(youtubeMetadata);
  const youtubeViews = youtubeMetadata ? formatCount(youtubeMetadata.view_count) : null;
  const youtubeLikes = youtubeMetadata ? formatCount(youtubeMetadata.like_count) : null;
  const youtubeUploaded = youtubeMetadata
    ? formatYoutubeUploadDate(youtubeMetadata.upload_date)
    : null;
  const youtubeDuration =
    typeof youtubeMetadata?.duration_seconds === 'number'
      ? `${Math.trunc(youtubeMetadata.duration_seconds)}s`
      : null;
  const youtubeLink = resolveYoutubeLink(youtubeMetadata);

  return (
    <div className={styles.tabContent}>
      <ul className={styles.detailList}>
        <li className={styles.detailItem}>
          <strong>Job ID:</strong> {item.jobId}
        </li>
        <li className={styles.detailItem}>
          <strong>Type:</strong> {libraryItemTypeLabel(itemType)}
        </li>
        <li className={styles.detailItem}>
          <strong>Job:</strong>{' '}
          <JobTypeGlyphBadge glyph={jobGlyph} className={styles.detailsJobGlyphInline} />{' '}
          {jobType ?? '—'}
        </li>
        <li className={styles.detailItem}>
          <strong>ISBN:</strong> {item.isbn && item.isbn.trim() ? item.isbn : '—'}
        </li>
        <li className={styles.detailItem}>
          <strong>{sourceLabel(itemType)}</strong> {item.sourcePath ? item.sourcePath : '—'}
        </li>
        {itemType === 'video' && youtubeMetadata ? (
          <>
            <li className={styles.detailItem}>
              <strong>YouTube channel:</strong> {youtubeChannel ?? '—'}
            </li>
            <li className={styles.detailItem}>
              <strong>YouTube views:</strong> {youtubeViews ?? '—'}
              {youtubeLikes ? ` · 👍 ${youtubeLikes}` : ''}
            </li>
            <li className={styles.detailItem}>
              <strong>YouTube uploaded:</strong> {youtubeUploaded ?? '—'}
            </li>
            <li className={styles.detailItem}>
              <strong>YouTube duration:</strong> {youtubeDuration ?? '—'}
            </li>
            <li className={styles.detailItem}>
              <strong>YouTube link:</strong>{' '}
              {youtubeLink ? (
                <a href={youtubeLink} target="_blank" rel="noopener noreferrer">
                  Open
                </a>
              ) : (
                '—'
              )}
            </li>
          </>
        ) : null}
        <li className={styles.detailItem}>
          <strong>Created:</strong> {formatLibraryTimestamp(item.createdAt)}
        </li>
        <li className={styles.detailItem}>
          <strong>Updated:</strong> {formatLibraryTimestamp(item.updatedAt)}
        </li>
        <li className={styles.detailItem}>
          <strong>Library path:</strong> {item.libraryPath}
        </li>
      </ul>
      <div>
        <h3>Raw Metadata</h3>
        <pre className={styles.metadataBlock}>
          {JSON.stringify(item.metadata, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function libraryItemTypeLabel(itemType: LibraryItemType): string {
  switch (itemType) {
    case 'video':
      return 'Video';
    case 'narrated_subtitle':
      return 'Narrated Subtitle';
    default:
      return 'Book';
  }
}

function sourceLabel(itemType: LibraryItemType): string {
  switch (itemType) {
    case 'video':
      return 'Source video:';
    case 'narrated_subtitle':
      return 'Source subtitle:';
    default:
      return 'Source file:';
  }
}

function resolveYoutubeChannel(youtubeMetadata: Record<string, unknown> | null): string | null {
  const channel = trimmedString(youtubeMetadata?.channel);
  if (channel) {
    return channel;
  }
  return trimmedString(youtubeMetadata?.uploader);
}

function resolveYoutubeLink(youtubeMetadata: Record<string, unknown> | null): string | null {
  return trimmedString(youtubeMetadata?.webpage_url);
}

function trimmedString(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
