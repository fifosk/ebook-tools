import { useCallback, useMemo } from 'react';
import type { CSSProperties, Ref, PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../../constants/languageCodes';
import { normalizeLanguageLabel } from '../../utils/languages';
import { parseLinguistLookupResult, type LinguistLookupResult } from '../../utils/myLinguistPrompt';
import EmojiIcon from '../EmojiIcon';
import type { LinguistBubbleFloatingPlacement, LinguistBubbleState } from './types';
import { containsNonLatinLetters, renderWithNonLatinBoost } from './utils';

type MyLinguistBubbleVariant = 'docked' | 'floating';

interface MyLinguistBubbleProps {
  bubble: LinguistBubbleState;
  isPinned: boolean;
  isDocked: boolean;
  isDragging?: boolean;
  isResizing?: boolean;
  variant: MyLinguistBubbleVariant;
  bubbleRef?: Ref<HTMLDivElement>;
  floatingPlacement?: LinguistBubbleFloatingPlacement;
  floatingPosition?: { top: number; left: number } | null;
  floatingSize?: { width: number; height: number } | null;
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  onTogglePinned: () => void;
  onToggleDocked: () => void;
  onNavigatePrev: () => void;
  onNavigateNext: () => void;
  onSpeak: () => void;
  onSpeakSlow: () => void;
  onClose: () => void;
  lookupLanguageOptions: string[];
  llmModelOptions: string[];
  ttsVoiceOptions: string[];
  onLookupLanguageChange: (value: string) => void;
  onLlmModelChange: (value: string | null) => void;
  onTtsVoiceChange: (value: string | null) => void;
  onBubblePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerDown?: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerMove?: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerUp?: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerCancel?: (event: ReactPointerEvent<HTMLDivElement>) => void;
}

export function MyLinguistBubble({
  bubble,
  isPinned,
  isDocked,
  isDragging = false,
  isResizing = false,
  variant,
  bubbleRef,
  floatingPlacement,
  floatingPosition,
  floatingSize,
  canNavigatePrev,
  canNavigateNext,
  onTogglePinned,
  onToggleDocked,
  onNavigatePrev,
  onNavigateNext,
  onSpeak,
  onSpeakSlow,
  onClose,
  lookupLanguageOptions,
  llmModelOptions,
  ttsVoiceOptions,
  onLookupLanguageChange,
  onLlmModelChange,
  onTtsVoiceChange,
  onBubblePointerDown,
  onBubblePointerMove,
  onBubblePointerUp,
  onBubblePointerCancel,
  onResizeHandlePointerDown,
  onResizeHandlePointerMove,
  onResizeHandlePointerUp,
  onResizeHandlePointerCancel,
}: MyLinguistBubbleProps) {
  const className = [
    'player-panel__my-linguist-bubble',
    variant === 'docked' ? 'player-panel__my-linguist-bubble--docked' : 'player-panel__my-linguist-bubble--floating',
    bubble.status === 'loading' ? 'player-panel__my-linguist-bubble--loading' : null,
    bubble.status === 'error' ? 'player-panel__my-linguist-bubble--error' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const style =
    variant === 'floating' && floatingPosition
      ? ({
          top: `${floatingPosition.top}px`,
          left: `${floatingPosition.left}px`,
          bottom: 'auto',
          transform: floatingPlacement === 'free' ? 'none' : undefined,
          width: floatingSize ? `${floatingSize.width}px` : undefined,
          height: floatingSize ? `${floatingSize.height}px` : undefined,
        } as CSSProperties)
      : undefined;
  const resolvedLookupLanguage =
    normalizeLanguageLabel(bubble.lookupLanguage) || bubble.lookupLanguage || 'English';
  const resolvedLookupFlag = resolveLanguageFlag(resolvedLookupLanguage) ?? DEFAULT_LANGUAGE_FLAG;
  const resolvedLookupOptions = useMemo(() => {
    const seen = new Set<string>();
    const result: string[] = [];
    const append = (value: string) => {
      const normalized = normalizeLanguageLabel(value) || value.trim();
      if (!normalized) {
        return;
      }
      const key = normalized.toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      result.push(normalized);
    };
    append(resolvedLookupLanguage);
    lookupLanguageOptions.forEach(append);
    return result;
  }, [lookupLanguageOptions, resolvedLookupLanguage]);
  const formatLookupOptionLabel = useCallback((language: string) => {
    const normalized = normalizeLanguageLabel(language) || language;
    const flag = resolveLanguageFlag(language) ?? DEFAULT_LANGUAGE_FLAG;
    return `${flag} ${normalized}`;
  }, []);
  const resolvedModelValue = bubble.llmModel?.trim() ?? '';
  const resolvedModelOptions = useMemo(() => {
    const seen = new Set<string>();
    const result: string[] = [];
    const append = (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) {
        return;
      }
      const key = trimmed.toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      result.push(trimmed);
    };
    if (bubble.llmModel) {
      append(bubble.llmModel);
    }
    llmModelOptions.forEach(append);
    return result;
  }, [bubble.llmModel, llmModelOptions]);

  const resolvedVoiceValue = bubble.ttsVoice?.trim() ?? '';
  const resolvedVoiceOptions = useMemo(() => {
    const seen = new Set<string>();
    const result: string[] = [];
    const append = (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) {
        return;
      }
      const key = trimmed.toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      result.push(trimmed);
    };
    if (bubble.ttsVoice) {
      append(bubble.ttsVoice);
    }
    ttsVoiceOptions.forEach(append);
    return result;
  }, [bubble.ttsVoice, ttsVoiceOptions]);

  const formatVoiceLabel = useCallback((voice: string) => {
    // Show shorter labels for voice options
    if (voice.includes(' - ')) {
      return voice.split(' - ')[0];
    }
    if (voice.startsWith('gTTS-')) {
      return `gTTS (${voice.slice(5)})`;
    }
    // Piper voices: en_US-lessac-medium → lessac
    const piperMatch = voice.match(/^[a-z]{2}_[A-Z]{2}-(.+)-(?:high|medium|low|x_low)$/i);
    if (piperMatch) {
      return piperMatch[1];
    }
    return voice;
  }, []);

  // Parse JSON response if available
  const parsedResult = useMemo((): LinguistLookupResult | null => {
    if (bubble.status !== 'ready' || !bubble.answer) {
      return null;
    }
    return parseLinguistLookupResult(bubble.answer);
  }, [bubble.status, bubble.answer]);

  // Render structured content from parsed JSON
  const renderStructuredContent = useCallback((result: LinguistLookupResult): ReactNode => {
    const items: ReactNode[] = [];

    // Definition (always shown)
    items.push(
      <div key="definition" className="player-panel__my-linguist-structured-definition">
        {renderWithNonLatinBoost(result.definition, 'player-panel__my-linguist-bubble-non-latin')}
      </div>
    );

    // Part of speech & pronunciation
    if (result.part_of_speech || result.pronunciation) {
      const parts: string[] = [];
      if (result.part_of_speech) {
        parts.push(result.part_of_speech);
      }
      if (result.pronunciation) {
        parts.push(`[${result.pronunciation}]`);
      }
      items.push(
        <div key="pos" className="player-panel__my-linguist-structured-meta">
          • {parts.join(' ')}
        </div>
      );
    }

    // Etymology
    if (result.etymology) {
      items.push(
        <div key="etymology" className="player-panel__my-linguist-structured-etymology">
          ⟶ {renderWithNonLatinBoost(result.etymology, 'player-panel__my-linguist-bubble-non-latin')}
        </div>
      );
    }

    // Example
    if (result.example) {
      items.push(
        <div key="example" className="player-panel__my-linguist-structured-example">
          <div className="player-panel__my-linguist-structured-example-text">
            „ {renderWithNonLatinBoost(result.example, 'player-panel__my-linguist-bubble-non-latin')}
            {result.example_transliteration ? (
              <span className="player-panel__my-linguist-structured-example-translit">
                {' '}({result.example_transliteration})
              </span>
            ) : null}
          </div>
          {result.example_translation ? (
            <div className="player-panel__my-linguist-structured-example-translation">
              → {result.example_translation}
            </div>
          ) : null}
        </div>
      );
    }

    // Idioms (for sentences)
    if (result.idioms && result.idioms.length > 0) {
      items.push(
        <div key="idioms" className="player-panel__my-linguist-structured-section">
          <div className="player-panel__my-linguist-structured-section-title">Idioms:</div>
          {result.idioms.map((idiom, idx) => (
            <div key={idx} className="player-panel__my-linguist-structured-list-item">
              • {renderWithNonLatinBoost(idiom, 'player-panel__my-linguist-bubble-non-latin')}
            </div>
          ))}
        </div>
      );
    }

    // Related languages
    if (result.related_languages && result.related_languages.length > 0) {
      items.push(
        <div key="related" className="player-panel__my-linguist-structured-section">
          <div className="player-panel__my-linguist-structured-section-title">Related:</div>
          {result.related_languages.map((lang, idx) => (
            <div key={idx} className="player-panel__my-linguist-structured-list-item">
              • {lang.language}:{' '}
              <span className="player-panel__my-linguist-structured-related-word">
                {renderWithNonLatinBoost(lang.word, 'player-panel__my-linguist-bubble-non-latin')}
              </span>
              {lang.transliteration ? ` (${lang.transliteration})` : null}
            </div>
          ))}
        </div>
      );
    }

    return <div className="player-panel__my-linguist-structured-content">{items}</div>;
  }, []);

  return (
    <div
      ref={bubbleRef}
      className={className}
      data-placement={variant === 'floating' ? floatingPlacement : undefined}
      data-dragging={isDragging ? 'true' : undefined}
      data-resizing={isResizing ? 'true' : undefined}
      style={style}
      role="dialog"
      aria-label="MyLinguist lookup"
    >
      <div
        className="player-panel__my-linguist-bubble-header"
        onPointerDown={onBubblePointerDown}
        onPointerMove={onBubblePointerMove}
        onPointerUp={onBubblePointerUp}
        onPointerCancel={onBubblePointerCancel}
      >
        <div className="player-panel__my-linguist-bubble-header-left">
          <span className="player-panel__my-linguist-bubble-title">MyLinguist</span>
          <div className="player-panel__my-linguist-bubble-selectors">
            <label className="player-panel__my-linguist-bubble-select">
              <span className="visually-hidden">Lookup language</span>
              <span className="player-panel__my-linguist-bubble-flag" aria-hidden="true">
                <EmojiIcon emoji={resolvedLookupFlag} />
              </span>
              <select
                value={resolvedLookupLanguage}
                onChange={(event) => onLookupLanguageChange(event.target.value)}
                aria-label="Lookup language"
              >
                {resolvedLookupOptions.map((language) => (
                  <option key={language} value={language}>
                    {formatLookupOptionLabel(language)}
                  </option>
                ))}
              </select>
            </label>
            <label className="player-panel__my-linguist-bubble-select player-panel__my-linguist-bubble-select--model">
              <span className="visually-hidden">LLM model</span>
              <select
                value={resolvedModelValue}
                onChange={(event) =>
                  onLlmModelChange(event.target.value.trim() ? event.target.value : null)
                }
                aria-label="LLM model"
              >
                <option value="">Auto</option>
                {resolvedModelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className="player-panel__my-linguist-bubble-actions">
          <button
            type="button"
            className="player-panel__my-linguist-bubble-pin"
            onClick={onTogglePinned}
            aria-label={isPinned ? 'Unpin MyLinguist bubble' : 'Pin MyLinguist bubble'}
            aria-pressed={isPinned}
            title={isPinned ? 'Unpin bubble' : 'Pin bubble'}
          >
            <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
              {isPinned ? (
                <>
                  <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                  <path d="M12 13v8" />
                </>
              ) : (
                <>
                  <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                  <path d="M12 13v8" />
                  <path d="M4 4l16 16" />
                </>
              )}
            </svg>
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-dock"
            onClick={onToggleDocked}
            aria-label={isDocked ? 'Undock MyLinguist bubble' : 'Dock MyLinguist bubble'}
            aria-pressed={isDocked}
            title={isDocked ? 'Float bubble' : 'Dock bubble'}
          >
            <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
              <path d="M4 19h16" />
              <path d="M12 5v9" />
              <path d="m8 11 4 4 4-4" />
            </svg>
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-nav"
            onClick={onNavigatePrev}
            aria-label="Previous word"
            title="Previous word (Alt+←)"
            disabled={!canNavigatePrev}
          >
            ←
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-nav"
            onClick={onNavigateNext}
            aria-label="Next word"
            title="Next word (Alt+→)"
            disabled={!canNavigateNext}
          >
            →
          </button>
          {resolvedVoiceOptions.length > 0 ? (
            <label className="player-panel__my-linguist-bubble-select player-panel__my-linguist-bubble-select--voice">
              <span className="visually-hidden">TTS voice</span>
              <span className="player-panel__my-linguist-bubble-voice-icon" aria-hidden="true">
                🔊
              </span>
              <select
                value={resolvedVoiceValue}
                onChange={(event) =>
                  onTtsVoiceChange(event.target.value.trim() ? event.target.value : null)
                }
                aria-label="TTS voice"
              >
                <option value="">Auto</option>
                {resolvedVoiceOptions.map((voice) => (
                  <option key={voice} value={voice}>
                    {formatVoiceLabel(voice)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button
            type="button"
            className="player-panel__my-linguist-bubble-speak"
            onClick={onSpeak}
            aria-label="Speak selection aloud"
            title="Speak selection aloud"
            disabled={bubble.ttsStatus === 'loading'}
          >
            {bubble.ttsStatus === 'loading' ? '…' : '▶'}
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-speak"
            onClick={onSpeakSlow}
            aria-label="Speak selection slowly"
            title="Speak slowly (0.5×)"
            disabled={bubble.ttsStatus === 'loading'}
          >
            {bubble.ttsStatus === 'loading' ? '…' : '🐢'}
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-close"
            onClick={onClose}
            aria-label="Close MyLinguist lookup"
          >
            ✕
          </button>
        </div>
      </div>
      <div
        className={[
          'player-panel__my-linguist-bubble-query',
          containsNonLatinLetters(bubble.fullQuery)
            ? 'player-panel__my-linguist-bubble-query--non-latin'
            : null,
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {bubble.query}
      </div>
      <div className="player-panel__my-linguist-bubble-body">
        {parsedResult
          ? renderStructuredContent(parsedResult)
          : renderWithNonLatinBoost(
              bubble.answer,
              'player-panel__my-linguist-bubble-non-latin',
            )}
      </div>
      {variant === 'floating' ? (
        <div
          className="player-panel__my-linguist-bubble-resize"
          onPointerDown={onResizeHandlePointerDown}
          onPointerMove={onResizeHandlePointerMove}
          onPointerUp={onResizeHandlePointerUp}
          onPointerCancel={onResizeHandlePointerCancel}
          role="presentation"
          aria-hidden="true"
        />
      ) : null}
    </div>
  );
}
