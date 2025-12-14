import { ReactNode, createContext, useCallback, useContext, useMemo, useState } from 'react';
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
}

const MyLinguistContext = createContext<MyLinguistContextValue | null>(null);

type Props = {
  children: ReactNode;
};

export function MyLinguistProvider({ children }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingOpenOptions, setPendingOpenOptions] = useState<MyLinguistOpenOptions | null>(null);

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

  const value = useMemo<MyLinguistContextValue>(() => {
    return {
      isOpen,
      open,
      close,
      toggle,
      pendingOpenOptions,
      consumePendingOpenOptions
    };
  }, [close, consumePendingOpenOptions, isOpen, open, pendingOpenOptions, toggle]);

  return <MyLinguistContext.Provider value={value}>{children}</MyLinguistContext.Provider>;
}

export function useMyLinguist(): MyLinguistContextValue {
  const context = useContext(MyLinguistContext);
  if (!context) {
    throw new Error('useMyLinguist must be used within a MyLinguistProvider');
  }
  return context;
}

