import { ReactNode, createContext, useCallback, useContext, useMemo, useState } from 'react';

export type MyPainterSentenceContext = {
  jobId: string | null;
  rangeFragment: string | null;
  sentenceNumber: number | null;
  sentenceText: string | null;
  prompt: string | null;
  negativePrompt: string | null;
  imagePath: string | null;
};

export type MyPainterOpenOptions = {
  followPlayer?: boolean;
  sentence?: MyPainterSentenceContext | null;
};

export interface MyPainterContextValue {
  isOpen: boolean;
  open: (options?: MyPainterOpenOptions) => void;
  close: () => void;
  toggle: () => void;
  pendingOpenOptions: MyPainterOpenOptions | null;
  consumePendingOpenOptions: () => MyPainterOpenOptions | null;
  playerSentence: MyPainterSentenceContext | null;
  setPlayerSentence: (value: MyPainterSentenceContext | null) => void;
  imageRefreshToken: number;
  bumpImageRefreshToken: () => void;
}

const MyPainterContext = createContext<MyPainterContextValue | null>(null);

type Props = {
  children: ReactNode;
};

export function MyPainterProvider({ children }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingOpenOptions, setPendingOpenOptions] = useState<MyPainterOpenOptions | null>(null);
  const [playerSentence, setPlayerSentence] = useState<MyPainterSentenceContext | null>(null);
  const [imageRefreshToken, setImageRefreshToken] = useState(0);

  const open = useCallback((options: MyPainterOpenOptions = {}) => {
    setPendingOpenOptions(options);
    setIsOpen(true);
  }, []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => {
    setIsOpen((previous) => {
      if (previous) {
        return false;
      }
      setPendingOpenOptions({});
      return true;
    });
  }, []);
  const consumePendingOpenOptions = useCallback(() => {
    const current = pendingOpenOptions;
    if (current) {
      setPendingOpenOptions(null);
    }
    return current;
  }, [pendingOpenOptions]);
  const bumpImageRefreshToken = useCallback(() => setImageRefreshToken((value) => value + 1), []);

  const value = useMemo<MyPainterContextValue>(() => {
    return {
      isOpen,
      open,
      close,
      toggle,
      pendingOpenOptions,
      consumePendingOpenOptions,
      playerSentence,
      setPlayerSentence,
      imageRefreshToken,
      bumpImageRefreshToken,
    };
  }, [
    bumpImageRefreshToken,
    close,
    consumePendingOpenOptions,
    imageRefreshToken,
    isOpen,
    open,
    pendingOpenOptions,
    playerSentence,
    toggle,
  ]);

  return <MyPainterContext.Provider value={value}>{children}</MyPainterContext.Provider>;
}

export function useMyPainter(): MyPainterContextValue {
  const context = useContext(MyPainterContext);
  if (!context) {
    throw new Error('useMyPainter must be used within a MyPainterProvider');
  }
  return context;
}
