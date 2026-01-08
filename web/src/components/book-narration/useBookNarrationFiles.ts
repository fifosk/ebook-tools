import { useCallback, useEffect, useState } from 'react';
import type { DragEvent } from 'react';
import type { PipelineFileBrowserResponse, PipelineFileEntry } from '../../api/dtos';
import { deletePipelineEbook, fetchPipelineFiles, uploadEpubFile } from '../../api/client';
import { loadCachedBookMetadataJson } from '../../utils/bookMetadataCache';
import type { FormState } from './bookNarrationFormTypes';
import { DEFAULT_FORM_STATE, PREFERRED_SAMPLE_EBOOK } from './bookNarrationFormDefaults';
import { deriveBaseOutputName } from './bookNarrationFormUtils';

type UseBookNarrationFilesOptions = {
  isGeneratedSource: boolean;
  forcedBaseOutputFile: string | null;
  markUserEditedField: (key: keyof FormState) => void;
  normalizePath: (value: string | null | undefined) => string | null;
  resolveStartFromHistory: (inputPath: string) => number | null;
  setFormState: React.Dispatch<React.SetStateAction<FormState>>;
  prefillAppliedRef: React.MutableRefObject<string | null>;
  userEditedStartRef: React.MutableRefObject<boolean>;
  userEditedInputRef: React.MutableRefObject<boolean>;
  userEditedEndRef: React.MutableRefObject<boolean>;
  lastAutoEndSentenceRef: React.MutableRefObject<string | null>;
};

export function useBookNarrationFiles({
  isGeneratedSource,
  forcedBaseOutputFile,
  markUserEditedField,
  normalizePath,
  resolveStartFromHistory,
  setFormState,
  prefillAppliedRef,
  userEditedStartRef,
  userEditedInputRef,
  userEditedEndRef,
  lastAutoEndSentenceRef,
}: UseBookNarrationFilesOptions) {
  const [fileOptions, setFileOptions] = useState<PipelineFileBrowserResponse | null>(null);
  const [fileDialogError, setFileDialogError] = useState<string | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [activeFileDialog, setActiveFileDialog] = useState<'input' | 'output' | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [recentUploadName, setRecentUploadName] = useState<string | null>(null);

  const handleInputFileChange = useCallback(
    (value: string) => {
      setRecentUploadName(null);
      setUploadError(null);
      userEditedStartRef.current = false;
      userEditedInputRef.current = true;
      userEditedEndRef.current = false;
      lastAutoEndSentenceRef.current = null;
      markUserEditedField('input_file');
      const normalizedInput = normalizePath(value);
      const cachedBookMetadata = normalizedInput ? loadCachedBookMetadataJson(normalizedInput) : null;
      setFormState((previous) => {
        if (previous.input_file === value) {
          return previous;
        }
        const previousDerivedBase = deriveBaseOutputName(previous.input_file);
        const nextDerivedBase = deriveBaseOutputName(value);
        const shouldUpdateBase =
          !previous.base_output_file || previous.base_output_file === previousDerivedBase;
        const suggestedStart = resolveStartFromHistory(value);
        const resolvedBase =
          forcedBaseOutputFile ?? (shouldUpdateBase ? nextDerivedBase : previous.base_output_file);
        return {
          ...previous,
          input_file: value,
          base_output_file: resolvedBase,
          book_metadata: cachedBookMetadata ?? '{}',
          start_sentence: suggestedStart ?? DEFAULT_FORM_STATE.start_sentence,
        };
      });
    },
    [
      forcedBaseOutputFile,
      markUserEditedField,
      normalizePath,
      resolveStartFromHistory,
      setFormState,
      userEditedEndRef,
      userEditedInputRef,
      userEditedStartRef,
      lastAutoEndSentenceRef,
    ],
  );

  const refreshFiles = useCallback(async () => {
    if (isGeneratedSource) {
      setIsLoadingFiles(false);
      setFileOptions(null);
      return;
    }
    setIsLoadingFiles(true);
    try {
      const response = await fetchPipelineFiles();
      setFileOptions(response);
      setFileDialogError(null);
    } catch (fetchError) {
      const message =
        fetchError instanceof Error ? fetchError.message : 'Unable to load available files.';
      setFileDialogError(message);
      setFileOptions(null);
    } finally {
      setIsLoadingFiles(false);
    }
  }, [isGeneratedSource]);

  const handleDeleteEbook = useCallback(
    async (entry: PipelineFileEntry) => {
      const confirmed =
        typeof window === 'undefined'
          ? true
          : window.confirm(`Delete ${entry.name}? This action cannot be undone.`);
      if (!confirmed) {
        return;
      }

      try {
        await deletePipelineEbook(entry.path);
        setFileDialogError(null);
        setFormState((previous) => {
          if (previous.input_file !== entry.path) {
            return previous;
          }
          const derivedBase = deriveBaseOutputName(entry.name);
          const nextBase =
            forcedBaseOutputFile ??
            (previous.base_output_file === derivedBase ? '' : previous.base_output_file);
          return {
            ...previous,
            input_file: '',
            base_output_file: nextBase,
            book_metadata: '{}',
          };
        });
        prefillAppliedRef.current = null;
        await refreshFiles();
      } catch (deleteError) {
        const message =
          deleteError instanceof Error
            ? deleteError.message
            : 'Unable to delete selected ebook.';
        setFileDialogError(message);
      }
    },
    [forcedBaseOutputFile, prefillAppliedRef, refreshFiles, setFormState],
  );

  const processFileUpload = useCallback(
    async (file: File) => {
      setUploadError(null);
      setRecentUploadName(null);

      const filename = file.name || 'uploaded.epub';
      if (!filename.toLowerCase().endsWith('.epub')) {
        setUploadError('Only EPUB files can be imported.');
        return;
      }

      setIsUploadingFile(true);
      try {
        const entry = await uploadEpubFile(file);
        handleInputFileChange(entry.path);
        setRecentUploadName(entry.name);
        await refreshFiles();
      } catch (uploadFailure) {
        const message =
          uploadFailure instanceof Error
            ? uploadFailure.message
            : 'Unable to upload EPUB file.';
        setUploadError(message);
      } finally {
        setIsUploadingFile(false);
      }
    },
    [handleInputFileChange, refreshFiles],
  );

  const handleDropzoneDragOver = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      if (!isDraggingFile) {
        setIsDraggingFile(true);
      }
    },
    [isDraggingFile],
  );

  const handleDropzoneDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDraggingFile(false);
  }, []);

  const handleDropzoneDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDraggingFile(false);

      const droppedFile = event.dataTransfer?.files?.[0];
      if (droppedFile) {
        void processFileUpload(droppedFile);
      }
    },
    [processFileUpload],
  );

  useEffect(() => {
    void refreshFiles();
  }, [refreshFiles]);

  useEffect(() => {
    if (!fileOptions || fileOptions.ebooks.length === 0 || isGeneratedSource) {
      return;
    }
    setFormState((previous) => {
      if (previous.input_file && previous.input_file.trim()) {
        return previous;
      }
      const preferred =
        fileOptions.ebooks.find((entry) =>
          entry.name.trim().toLowerCase() === PREFERRED_SAMPLE_EBOOK,
        ) || fileOptions.ebooks[0];
      const nextInput = preferred.path;
      const derivedBase = deriveBaseOutputName(preferred.name || preferred.path);
      const suggestedStart = resolveStartFromHistory(nextInput);
      userEditedStartRef.current = false;
      return {
        ...previous,
        input_file: nextInput,
        base_output_file: derivedBase || previous.base_output_file || 'book-output',
        start_sentence: suggestedStart ?? DEFAULT_FORM_STATE.start_sentence,
      };
    });
  }, [fileOptions, isGeneratedSource, resolveStartFromHistory, setFormState, userEditedStartRef]);

  return {
    fileOptions,
    fileDialogError,
    isLoadingFiles,
    activeFileDialog,
    setActiveFileDialog,
    isDraggingFile,
    isUploadingFile,
    uploadError,
    recentUploadName,
    handleInputFileChange,
    refreshFiles,
    handleDeleteEbook,
    processFileUpload,
    handleDropzoneDragOver,
    handleDropzoneDragLeave,
    handleDropzoneDrop,
  };
}
