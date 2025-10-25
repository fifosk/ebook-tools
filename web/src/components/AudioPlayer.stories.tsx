import { useState } from 'react';
import AudioPlayer, { type AudioFile } from './AudioPlayer';

const sampleTracks: AudioFile[] = [
  {
    id: 'intro',
    name: 'Introduction',
    url: 'https://example.com/audio/intro.mp3'
  },
  {
    id: 'chapter-1',
    name: 'Chapter 1',
    url: 'https://example.com/audio/chapter-1.mp3'
  },
  {
    id: 'chapter-2',
    name: 'Chapter 2',
    url: 'https://example.com/audio/chapter-2.mp3'
  }
];

export default {
  title: 'Components/AudioPlayer',
  component: AudioPlayer
};

export const BasicPlayback = () => {
  const [index, setIndex] = useState(0);

  const nextTrack = () => {
    setIndex((previous) => (previous + 1) % sampleTracks.length);
  };

  return (
    <div>
      <button type="button" onClick={nextTrack}>
        Play next track
      </button>
      <AudioPlayer file={sampleTracks[index]} />
    </div>
  );
};
