import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem
} from '../../utils/browserStorage';
import { VIDEO_DUB_STORAGE_KEYS } from './videoDubbingConfig';

type SelectionState = {
  baseDir: string;
  setBaseDir: Dispatch<SetStateAction<string>>;
  selectedVideoPath: string | null;
  setSelectedVideoPath: Dispatch<SetStateAction<string | null>>;
  selectedVideoPathRef: MutableRefObject<string | null>;
  selectedSubtitlePath: string | null;
  setSelectedSubtitlePath: Dispatch<SetStateAction<string | null>>;
  selectedSubtitlePathRef: MutableRefObject<string | null>;
  selectedVideoDiscoveryTemplateState: Record<string, unknown> | null;
  setSelectedVideoDiscoveryTemplateState: Dispatch<SetStateAction<Record<string, unknown> | null>>;
  clearSelectedVideoDiscoveryTemplate: () => void;
};

function readStoredText(key: string): string {
  return getLocalStorageItem(key)?.trim() ?? '';
}

function readStoredPath(key: string): string | null {
  const stored = readStoredText(key);
  return stored.length > 0 ? stored : null;
}

function normalizeOptionalText(value: string | null): string | null {
  const trimmed = value?.trim() ?? '';
  return trimmed.length > 0 ? trimmed : null;
}

function persistOptionalText(key: string, value: string | null): void {
  const normalized = normalizeOptionalText(value);
  if (normalized) {
    setLocalStorageItem(key, normalized);
  } else {
    removeLocalStorageItem(key);
  }
}

export function useVideoDubbingSelectionState(): SelectionState {
  const [baseDir, setBaseDirState] = useState(() => readStoredText(VIDEO_DUB_STORAGE_KEYS.baseDir));
  const [selectedVideoPath, setSelectedVideoPathState] = useState<string | null>(() =>
    readStoredPath(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath)
  );
  const [selectedSubtitlePath, setSelectedSubtitlePathState] = useState<string | null>(() =>
    readStoredPath(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath)
  );
  const [selectedVideoDiscoveryTemplateState, setSelectedVideoDiscoveryTemplateState] =
    useState<Record<string, unknown> | null>(null);
  const selectedVideoPathRef = useRef<string | null>(selectedVideoPath);
  const selectedSubtitlePathRef = useRef<string | null>(selectedSubtitlePath);

  const setBaseDir = useCallback<Dispatch<SetStateAction<string>>>((nextValue) => {
    setBaseDirState((current) => {
      const resolved = typeof nextValue === 'function' ? nextValue(current) : nextValue;
      return resolved.trim();
    });
  }, []);

  const setSelectedVideoPath = useCallback<Dispatch<SetStateAction<string | null>>>((nextValue) => {
    setSelectedVideoPathState((current) => {
      const resolved = typeof nextValue === 'function' ? nextValue(current) : nextValue;
      return normalizeOptionalText(resolved);
    });
  }, []);

  const setSelectedSubtitlePath = useCallback<Dispatch<SetStateAction<string | null>>>((nextValue) => {
    setSelectedSubtitlePathState((current) => {
      const resolved = typeof nextValue === 'function' ? nextValue(current) : nextValue;
      return normalizeOptionalText(resolved);
    });
  }, []);

  const clearSelectedVideoDiscoveryTemplate = useCallback(() => {
    setSelectedVideoDiscoveryTemplateState(null);
  }, []);

  useEffect(() => {
    persistOptionalText(VIDEO_DUB_STORAGE_KEYS.baseDir, baseDir);
  }, [baseDir]);

  useEffect(() => {
    selectedVideoPathRef.current = selectedVideoPath;
    persistOptionalText(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath, selectedVideoPath);
  }, [selectedVideoPath]);

  useEffect(() => {
    selectedSubtitlePathRef.current = selectedSubtitlePath;
    persistOptionalText(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath, selectedSubtitlePath);
  }, [selectedSubtitlePath]);

  return {
    baseDir,
    setBaseDir,
    selectedVideoPath,
    setSelectedVideoPath,
    selectedVideoPathRef,
    selectedSubtitlePath,
    setSelectedSubtitlePath,
    selectedSubtitlePathRef,
    selectedVideoDiscoveryTemplateState,
    setSelectedVideoDiscoveryTemplateState,
    clearSelectedVideoDiscoveryTemplate
  };
}
