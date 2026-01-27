type MetadataMediaPreviewProps = {
  /** URL of the image to display */
  imageUrl?: string;
  /** Optional link to wrap the image */
  linkUrl?: string;
  /** Alt text for the image */
  alt: string;
  /** Display variant affecting aspect ratio and styling */
  variant?: 'poster' | 'still' | 'thumbnail';
  /** Additional CSS class */
  className?: string;
};

/**
 * Displays a media preview image (cover, poster, thumbnail, still).
 * Supports linking to external sources and different aspect ratio variants.
 */
export function MetadataMediaPreview({
  imageUrl,
  linkUrl,
  alt,
  variant = 'poster',
  className,
}: MetadataMediaPreviewProps) {
  if (!imageUrl) {
    return null;
  }

  const variantClass = `metadata-media-preview--${variant}`;
  const classes = ['metadata-media-preview', variantClass, className]
    .filter(Boolean)
    .join(' ');

  const image = <img src={imageUrl} alt={alt} loading="lazy" />;

  if (linkUrl) {
    return (
      <a
        href={linkUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={classes}
      >
        {image}
      </a>
    );
  }

  return <div className={classes}>{image}</div>;
}
