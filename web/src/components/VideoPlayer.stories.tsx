import { useState } from 'react';
import VideoPlayer, { type VideoFile } from './VideoPlayer';

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

export const BasicPlayback = () => {
  const [index, setIndex] = useState(0);

  const nextVideo = () => {
    setIndex((previous) => (previous + 1) % sampleVideos.length);
  };

  return (
    <div>
      <button type="button" onClick={nextVideo}>
        Play next video
      </button>
      <VideoPlayer file={sampleVideos[index]} />
    </div>
  );
};
