import type { PipelineFileBrowserResponse, PipelineFileEntry } from '../../api/dtos';
import FileSelectionDialog from '../FileSelectionDialog';

export type BookNarrationFileDialogMode = 'input' | 'output';

interface BookNarrationFileDialogProps {
  activeFileDialog: BookNarrationFileDialogMode | null;
  fileOptions: PipelineFileBrowserResponse | null;
  onInputFileSelect: (path: string) => void;
  onOutputPathSelect: (path: string) => void;
  onClose: () => void;
  onDeleteEbook: (entry: PipelineFileEntry) => void;
}

export function BookNarrationFileDialog({
  activeFileDialog,
  fileOptions,
  onInputFileSelect,
  onOutputPathSelect,
  onClose,
  onDeleteEbook
}: BookNarrationFileDialogProps) {
  if (!activeFileDialog || !fileOptions) {
    return null;
  }

  const isInputDialog = activeFileDialog === 'input';

  return (
    <FileSelectionDialog
      title={isInputDialog ? 'Select ebook file' : 'Select output path'}
      description={
        isInputDialog
          ? 'Choose an EPUB file from the configured books directory.'
          : 'Select an existing output file or directory as the base path.'
      }
      files={isInputDialog ? fileOptions.ebooks : fileOptions.outputs}
      onSelect={(path) => {
        if (isInputDialog) {
          onInputFileSelect(path);
        } else {
          onOutputPathSelect(path);
        }
        onClose();
      }}
      onClose={onClose}
      onDelete={
        isInputDialog
          ? (entry) => {
              onDeleteEbook(entry);
            }
          : undefined
      }
    />
  );
}
