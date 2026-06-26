import { fireEvent, render, screen } from '@testing-library/react';
import type { FormEvent } from 'react';
import { describe, expect, it, vi } from 'vitest';
import SubtitleToolTabContent from '../subtitle-tool/SubtitleToolTabContent';
import type { SubtitleToolTab } from '../subtitle-tool/subtitleToolTypes';

function renderTab(activeTab: SubtitleToolTab) {
  const handleSubmit = vi.fn((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
  });
  const props = {
    activeTab,
    formId: 'subtitle-submit-form',
    onSubmit: handleSubmit,
    sourcePanelProps: {
      sourceMode: 'existing' as const,
      sourceDirectory: '/Volumes/Data/Video/Subtitles',
      sourceCount: 0,
      sortedSources: [],
      selectedSource: '',
      isLoadingSources: false,
      sourceError: null,
      sourceMessage: null,
      deletingSourcePath: null,
      isAssSelection: false,
      onSourceModeChange: vi.fn(),
      onSelectSource: vi.fn(),
      onRefreshSources: vi.fn(),
      onDeleteSource: vi.fn(),
      onUploadFileChange: vi.fn()
    },
    optionsPanelProps: {
      inputLanguage: 'English',
      targetLanguage: 'Turkish',
      sortedLanguageOptions: ['English', 'Turkish'],
      selectedModel: 'googletrans',
      transliterationModel: '',
      availableModels: ['googletrans'],
      modelsLoading: false,
      modelsError: null,
      translationProvider: 'googletrans',
      transliterationMode: 'none',
      enableTransliteration: false,
      enableHighlight: true,
      generateAudioBook: false,
      showOriginal: true,
      mirrorToSourceDir: false,
      outputFormat: 'srt' as const,
      assFontSize: 48,
      assEmphasis: 1.4,
      startTime: '',
      endTime: '',
      sourceDirectory: '/Volumes/Data/Video/Subtitles',
      onInputLanguageChange: vi.fn(),
      onTargetLanguageChange: vi.fn(),
      onModelChange: vi.fn(),
      onTranslationProviderChange: vi.fn(),
      onTransliterationModeChange: vi.fn(),
      onTransliterationModelChange: vi.fn(),
      onEnableTransliterationChange: vi.fn(),
      onEnableHighlightChange: vi.fn(),
      onGenerateAudioBookChange: vi.fn(),
      onShowOriginalChange: vi.fn(),
      onMirrorToSourceDirChange: vi.fn(),
      onOutputFormatChange: vi.fn(),
      onAssFontSizeChange: vi.fn(),
      onAssEmphasisChange: vi.fn(),
      onStartTimeChange: vi.fn(),
      onEndTimeChange: vi.fn()
    },
    tuningPanelProps: {
      workerCount: 4,
      batchSize: 80,
      translationBatchSize: 12,
      onWorkerCountChange: vi.fn(),
      onBatchSizeChange: vi.fn(),
      onTranslationBatchSizeChange: vi.fn()
    },
    metadataPanelProps: {
      metadataSourceName: '',
      metadataLookupSourceName: '',
      metadataPreview: null,
      metadataLoading: false,
      metadataError: null,
      mediaMetadataDraft: null,
      onLookupSourceNameChange: vi.fn(),
      onLookupMetadata: vi.fn(),
      onClearMetadata: vi.fn(),
      onUpdateMediaMetadataDraft: vi.fn(),
      onUpdateMediaMetadataSection: vi.fn()
    },
    jobsPanelProps: {
      jobs: [],
      jobResults: {},
      onSelectJob: vi.fn()
    }
  };
  const view = render(<SubtitleToolTabContent {...props} />);
  return { ...view, handleSubmit };
}

describe('SubtitleToolTabContent', () => {
  it.each([
    ['subtitles', 'Subtitle selection'],
    ['options', 'Subtitle options'],
    ['tuning', 'Performance tuning'],
    ['metadata', 'Metadata loader'],
    ['jobs', 'Subtitle jobs']
  ] as const)('renders the %s tab panel', (activeTab, heading) => {
    renderTab(activeTab);

    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
  });

  it('keeps source, option, tuning, and metadata tabs inside the shared submit form', () => {
    const { container, handleSubmit } = renderTab('subtitles');
    const form = container.querySelector<HTMLFormElement>('#subtitle-submit-form');

    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });
});
