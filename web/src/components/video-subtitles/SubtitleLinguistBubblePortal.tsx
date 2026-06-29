import { createPortal } from 'react-dom';
import { MyLinguistBubble } from '../interactive-text/MyLinguistBubble';
import type { LinguistBubbleState } from '../interactive-text/types';
import type { UseLinguistBubbleLayoutResult } from '../interactive-text/useLinguistBubbleLayout';
import type { UseLinguistBubbleLookupResult } from '../interactive-text/useLinguistBubbleLookup';

type SubtitleLinguistBubblePortalProps = {
  bubble: LinguistBubbleState | null;
  linguistEnabled: boolean;
  layout: UseLinguistBubbleLayoutResult;
  lookup: UseLinguistBubbleLookupResult;
  dockedContainer: HTMLElement | null;
  lookupLanguageOptions: string[];
  llmModelOptions: string[];
  ttsVoiceOptions: string[];
  onLookupLanguageChange: (value: string) => void;
  onLlmModelChange: (value: string | null) => void;
  onTtsVoiceChange: (value: string | null) => void;
  onClose: () => void;
};

const noop = () => {};

export function SubtitleLinguistBubblePortal({
  bubble,
  linguistEnabled,
  layout,
  lookup,
  dockedContainer,
  lookupLanguageOptions,
  llmModelOptions,
  ttsVoiceOptions,
  onLookupLanguageChange,
  onLlmModelChange,
  onTtsVoiceChange,
  onClose,
}: SubtitleLinguistBubblePortalProps) {
  if (!linguistEnabled || !bubble) {
    return null;
  }

  const bubbleNode = (
    <MyLinguistBubble
      bubble={bubble}
      isPinned={layout.bubblePinned}
      isDocked={layout.bubbleDocked}
      isDragging={layout.bubbleDragging}
      isResizing={layout.bubbleResizing}
      variant={layout.bubbleDocked ? 'docked' : 'floating'}
      bubbleRef={layout.bubbleRef}
      floatingPlacement={layout.floatingPlacement}
      floatingPosition={layout.floatingPosition}
      floatingSize={layout.floatingSize}
      canNavigatePrev={false}
      canNavigateNext={false}
      onTogglePinned={layout.onTogglePinned}
      onToggleDocked={layout.onToggleDocked}
      onNavigatePrev={noop}
      onNavigateNext={noop}
      onSpeak={lookup.onSpeak}
      onSpeakSlow={lookup.onSpeakSlow}
      onPlayFromNarration={undefined}
      onClose={onClose}
      lookupLanguageOptions={lookupLanguageOptions}
      onLookupLanguageChange={onLookupLanguageChange}
      llmModelOptions={llmModelOptions}
      onLlmModelChange={onLlmModelChange}
      ttsVoiceOptions={ttsVoiceOptions}
      onTtsVoiceChange={onTtsVoiceChange}
      onBubblePointerDown={layout.onBubblePointerDown}
      onBubblePointerMove={layout.onBubblePointerMove}
      onBubblePointerUp={layout.onBubblePointerUp}
      onBubblePointerCancel={layout.onBubblePointerCancel}
      onResizeHandlePointerDown={layout.onResizeHandlePointerDown}
      onResizeHandlePointerMove={layout.onResizeHandlePointerMove}
      onResizeHandlePointerUp={layout.onResizeHandlePointerUp}
      onResizeHandlePointerCancel={layout.onResizeHandlePointerCancel}
    />
  );

  if (layout.bubbleDocked && dockedContainer) {
    return createPortal(bubbleNode, dockedContainer);
  }

  return bubbleNode;
}
