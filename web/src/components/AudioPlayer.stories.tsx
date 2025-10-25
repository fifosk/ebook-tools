import { useState } from 'react';
import AudioPlayer, { AudioFile } from './AudioPlayer';

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

export const ProgressiveUpdates = () => {
  const [files, setFiles] = useState<AudioFile[]>(sampleTracks.slice(0, 1));

  const addNextTrack = () => {
    setFiles((previous) => {
      if (previous.length >= sampleTracks.length) {
        return previous;
      }

      return [...previous, sampleTracks[previous.length]];
    });
  };

  return (
    <div>
      <button type="button" onClick={addNextTrack} disabled={files.length >= sampleTracks.length}>
        Add next audio track
      </button>
      <AudioPlayer files={files} />
    </div>
  );
};
