import { useState } from 'react';
import TextViewer, { TextFile } from './TextViewer';

const sampleFiles: TextFile[] = [
  {
    id: 'intro',
    name: 'Introduction',
    content: 'Welcome to the sample document.'
  },
  {
    id: 'chapter-1',
    name: 'Chapter 1',
    content: 'This chapter demonstrates incremental updates.'
  },
  {
    id: 'chapter-2',
    name: 'Chapter 2',
    content: 'Each click appends another section to the viewer.'
  }
];

export default {
  title: 'Components/TextViewer',
  component: TextViewer
};

export const ProgressiveUpdates = () => {
  const [files, setFiles] = useState<TextFile[]>(sampleFiles.slice(0, 1));

  const addNextFile = () => {
    setFiles((previous) => {
      if (previous.length >= sampleFiles.length) {
        return previous;
      }

      return [...previous, sampleFiles[previous.length]];
    });
  };

  return (
    <div>
      <button type="button" onClick={addNextFile} disabled={files.length >= sampleFiles.length}>
        Add next text file
      </button>
      <TextViewer files={files} />
    </div>
  );
};
