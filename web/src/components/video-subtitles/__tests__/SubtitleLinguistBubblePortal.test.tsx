import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { MutableRefObject, PointerEvent as ReactPointerEvent } from 'react';
import type { LinguistBubbleState } from '../../interactive-text/types';
import type { UseLinguistBubbleLayoutResult } from '../../interactive-text/useLinguistBubbleLayout';
import type { UseLinguistBubbleLookupResult } from '../../interactive-text/useLinguistBubbleLookup';
import { SubtitleLinguistBubblePortal } from '../SubtitleLinguistBubblePortal';

type MockBubbleProps = {
  bubble: LinguistBubbleState;
  isDocked: boolean;
  isPinned: boolean;
  variant: 'docked' | 'floating';
  lookupLanguageOptions: string[];
  llmModelOptions: string[];
  ttsVoiceOptions: string[];
  onSpeak: () => void;
  onSpeakSlow: () => void;
  onClose: () => void;
  onTogglePinned: () => void;
  onToggleDocked: () => void;
  onLookupLanguageChange: (value: string) => void;
  onLlmModelChange: (value: string | null) => void;
  onTtsVoiceChange: (value: string | null) => void;
};

vi.mock('../../interactive-text/MyLinguistBubble', () => ({
  MyLinguistBubble: ({
    bubble,
    isDocked,
    isPinned,
    variant,
    lookupLanguageOptions,
    llmModelOptions,
    ttsVoiceOptions,
    onSpeak,
    onSpeakSlow,
    onClose,
    onTogglePinned,
    onToggleDocked,
    onLookupLanguageChange,
    onLlmModelChange,
    onTtsVoiceChange,
  }: MockBubbleProps) => (
    <div
      data-testid="mock-linguist-bubble"
      data-docked={String(isDocked)}
      data-pinned={String(isPinned)}
      data-variant={variant}
    >
      <span>{bubble.query}</span>
      <span>{lookupLanguageOptions.join(',')}</span>
      <span>{llmModelOptions.join(',')}</span>
      <span>{ttsVoiceOptions.join(',')}</span>
      <button type="button" onClick={onSpeak}>
        speak
      </button>
      <button type="button" onClick={onSpeakSlow}>
        speak slow
      </button>
      <button type="button" onClick={onTogglePinned}>
        pin
      </button>
      <button type="button" onClick={onToggleDocked}>
        dock
      </button>
      <button type="button" onClick={() => onLookupLanguageChange('German')}>
        lookup language
      </button>
      <button type="button" onClick={() => onLlmModelChange('gpt-test')}>
        llm
      </button>
      <button type="button" onClick={() => onTtsVoiceChange('voice-test')}>
        voice
      </button>
      <button type="button" onClick={onClose}>
        close
      </button>
    </div>
  ),
}));

const noopPointer = () => {};

function bubble(overrides: Partial<LinguistBubbleState> = {}): LinguistBubbleState {
  return {
    query: 'merhaba',
    fullQuery: 'merhaba',
    status: 'ready',
    answer: 'hello',
    lookupLanguage: 'English',
    llmModel: null,
    ttsLanguage: 'Turkish',
    ttsVoice: null,
    ttsStatus: 'idle',
    navigation: null,
    ...overrides,
  };
}

function layout(
  overrides: Partial<UseLinguistBubbleLayoutResult> = {},
): UseLinguistBubbleLayoutResult {
  return {
    bubbleRef: { current: null } as MutableRefObject<HTMLDivElement | null>,
    bubblePinned: false,
    bubbleDocked: false,
    bubbleDragging: false,
    bubbleResizing: false,
    floatingPlacement: 'above',
    floatingPosition: null,
    floatingSize: null,
    onTogglePinned: vi.fn(),
    onToggleDocked: vi.fn(),
    onBubblePointerDown: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onBubblePointerMove: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onBubblePointerUp: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onBubblePointerCancel: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onResizeHandlePointerDown: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onResizeHandlePointerMove: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onResizeHandlePointerUp: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    onResizeHandlePointerCancel: noopPointer as (event: ReactPointerEvent<HTMLDivElement>) => void,
    requestPositionUpdate: vi.fn(),
    applyOpenLayout: vi.fn(),
    resetLayout: vi.fn(),
    ...overrides,
  };
}

function lookup(
  overrides: Partial<UseLinguistBubbleLookupResult> = {},
): UseLinguistBubbleLookupResult {
  return {
    openLinguistBubbleForRect: vi.fn(),
    onSpeak: vi.fn(),
    onSpeakSlow: vi.fn(),
    resetBubbleState: vi.fn(),
    ...overrides,
  };
}

function renderPortal({
  bubbleState = bubble(),
  dockedContainer = null,
  layoutState = layout(),
  lookupState = lookup(),
  linguistEnabled = true,
}: {
  bubbleState?: LinguistBubbleState | null;
  dockedContainer?: HTMLElement | null;
  layoutState?: UseLinguistBubbleLayoutResult;
  lookupState?: UseLinguistBubbleLookupResult;
  linguistEnabled?: boolean;
} = {}) {
  const handlers = {
    onLookupLanguageChange: vi.fn(),
    onLlmModelChange: vi.fn(),
    onTtsVoiceChange: vi.fn(),
    onClose: vi.fn(),
  };

  const view = render(
    <SubtitleLinguistBubblePortal
      bubble={bubbleState}
      linguistEnabled={linguistEnabled}
      layout={layoutState}
      lookup={lookupState}
      dockedContainer={dockedContainer}
      lookupLanguageOptions={['English', 'German']}
      llmModelOptions={['gpt-test']}
      ttsVoiceOptions={['voice-test']}
      {...handlers}
    />,
  );

  return { ...view, handlers, layoutState, lookupState };
}

describe('SubtitleLinguistBubblePortal', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('does not render when the linguist bubble is disabled or closed', () => {
    const { rerender } = renderPortal({ linguistEnabled: false });

    expect(screen.queryByTestId('mock-linguist-bubble')).not.toBeInTheDocument();

    rerender(
      <SubtitleLinguistBubblePortal
        bubble={null}
        linguistEnabled
        layout={layout()}
        lookup={lookup()}
        dockedContainer={null}
        lookupLanguageOptions={[]}
        llmModelOptions={[]}
        ttsVoiceOptions={[]}
        onLookupLanguageChange={vi.fn()}
        onLlmModelChange={vi.fn()}
        onTtsVoiceChange={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByTestId('mock-linguist-bubble')).not.toBeInTheDocument();
  });

  it('renders a floating bubble and forwards lookup controls', () => {
    const layoutState = layout({ bubblePinned: true });
    const lookupState = lookup();
    const { handlers } = renderPortal({ layoutState, lookupState });
    const rendered = screen.getByTestId('mock-linguist-bubble');

    expect(rendered).toHaveAttribute('data-variant', 'floating');
    expect(rendered).toHaveAttribute('data-docked', 'false');
    expect(rendered).toHaveAttribute('data-pinned', 'true');
    expect(rendered).toHaveTextContent('merhaba');

    fireEvent.click(screen.getByRole('button', { name: 'speak' }));
    fireEvent.click(screen.getByRole('button', { name: 'speak slow' }));
    fireEvent.click(screen.getByRole('button', { name: 'pin' }));
    fireEvent.click(screen.getByRole('button', { name: 'dock' }));
    fireEvent.click(screen.getByRole('button', { name: 'lookup language' }));
    fireEvent.click(screen.getByRole('button', { name: 'llm' }));
    fireEvent.click(screen.getByRole('button', { name: 'voice' }));
    fireEvent.click(screen.getByRole('button', { name: 'close' }));

    expect(lookupState.onSpeak).toHaveBeenCalledOnce();
    expect(lookupState.onSpeakSlow).toHaveBeenCalledOnce();
    expect(layoutState.onTogglePinned).toHaveBeenCalledOnce();
    expect(layoutState.onToggleDocked).toHaveBeenCalledOnce();
    expect(handlers.onLookupLanguageChange).toHaveBeenCalledWith('German');
    expect(handlers.onLlmModelChange).toHaveBeenCalledWith('gpt-test');
    expect(handlers.onTtsVoiceChange).toHaveBeenCalledWith('voice-test');
    expect(handlers.onClose).toHaveBeenCalledOnce();
  });

  it('portals a docked bubble into the provided container', () => {
    const dockedContainer = document.createElement('section');
    document.body.appendChild(dockedContainer);

    const { container } = renderPortal({
      dockedContainer,
      layoutState: layout({ bubbleDocked: true }),
    });

    expect(container.querySelector('[data-testid="mock-linguist-bubble"]')).toBeNull();
    expect(within(dockedContainer).getByTestId('mock-linguist-bubble')).toHaveAttribute(
      'data-variant',
      'docked',
    );
  });
});
