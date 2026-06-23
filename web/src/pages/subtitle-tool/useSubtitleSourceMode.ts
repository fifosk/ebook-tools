import { useCallback, useMemo, useState } from 'react';
import type { SubtitleSourceEntry } from '../../api/dtos';
import type { SubtitleSourceMode } from './subtitleToolTypes';
import {
  isAssSubtitleSelection,
  resolveSubtitleMetadataSourceName
} from './subtitleToolUtils';

type UseSubtitleSourceModeInput = {
  selectedSource: string;
  selectedSourceEntry: SubtitleSourceEntry | null | undefined;
  onSubmitErrorReset?: () => void;
};

export function useSubtitleSourceMode({
  selectedSource,
  selectedSourceEntry,
  onSubmitErrorReset
}: UseSubtitleSourceModeInput) {
  const [sourceMode, setSourceMode] = useState<SubtitleSourceMode>('existing');
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const isAssSelection = useMemo(
    () => isAssSubtitleSelection(sourceMode, selectedSourceEntry),
    [sourceMode, selectedSourceEntry]
  );

  const metadataSourceName = useMemo(
    () =>
      resolveSubtitleMetadataSourceName({
        sourceMode,
        uploadFileName: uploadFile?.name,
        selectedSourceName: selectedSourceEntry?.name,
        selectedSourcePath: selectedSource
      }),
    [selectedSource, selectedSourceEntry, sourceMode, uploadFile]
  );

  const handleSourceModeChange = useCallback(
    (mode: SubtitleSourceMode) => {
      setSourceMode(mode);
      onSubmitErrorReset?.();
    },
    [onSubmitErrorReset]
  );

  const handleUploadFileChange = useCallback((file: File | null) => {
    setUploadFile(file);
  }, []);

  const clearUploadFile = useCallback(() => {
    setUploadFile(null);
  }, []);

  return {
    sourceMode,
    uploadFile,
    isAssSelection,
    metadataSourceName,
    handleSourceModeChange,
    handleUploadFileChange,
    clearUploadFile
  };
}
