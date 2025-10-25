import { useState } from 'react';
import TextViewer, { type TextFile } from './TextViewer';

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

export const BasicReader = () => {
  const [index, setIndex] = useState(0);

  const nextFile = () => {
    setIndex((previous) => (previous + 1) % sampleFiles.length);
  };

  return (
    <div>
      <button type="button" onClick={nextFile}>
        Show next text file
      </button>
      <TextViewer file={sampleFiles[index]} />
    </div>
  );
};
