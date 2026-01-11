import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { assistantLookup, fetchLlmModels, fetchVoiceInventory } from '../api/client';
import type {
  AssistantChatMessage,
  AssistantLookupResponse,
  AssistantRequestContext,
  MacOSVoice,
  VoiceInventoryResponse
} from '../api/dtos';
import { VOICE_OPTIONS } from '../constants/menuOptions';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { useMyLinguist } from '../context/MyLinguistProvider';
import { speakText } from '../utils/ttsPlayback';
import { resolveLanguageCode } from '../constants/languageCodes';
import { buildMyLinguistSystemPrompt } from '../utils/myLinguistPrompt';
import LanguageDropdown from './LanguageDropdown';
import styles from './MyLinguistAssistant.module.css';

type ChatMessage = AssistantChatMessage & {
  id: string;
  createdAt: number;
};

type VoiceOption = {
  value: string;
  label: string;
  description?: string;
};

const STORAGE_KEYS = {
  inputLanguage: 'ebookTools.myLinguist.inputLanguage',
  lookupLanguage: 'ebookTools.myLinguist.lookupLanguage',
  llmModel: 'ebookTools.myLinguist.llmModel',
  systemPrompt: 'ebookTools.myLinguist.systemPrompt',
  questionVoice: 'ebookTools.myLinguist.questionVoice',
  replyVoice: 'ebookTools.myLinguist.replyVoice',
  panelWidth: 'ebookTools.myLinguist.panelWidth',
  panelHeight: 'ebookTools.myLinguist.panelHeight'
} as const;

const DEFAULT_LOOKUP_LANGUAGE = 'English';
const DEFAULT_LLM_MODEL = 'ollama_cloud:gpt-oss:120b-cloud';
const EMPTY_SENTINEL = '__EMPTY__';

function nowId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function capitalize(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${capitalize(voice.gender)}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const segments: string[] = [voice.lang];
  if (voice.gender) {
    segments.push(capitalize(voice.gender));
  }
  if (voice.quality) {
    segments.push(voice.quality);
  }
  const meta = segments.length > 0 ? ` (${segments.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

function buildVoiceOptionsForLanguage(
  voiceInventory: VoiceInventoryResponse | null,
  languageCode: string | null
): VoiceOption[] {
  const baseOptions: VoiceOption[] = VOICE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label,
    description: option.description
  }));

  if (!voiceInventory || !languageCode) {
    return baseOptions;
  }

  const extras: VoiceOption[] = [];
  const normalizedCode = languageCode.toLowerCase();

  const gttsMatches = voiceInventory.gtts.filter((entry) => {
    const entryCode = entry.code.toLowerCase();
    if (entryCode === normalizedCode) {
      return true;
    }
    return entryCode.startsWith(`${normalizedCode}-`) || entryCode.startsWith(`${normalizedCode}_`);
  });
  const seenGtts = new Set<string>();
  for (const entry of gttsMatches) {
    const shortCode = entry.code.split(/[-_]/)[0].toLowerCase();
    if (!shortCode || seenGtts.has(shortCode)) {
      continue;
    }
    seenGtts.add(shortCode);
    const identifier = `gTTS-${shortCode}`;
    extras.push({ value: identifier, label: `gTTS (${entry.name})`, description: 'gTTS voice' });
  }

  const macVoices = voiceInventory.macos.filter((voice) => {
    const voiceLang = voice.lang.toLowerCase();
    return (
      voiceLang === normalizedCode ||
      voiceLang.startsWith(`${normalizedCode}-`) ||
      voiceLang.startsWith(`${normalizedCode}_`)
    );
  });
  macVoices
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((voice) => {
      extras.push({
        value: formatMacOSVoiceIdentifier(voice),
        label: formatMacOSVoiceLabel(voice),
        description: 'macOS system voice'
      });
    });

  const merged = new Map<string, VoiceOption>();
  for (const option of [...baseOptions, ...extras]) {
    if (!option.value) {
      continue;
    }
    if (!merged.has(option.value)) {
      merged.set(option.value, option);
    }
  }
  return Array.from(merged.values());
}

function loadStored(key: string, { allowEmpty = false }: { allowEmpty?: boolean } = {}): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) {
      return null;
    }
    if (raw === EMPTY_SENTINEL) {
      return '';
    }
    if (!raw.trim()) {
      return allowEmpty ? '' : null;
    }
    return raw;
  } catch {
    return null;
  }
}

function storeValue(key: string, value: string, { allowEmpty = false }: { allowEmpty?: boolean } = {}): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    const next = allowEmpty && !value ? EMPTY_SENTINEL : value;
    window.localStorage.setItem(key, next);
  } catch {
    return;
  }
}

function loadStoredNumber(key: string): number | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function storeNumber(key: string, value: number): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    if (!Number.isFinite(value) || value <= 0) {
      return;
    }
    window.localStorage.setItem(key, String(Math.round(value)));
  } catch {
    return;
  }
}

type PanelSize = { width: number; height: number };
type ResizeDirection = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';

export default function MyLinguistAssistant() {
  const { inputLanguage: globalInputLanguage } = useLanguagePreferences();
  const { isOpen, toggle, close, consumePendingOpenOptions } = useMyLinguist();

  const initialModelPreference = useMemo(() => {
    const stored = loadStored(STORAGE_KEYS.llmModel, { allowEmpty: true });
    return { value: stored ?? '', hasPreference: stored !== null };
  }, []);

  const [inputLanguage, setInputLanguage] = useState(
    () => loadStored(STORAGE_KEYS.inputLanguage) ?? globalInputLanguage
  );
  const [lookupLanguage, setLookupLanguage] = useState(
    () => loadStored(STORAGE_KEYS.lookupLanguage) ?? DEFAULT_LOOKUP_LANGUAGE
  );
  const [llmModel, setLlmModel] = useState(() => initialModelPreference.value);
  const [hasModelPreference, setHasModelPreference] = useState(() => initialModelPreference.hasPreference);
  const [systemPrompt, setSystemPrompt] = useState(
    () => loadStored(STORAGE_KEYS.systemPrompt, { allowEmpty: true }) ?? ''
  );
  const [questionVoice, setQuestionVoice] = useState(() => loadStored(STORAGE_KEYS.questionVoice, { allowEmpty: true }) ?? '');
  const [replyVoice, setReplyVoice] = useState(() => loadStored(STORAGE_KEYS.replyVoice, { allowEmpty: true }) ?? '');
  const [activeTab, setActiveTab] = useState<'chat' | 'settings' | 'prompt'>('chat');
  const [panelSize, setPanelSize] = useState<PanelSize>(() => ({
    width: loadStoredNumber(STORAGE_KEYS.panelWidth) ?? 420,
    height: loadStoredNumber(STORAGE_KEYS.panelHeight) ?? 520
  }));
  const [viewport, setViewport] = useState<{ width: number; height: number }>(() => ({
    width: typeof window === 'undefined' ? 1280 : window.innerWidth,
    height: typeof window === 'undefined' ? 800 : window.innerHeight
  }));

  const [models, setModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [voicesError, setVoicesError] = useState<string | null>(null);

  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<AssistantLookupResponse | null>(null);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [ttsError, setTtsError] = useState<string | null>(null);

  const messagesRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const resizeSessionRef = useRef<{
    dir: ResizeDirection;
    pointerId: number;
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
  } | null>(null);

  useEffect(() => {
    storeValue(STORAGE_KEYS.inputLanguage, inputLanguage);
  }, [inputLanguage]);

  useEffect(() => {
    storeValue(STORAGE_KEYS.lookupLanguage, lookupLanguage);
  }, [lookupLanguage]);

  useEffect(() => {
    storeValue(STORAGE_KEYS.llmModel, llmModel, { allowEmpty: true });
  }, [llmModel]);

  useEffect(() => {
    storeValue(STORAGE_KEYS.systemPrompt, systemPrompt, { allowEmpty: true });
  }, [systemPrompt]);

  useEffect(() => {
    storeValue(STORAGE_KEYS.questionVoice, questionVoice, { allowEmpty: true });
  }, [questionVoice]);

  useEffect(() => {
    storeValue(STORAGE_KEYS.replyVoice, replyVoice, { allowEmpty: true });
  }, [replyVoice]);

  useEffect(() => {
    storeNumber(STORAGE_KEYS.panelWidth, panelSize.width);
    storeNumber(STORAGE_KEYS.panelHeight, panelSize.height);
  }, [panelSize.height, panelSize.width]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handle = () => {
      setViewport({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener('resize', handle);
    return () => window.removeEventListener('resize', handle);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const pending = consumePendingOpenOptions();
    if (!pending) {
      return;
    }
    if (pending.inputLanguage) {
      setInputLanguage(pending.inputLanguage);
    }
    if (pending.lookupLanguage) {
      setLookupLanguage(pending.lookupLanguage);
    }
    if (typeof pending.llmModel !== 'undefined') {
      setLlmModel(pending.llmModel ?? '');
      setHasModelPreference(true);
    }
    if (typeof pending.systemPrompt !== 'undefined') {
      setSystemPrompt(pending.systemPrompt ?? '');
    }
    if (pending.query) {
      setDraft(pending.query);
    }
    setActiveTab('chat');
  }, [consumePendingOpenOptions, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    if (modelsLoading || models.length) {
      return;
    }
    setModelsLoading(true);
    setModelsError(null);
    void fetchLlmModels()
      .then((loaded) => {
        setModels(loaded);
        if (!hasModelPreference && !llmModel && loaded.includes(DEFAULT_LLM_MODEL)) {
          setLlmModel(DEFAULT_LLM_MODEL);
        } else if (!hasModelPreference && !llmModel && loaded.length > 0) {
          setLlmModel(loaded[0]);
        }
      })
      .catch((error) => {
        setModelsError(error instanceof Error ? error.message : 'Unable to load models.');
      })
      .finally(() => {
        setModelsLoading(false);
      });
  }, [hasModelPreference, isOpen, llmModel, models.length, modelsLoading]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    if (voicesLoading || voiceInventory) {
      return;
    }
    setVoicesLoading(true);
    setVoicesError(null);
    void fetchVoiceInventory()
      .then((inventory) => {
        setVoiceInventory(inventory);
      })
      .catch((error) => {
        setVoicesError(error instanceof Error ? error.message : 'Unable to load voices.');
      })
      .finally(() => {
        setVoicesLoading(false);
      });
  }, [isOpen, voiceInventory, voicesLoading]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const el = messagesRef.current;
    if (!el) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [isOpen, messages]);

  const resolvedPrompt = useMemo(() => {
    const trimmed = systemPrompt.trim();
    if (trimmed) {
      return trimmed;
    }
    return buildMyLinguistSystemPrompt(inputLanguage, lookupLanguage);
  }, [inputLanguage, lookupLanguage, systemPrompt]);

  const appendMessage = useCallback((role: AssistantChatMessage['role'], content: string) => {
    setMessages((previous) => [
      ...previous,
      {
        id: nowId(role),
        role,
        content,
        createdAt: Date.now()
      }
    ]);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setLastResponse(null);
    setSendError(null);
    setActiveTab('chat');
  }, []);

  const buildContext = useCallback((): AssistantRequestContext => {
    const page = typeof window !== 'undefined' ? window.location.pathname : null;
    return {
      source: 'my_linguist',
      page,
      metadata: {
        ui: 'floating_chat'
      }
    };
  }, []);

  const handleSend = useCallback(async () => {
    const query = draft.trim();
    if (!query || isSending) {
      return;
    }
    setSendError(null);
    setIsSending(true);

    appendMessage('user', query);
    setDraft('');

    const history = messages.slice(-10).map(({ role, content }) => ({ role, content }));

    try {
      const response = await assistantLookup({
        query,
        input_language: inputLanguage.trim() || globalInputLanguage,
        lookup_language: lookupLanguage.trim() || DEFAULT_LOOKUP_LANGUAGE,
        llm_model: llmModel.trim() ? llmModel.trim() : null,
        system_prompt: resolvedPrompt,
        history,
        context: buildContext()
      });
      setLastResponse(response);
      appendMessage('assistant', response.answer);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to reach assistant.';
      setSendError(message);
      appendMessage('assistant', `Error: ${message}`);
    } finally {
      setIsSending(false);
    }
  }, [
    appendMessage,
    buildContext,
    draft,
    globalInputLanguage,
    inputLanguage,
    isSending,
    llmModel,
    lookupLanguage,
    messages,
    systemPrompt
  ]);

  const handleSpeakMessage = useCallback(
    async (message: ChatMessage, playbackRate?: number) => {
      const text = message.content.trim();
      if (!text) {
        return;
      }
      setTtsError(null);
      setSpeakingMessageId(message.id);
      try {
        const isUser = message.role === 'user';
        const language = isUser
          ? inputLanguage.trim() || globalInputLanguage
          : lookupLanguage.trim() || DEFAULT_LOOKUP_LANGUAGE;
        const voice = isUser ? questionVoice.trim() : replyVoice.trim();
        await speakText({
          text,
          language,
          voice: voice ? voice : null,
          playbackRate: typeof playbackRate === 'number' ? playbackRate : null,
        });
      } catch (error) {
        setTtsError(error instanceof Error ? error.message : 'Unable to speak text.');
      } finally {
        setSpeakingMessageId((current) => (current === message.id ? null : current));
      }
    },
    [globalInputLanguage, inputLanguage, lookupLanguage, questionVoice, replyVoice]
  );

  const clampPanelSize = useCallback(
    (size: PanelSize): PanelSize => {
      const maxWidth = Math.min(520, Math.max(320, viewport.width - 36));
      const maxHeight = Math.min(720, Math.max(360, viewport.height - 120));
      return {
        width: Math.max(320, Math.min(maxWidth, size.width)),
        height: Math.max(360, Math.min(maxHeight, size.height)),
      };
    },
    [viewport.height, viewport.width]
  );

  useEffect(() => {
    setPanelSize((previous) => {
      const clamped = clampPanelSize(previous);
      if (clamped.width === previous.width && clamped.height === previous.height) {
        return previous;
      }
      return clamped;
    });
  }, [clampPanelSize]);

  const beginResize = useCallback(
    (event: ReactPointerEvent, dir: ResizeDirection) => {
      if (!panelRef.current) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      resizeSessionRef.current = {
        dir,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startWidth: panelSize.width,
        startHeight: panelSize.height,
      };
      try {
        panelRef.current.setPointerCapture(event.pointerId);
      } catch {
        // ignore
      }
    },
    [panelSize.height, panelSize.width]
  );

  const applyResize = useCallback(
    (event: ReactPointerEvent) => {
      const session = resizeSessionRef.current;
      if (!session || session.pointerId !== event.pointerId) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const dx = event.clientX - session.startX;
      const dy = event.clientY - session.startY;
      const affectsWidth = session.dir.includes('e') || session.dir.includes('w');
      const affectsHeight = session.dir.includes('n') || session.dir.includes('s');

      const nextWidth = affectsWidth
        ? session.startWidth + (session.dir.includes('w') ? -dx : dx)
        : session.startWidth;
      const nextHeight = affectsHeight
        ? session.startHeight + (session.dir.includes('n') ? -dy : dy)
        : session.startHeight;

      setPanelSize(clampPanelSize({ width: nextWidth, height: nextHeight }));
    },
    [clampPanelSize]
  );

  const endResize = useCallback((event: ReactPointerEvent) => {
    const session = resizeSessionRef.current;
    if (!session || session.pointerId !== event.pointerId) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    resizeSessionRef.current = null;
    try {
      panelRef.current?.releasePointerCapture(event.pointerId);
    } catch {
      // ignore
    }
  }, []);

  const resolvedModels = models.length ? models : llmModel ? [llmModel] : [DEFAULT_LLM_MODEL];
  const inputLanguageCode = resolveLanguageCode(inputLanguage) ?? resolveLanguageCode(globalInputLanguage);
  const lookupLanguageCode = resolveLanguageCode(lookupLanguage) ?? resolveLanguageCode(DEFAULT_LOOKUP_LANGUAGE);
  const questionVoiceOptions = useMemo(
    () => buildVoiceOptionsForLanguage(voiceInventory, inputLanguageCode ?? null),
    [globalInputLanguage, inputLanguageCode, voiceInventory]
  );
  const replyVoiceOptions = useMemo(
    () => buildVoiceOptionsForLanguage(voiceInventory, lookupLanguageCode ?? null),
    [lookupLanguageCode, voiceInventory]
  );

  if (!isOpen) {
    return (
      <div className={styles.launcher}>
        <button type="button" className={styles.launcherButton} onClick={toggle} aria-label="Open MyLinguist assistant">
          <span className={styles.launcherGlyph} aria-hidden="true">
            <svg viewBox="0 0 64 64" role="img" focusable="false">
              <path d="M32 12 6 23l26 11 26-11-26-11Z" />
              <path d="M14 29v11c0 2 8 10 18 10s18-8 18-10V29L32 38 14 29Z" opacity="0.95" />
              <path
                d="M58 24v16c0 1.1-.9 2-2 2s-2-.9-2-2V25.7l-22 9.2-26-11"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.9"
              />
            </svg>
          </span>
          <span className={styles.launcherLabel}>MyLinguist</span>
        </button>
      </div>
    );
  }

  return (
    <>
      <div className={styles.launcher}>
        <button type="button" className={styles.launcherButton} onClick={toggle} aria-label="Toggle MyLinguist assistant">
          <span className={styles.launcherGlyph} aria-hidden="true">
            <svg viewBox="0 0 64 64" role="img" focusable="false">
              <path d="M32 12 6 23l26 11 26-11-26-11Z" />
              <path d="M14 29v11c0 2 8 10 18 10s18-8 18-10V29L32 38 14 29Z" opacity="0.95" />
              <path
                d="M58 24v16c0 1.1-.9 2-2 2s-2-.9-2-2V25.7l-22 9.2-26-11"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.9"
              />
            </svg>
          </span>
          <span className={styles.launcherLabel}>MyLinguist</span>
        </button>
      </div>
      <section
        className={styles.panel}
        aria-label="MyLinguist assistant"
        ref={panelRef as unknown as React.RefObject<HTMLElement>}
        style={{ width: panelSize.width, height: panelSize.height }}
        onPointerMove={applyResize}
        onPointerUp={endResize}
        onPointerCancel={endResize}
      >
        <div className={styles.resizeHandles} aria-hidden="true">
          <div className={[styles.resizeHandle, styles.resizeHandleNw].join(' ')} onPointerDown={(e) => beginResize(e, 'nw')} />
          <div className={[styles.resizeHandle, styles.resizeHandleNe].join(' ')} onPointerDown={(e) => beginResize(e, 'ne')} />
          <div className={[styles.resizeHandle, styles.resizeHandleSw].join(' ')} onPointerDown={(e) => beginResize(e, 'sw')} />
          <div className={[styles.resizeHandle, styles.resizeHandleSe].join(' ')} onPointerDown={(e) => beginResize(e, 'se')} />
          <div className={[styles.resizeHandle, styles.resizeHandleN].join(' ')} onPointerDown={(e) => beginResize(e, 'n')} />
          <div className={[styles.resizeHandle, styles.resizeHandleS].join(' ')} onPointerDown={(e) => beginResize(e, 's')} />
          <div className={[styles.resizeHandle, styles.resizeHandleE].join(' ')} onPointerDown={(e) => beginResize(e, 'e')} />
          <div className={[styles.resizeHandle, styles.resizeHandleW].join(' ')} onPointerDown={(e) => beginResize(e, 'w')} />
        </div>
        <header className={styles.header}>
          <div className={styles.titleBlock}>
            <div className={styles.title}>MyLinguist</div>
            <div className={styles.subtitle}>
              Lookup dictionary · {lastResponse?.model ? `Model: ${lastResponse.model}` : 'Ready'}
            </div>
          </div>
          <div className={styles.headerActions}>
            <button type="button" className={styles.iconButton} onClick={clearChat}>
              Clear
            </button>
            <button type="button" className={styles.iconButton} onClick={close} aria-label="Close MyLinguist">
              ✕
            </button>
          </div>
        </header>
        <div className={styles.body}>
          <div className={styles.tabs} role="tablist" aria-label="MyLinguist tabs">
            <button
              type="button"
              role="tab"
              className={[styles.tabButton, activeTab === 'chat' ? styles.tabButtonActive : ''].join(' ')}
              aria-selected={activeTab === 'chat'}
              aria-controls="my-linguist-tabpanel-chat"
              onClick={() => setActiveTab('chat')}
            >
              Chat
            </button>
            <button
              type="button"
              role="tab"
              className={[styles.tabButton, activeTab === 'settings' ? styles.tabButtonActive : ''].join(' ')}
              aria-selected={activeTab === 'settings'}
              aria-controls="my-linguist-tabpanel-settings"
              onClick={() => setActiveTab('settings')}
            >
              Settings
            </button>
            <button
              type="button"
              role="tab"
              className={[styles.tabButton, activeTab === 'prompt' ? styles.tabButtonActive : ''].join(' ')}
              aria-selected={activeTab === 'prompt'}
              aria-controls="my-linguist-tabpanel-prompt"
              onClick={() => setActiveTab('prompt')}
            >
              Prompt
            </button>
          </div>

          <div className={styles.tabPanel} role="tabpanel" id="my-linguist-tabpanel-chat" hidden={activeTab !== 'chat'}>
            <div className={styles.messages} ref={messagesRef}>
              {messages.length === 0 ? (
                <div className={styles.hint}>
                  Type a word/phrase/sentence and get a quick definition in {lookupLanguage || DEFAULT_LOOKUP_LANGUAGE}.
                </div>
              ) : null}
              {messages.map((message) => (
                <div key={message.id} className={styles.message}>
                  <div className={styles.messageMeta}>
                    <div className={styles.messageMetaLeft}>
                      <span>{message.role === 'user' ? 'You' : 'MyLinguist'}</span>
                      <span>{new Date(message.createdAt).toLocaleTimeString()}</span>
                    </div>
                    <div className={styles.messageMetaRight}>
                      <button
                        type="button"
                        className={styles.messageSpeakButton}
                        onClick={() => void handleSpeakMessage(message)}
                        disabled={!message.content.trim() || speakingMessageId === message.id}
                        aria-label={message.role === 'user' ? 'Speak your message aloud' : 'Speak MyLinguist reply aloud'}
                        title={message.role === 'user' ? 'Speak message' : 'Speak reply'}
                      >
                        <span aria-hidden="true">{speakingMessageId === message.id ? '…' : '🔊'}</span>
                      </button>
                      <button
                        type="button"
                        className={styles.messageSpeakButton}
                        onClick={() => void handleSpeakMessage(message, 0.5)}
                        disabled={!message.content.trim() || speakingMessageId === message.id}
                        aria-label={
                          message.role === 'user'
                            ? 'Speak your message slowly'
                            : 'Speak MyLinguist reply slowly'
                        }
                        title={message.role === 'user' ? 'Speak slowly (0.5×)' : 'Speak reply slowly (0.5×)'}
                      >
                        <span aria-hidden="true">{speakingMessageId === message.id ? '…' : '🐢'}</span>
                      </button>
                    </div>
                  </div>
                  <div
                    className={[
                      styles.bubble,
                      message.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant
                    ].join(' ')}
                  >
                    {message.content}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            className={styles.tabPanel}
            role="tabpanel"
            id="my-linguist-tabpanel-settings"
            hidden={activeTab !== 'settings'}
          >
            <div className={styles.settingsPanel}>
              <div className={styles.settingsGrid}>
                <LanguageDropdown
                  label="Input language"
                  value={inputLanguage}
                  onChange={setInputLanguage}
                  preferredLanguages={[globalInputLanguage, inputLanguage]}
                  placeholder={globalInputLanguage}
                  helperText={null}
                />
                <LanguageDropdown
                  label="Lookup language"
                  value={lookupLanguage}
                  onChange={setLookupLanguage}
                  preferredLanguages={[lookupLanguage, DEFAULT_LOOKUP_LANGUAGE]}
                  placeholder={DEFAULT_LOOKUP_LANGUAGE}
                  helperText={null}
                />
                <label htmlFor="my-linguist-model">
                  LLM model
                  <select
                    id="my-linguist-model"
                    value={llmModel}
                    onChange={(event) => {
                      setHasModelPreference(true);
                      setLlmModel(event.target.value);
                    }}
                    disabled={modelsLoading && models.length === 0}
                  >
                    <option value="">Use server default</option>
                    {resolvedModels.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                  <small className="form-help-text">
                    {modelsLoading
                      ? 'Loading available models…'
                      : modelsError
                        ? `Unable to load models (${modelsError}).`
                        : null}
                  </small>
                </label>
                <label htmlFor="my-linguist-mode">
                  Response mode
                  <input id="my-linguist-mode" value="Lookup dictionary" readOnly />
                </label>
                <label htmlFor="my-linguist-question-voice">
                  Question voice
                  <select
                    id="my-linguist-question-voice"
                    value={questionVoice}
                    onChange={(event) => setQuestionVoice(event.target.value)}
                    disabled={voicesLoading && !voiceInventory}
                  >
                    <option value="">Use server default</option>
                    {questionVoiceOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <small className="form-help-text">
                    {voicesLoading
                      ? 'Loading voices…'
                      : voicesError
                        ? `Unable to load voices (${voicesError}).`
                        : null}
                  </small>
                </label>
                <label htmlFor="my-linguist-reply-voice">
                  Reply voice
                  <select
                    id="my-linguist-reply-voice"
                    value={replyVoice}
                    onChange={(event) => setReplyVoice(event.target.value)}
                    disabled={voicesLoading && !voiceInventory}
                  >
                    <option value="">Use server default</option>
                    {replyVoiceOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          </div>

          <div className={styles.tabPanel} role="tabpanel" id="my-linguist-tabpanel-prompt" hidden={activeTab !== 'prompt'}>
            <div className={styles.settingsPanel}>
              <div className={styles.promptEditor}>
                <div className={styles.promptEditorHeader}>
                  <span>System prompt override</span>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      className={styles.iconButton}
                      onClick={() => setSystemPrompt(buildMyLinguistSystemPrompt(inputLanguage, lookupLanguage))}
                    >
                      Reset
                    </button>
                    <button type="button" className={styles.iconButton} onClick={() => setSystemPrompt('')}>
                      Use default
                    </button>
                  </div>
                </div>
                <textarea
                  value={resolvedPrompt}
                  onChange={(event) => setSystemPrompt(event.target.value)}
                  rows={10}
                  spellCheck={false}
                />
              </div>
            </div>
          </div>
        </div>
        {activeTab === 'chat' ? (
          <footer className={styles.composer}>
            {sendError ? <div className={styles.error}>{sendError}</div> : null}
            {ttsError ? <div className={styles.error}>{ttsError}</div> : null}
            <div className={styles.composerRow}>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask for a definition, meaning, usage…"
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault();
                    void handleSend();
                  }
                }}
                disabled={isSending}
              />
              <button
                type="button"
                className={styles.sendButton}
                onClick={() => void handleSend()}
                disabled={!draft.trim() || isSending}
              >
                {isSending ? 'Sending…' : 'Send'}
              </button>
            </div>
            <div className={styles.hint}>Tip: press Ctrl/⌘ + Enter to send.</div>
          </footer>
        ) : null}
      </section>
    </>
  );
}
