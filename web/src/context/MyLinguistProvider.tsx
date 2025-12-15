import { ReactNode, createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { AssistantRequestContext } from '../api/dtos';

export type MyLinguistOpenOptions = {
  query?: string;
  inputLanguage?: string;
  lookupLanguage?: string;
  llmModel?: string | null;
  systemPrompt?: string | null;
  context?: AssistantRequestContext | null;
  autoSend?: boolean;
};

export interface MyLinguistContextValue {
  isOpen: boolean;
  open: (options?: MyLinguistOpenOptions) => void;
  close: () => void;
  toggle: () => void;
  pendingOpenOptions: MyLinguistOpenOptions | null;
  consumePendingOpenOptions: () => MyLinguistOpenOptions | null;
  baseFontScalePercent: number;
  setBaseFontScalePercent: (value: number) => void;
}

const MyLinguistContext = createContext<MyLinguistContextValue | null>(null);

type Props = {
  children: ReactNode;
};

const BASE_FONT_SCALE_STORAGE_KEY = 'ebookTools.myLinguist.baseFontScalePercent';
const BASE_FONT_SCALE_DEFAULT = 120;
const BASE_FONT_SCALE_MIN = 80;
const BASE_FONT_SCALE_MAX = 160;

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return BASE_FONT_SCALE_DEFAULT;
  }
  return Math.min(Math.max(Math.round(value), BASE_FONT_SCALE_MIN), BASE_FONT_SCALE_MAX);
}

export function MyLinguistProvider({ children }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingOpenOptions, setPendingOpenOptions] = useState<MyLinguistOpenOptions | null>(null);
  const [baseFontScalePercent, setBaseFontScalePercentState] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return BASE_FONT_SCALE_DEFAULT;
    }
    const stored = window.localStorage.getItem(BASE_FONT_SCALE_STORAGE_KEY);
    if (!stored) {
      return BASE_FONT_SCALE_DEFAULT;
    }
    const parsed = Number.parseFloat(stored);
    return clampPercent(parsed);
  });

  const open = useCallback((options: MyLinguistOpenOptions = {}) => {
    setPendingOpenOptions(options);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((previous) => !previous);
  }, []);

  const consumePendingOpenOptions = useCallback(() => {
    const current = pendingOpenOptions;
    if (current) {
      setPendingOpenOptions(null);
    }
    return current;
  }, [pendingOpenOptions]);

  const setBaseFontScalePercent = useCallback((value: number) => {
    setBaseFontScalePercentState(clampPercent(value));
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(BASE_FONT_SCALE_STORAGE_KEY, String(baseFontScalePercent));
    document.documentElement.style.setProperty('--my-linguist-font-scale', String(baseFontScalePercent / 100));
  }, [baseFontScalePercent]);

  const value = useMemo<MyLinguistContextValue>(() => {
    return {
      isOpen,
      open,
      close,
      toggle,
      pendingOpenOptions,
      consumePendingOpenOptions,
      baseFontScalePercent,
      setBaseFontScalePercent,
    };
  }, [baseFontScalePercent, close, consumePendingOpenOptions, isOpen, open, pendingOpenOptions, setBaseFontScalePercent, toggle]);

  return <MyLinguistContext.Provider value={value}>{children}</MyLinguistContext.Provider>;
}

export function useMyLinguist(): MyLinguistContextValue {
  const context = useContext(MyLinguistContext);
  if (!context) {
    throw new Error('useMyLinguist must be used within a MyLinguistProvider');
  }
  return context;
}
