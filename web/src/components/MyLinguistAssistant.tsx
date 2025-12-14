import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { assistantLookup, fetchLlmModels } from '../api/client';
import type { AssistantChatMessage, AssistantLookupResponse, AssistantRequestContext } from '../api/dtos';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { useMyLinguist } from '../context/MyLinguistProvider';
import LanguageDropdown from './LanguageDropdown';
import styles from './MyLinguistAssistant.module.css';

type ChatMessage = AssistantChatMessage & {
  id: string;
  createdAt: number;
};

const STORAGE_KEYS = {
  inputLanguage: 'ebookTools.myLinguist.inputLanguage',
  lookupLanguage: 'ebookTools.myLinguist.lookupLanguage',
  llmModel: 'ebookTools.myLinguist.llmModel',
  systemPrompt: 'ebookTools.myLinguist.systemPrompt'
} as const;

const DEFAULT_LOOKUP_LANGUAGE = 'English';
const DEFAULT_LLM_MODEL = 'kimi-k2:1t-cloud';
const EMPTY_SENTINEL = '__EMPTY__';
const SOURCE_START = '<<<BEGIN_SOURCE_TEXT>>>';
const SOURCE_END = '<<<END_SOURCE_TEXT>>>';

function defaultLookupPrompt(inputLanguage: string, lookupLanguage: string): string {
  const resolvedInput = inputLanguage.trim() || 'the input language';
  const resolvedLookup = lookupLanguage.trim() || 'English';
  return [
    'You are MyLinguist, a fast lookup dictionary assistant.',
    `The user will provide a word, phrase, or sentence in ${resolvedInput}.`,
    `Respond in ${resolvedLookup}.`,
    `The user's text is between the markers ${SOURCE_START} and ${SOURCE_END}.`,
    'Never include those markers (or variations such as <<<, >>>, <<, >>) in your response.',
    'Be concise and helpful. Avoid filler, safety disclaimers, and meta commentary.',
    '',
    'If the input is a single word or short phrase:',
    '- Give a one-line definition.',
    '- Include a very brief etymology note (origin/root) if you know it; if unsure, omit rather than guess.',
    '- Include part of speech when clear.',
    '- Include pronunciation/reading (IPA or common reading) if you know it.',
    '- Optionally include 1 short example usage.',
    '',
    'If the input is a full sentence:',
    '- Give a brief meaning/paraphrase.',
    '- Call out any key idiom(s) or tricky segment(s) if present.',
    '',
    'Prefer a compact bullet list. Keep the whole response under ~120 words unless necessary.'
  ].join('\n');
}

function nowId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
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
  const [activeTab, setActiveTab] = useState<'chat' | 'settings' | 'prompt'>('chat');

  const [models, setModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<AssistantLookupResponse | null>(null);

  const messagesRef = useRef<HTMLDivElement | null>(null);

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
    return defaultLookupPrompt(inputLanguage, lookupLanguage);
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
        system_prompt: systemPrompt.trim() ? systemPrompt.trim() : null,
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
    resolvedPrompt
  ]);

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

  const resolvedModels = models.length ? models : llmModel ? [llmModel] : [DEFAULT_LLM_MODEL];

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
      <section className={styles.panel} aria-label="MyLinguist assistant">
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
                    <span>{message.role === 'user' ? 'You' : 'MyLinguist'}</span>
                    <span>{new Date(message.createdAt).toLocaleTimeString()}</span>
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
                      onClick={() => setSystemPrompt(defaultLookupPrompt(inputLanguage, lookupLanguage))}
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
