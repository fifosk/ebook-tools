import { useState } from 'react';
import VideoPlayer, { VideoFile } from './VideoPlayer';

const sampleVideos: VideoFile[] = [
  {
    id: 'teaser',
    name: 'Teaser',
    url: 'https://example.com/video/teaser.mp4',
    poster: 'https://example.com/video/teaser.jpg'
  },
  {
    id: 'trailer',
    name: 'Trailer',
    url: 'https://example.com/video/trailer.mp4'
  },
  {
    id: 'feature',
    name: 'Feature',
    url: 'https://example.com/video/feature.mp4'
  }
];

export default {
  title: 'Components/VideoPlayer',
  component: VideoPlayer
};

export const ProgressiveUpdates = () => {
  const [files, setFiles] = useState<VideoFile[]>(sampleVideos.slice(0, 1));

  const addNextVideo = () => {
    setFiles((previous) => {
      if (previous.length >= sampleVideos.length) {
        return previous;
      }

      return [...previous, sampleVideos[previous.length]];
    });
  };

  return (
    <div>
      <button type="button" onClick={addNextVideo} disabled={files.length >= sampleVideos.length}>
        Add next video
      </button>
      <VideoPlayer files={files} />
    </div>
  );
};
