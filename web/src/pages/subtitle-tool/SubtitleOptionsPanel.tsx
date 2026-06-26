import type { SubtitleOutputFormat } from './subtitleToolTypes';
import SubtitleLanguageOptionsSection from './SubtitleLanguageOptionsSection';
import {
  DEFAULT_ASS_EMPHASIS,
  MAX_ASS_EMPHASIS,
  MAX_ASS_FONT_SIZE,
  MIN_ASS_EMPHASIS,
  MIN_ASS_FONT_SIZE
} from './subtitleToolConfig';
import styles from '../SubtitleToolPage.module.css';

type SubtitleOptionsPanelProps = {
  inputLanguage: string;
  targetLanguage: string;
  sortedLanguageOptions: string[];
  selectedModel: string;
  transliterationModel: string;
  availableModels: string[];
  modelsLoading: boolean;
  modelsError: string | null;
  translationProvider: string;
  transliterationMode: string;
  enableTransliteration: boolean;
  enableHighlight: boolean;
  generateAudioBook: boolean;
  showOriginal: boolean;
  mirrorToSourceDir: boolean;
  outputFormat: SubtitleOutputFormat;
  assFontSize: number | '';
  assEmphasis: number | '';
  startTime: string;
  endTime: string;
  sourceDirectory: string;
  onInputLanguageChange: (value: string) => void;
  onTargetLanguageChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onTranslationProviderChange: (value: string) => void;
  onTransliterationModeChange: (value: string) => void;
  onTransliterationModelChange: (value: string) => void;
  onEnableTransliterationChange: (value: boolean) => void;
  onEnableHighlightChange: (value: boolean) => void;
  onGenerateAudioBookChange: (value: boolean) => void;
  onShowOriginalChange: (value: boolean) => void;
  onMirrorToSourceDirChange: (value: boolean) => void;
  onOutputFormatChange: (value: SubtitleOutputFormat) => void;
  onAssFontSizeChange: (value: number | '') => void;
  onAssEmphasisChange: (value: number | '') => void;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
};

export default function SubtitleOptionsPanel({
  inputLanguage,
  targetLanguage,
  sortedLanguageOptions,
  selectedModel,
  transliterationModel,
  availableModels,
  modelsLoading,
  modelsError,
  translationProvider,
  transliterationMode,
  enableTransliteration,
  enableHighlight,
  generateAudioBook,
  showOriginal,
  mirrorToSourceDir,
  outputFormat,
  assFontSize,
  assEmphasis,
  startTime,
  endTime,
  sourceDirectory,
  onInputLanguageChange,
  onTargetLanguageChange,
  onModelChange,
  onTranslationProviderChange,
  onTransliterationModeChange,
  onTransliterationModelChange,
  onEnableTransliterationChange,
  onEnableHighlightChange,
  onGenerateAudioBookChange,
  onShowOriginalChange,
  onMirrorToSourceDirChange,
  onOutputFormatChange,
  onAssFontSizeChange,
  onAssEmphasisChange,
  onStartTimeChange,
  onEndTimeChange
}: SubtitleOptionsPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Subtitle options</h2>
          <p className={styles.cardHint}>Configure translation, highlighting, output format, and batching.</p>
        </div>
      </div>
      <SubtitleLanguageOptionsSection
        inputLanguage={inputLanguage}
        targetLanguage={targetLanguage}
        sortedLanguageOptions={sortedLanguageOptions}
        selectedModel={selectedModel}
        transliterationModel={transliterationModel}
        availableModels={availableModels}
        modelsLoading={modelsLoading}
        modelsError={modelsError}
        translationProvider={translationProvider}
        transliterationMode={transliterationMode}
        enableTransliteration={enableTransliteration}
        enableHighlight={enableHighlight}
        generateAudioBook={generateAudioBook}
        showOriginal={showOriginal}
        mirrorToSourceDir={mirrorToSourceDir}
        sourceDirectory={sourceDirectory}
        onInputLanguageChange={onInputLanguageChange}
        onTargetLanguageChange={onTargetLanguageChange}
        onModelChange={onModelChange}
        onTranslationProviderChange={onTranslationProviderChange}
        onTransliterationModeChange={onTransliterationModeChange}
        onTransliterationModelChange={onTransliterationModelChange}
        onEnableTransliterationChange={onEnableTransliterationChange}
        onEnableHighlightChange={onEnableHighlightChange}
        onGenerateAudioBookChange={onGenerateAudioBookChange}
        onShowOriginalChange={onShowOriginalChange}
        onMirrorToSourceDirChange={onMirrorToSourceDirChange}
      />
      <fieldset>
        <legend>Output & timing</legend>
        <div className="field-inline">
          <label>
            Subtitle format
            <select
              value={outputFormat}
              onChange={(event) => onOutputFormatChange(event.target.value === 'ass' ? 'ass' : 'srt')}
            >
              <option value="srt">SRT (SubRip)</option>
              <option value="ass">ASS (Advanced SubStation Alpha)</option>
            </select>
          </label>
          <label>
            ASS base font size
            <input
              type="number"
              min={MIN_ASS_FONT_SIZE}
              max={MAX_ASS_FONT_SIZE}
              value={typeof assFontSize === 'number' ? assFontSize : ''}
              onChange={(event) => {
                const raw = event.target.value;
                if (!raw.trim()) {
                  onAssFontSizeChange('');
                  return;
                }
                const parsed = Number(raw);
                if (Number.isNaN(parsed)) {
                  return;
                }
                const clamped = Math.max(
                  MIN_ASS_FONT_SIZE,
                  Math.min(MAX_ASS_FONT_SIZE, Math.round(parsed))
                );
                onAssFontSizeChange(clamped);
              }}
              disabled={outputFormat !== 'ass'}
            />
            <small>Used only for ASS exports ({MIN_ASS_FONT_SIZE}-{MAX_ASS_FONT_SIZE}).</small>
          </label>
          <label>
            ASS emphasis scale
            <input
              type="number"
              step={0.1}
              min={MIN_ASS_EMPHASIS}
              max={MAX_ASS_EMPHASIS}
              value={typeof assEmphasis === 'number' ? assEmphasis : ''}
              onChange={(event) => {
                const raw = event.target.value;
                if (!raw.trim()) {
                  onAssEmphasisChange('');
                  return;
                }
                const parsed = Number(raw);
                if (Number.isNaN(parsed)) {
                  return;
                }
                const clamped = Math.max(
                  MIN_ASS_EMPHASIS,
                  Math.min(MAX_ASS_EMPHASIS, Math.round(parsed * 100) / 100)
                );
                onAssEmphasisChange(clamped);
              }}
              disabled={outputFormat !== 'ass'}
            />
            <small>Translation scale (default {DEFAULT_ASS_EMPHASIS.toFixed(2)}×).</small>
          </label>
          <label>
            Start time (MM:SS or HH:MM:SS)
            <input
              type="text"
              value={startTime}
              onChange={(event) => onStartTimeChange(event.target.value)}
              placeholder="00:00"
              inputMode="numeric"
            />
          </label>
          <label>
            End time (leave blank for full file)
            <input
              type="text"
              value={endTime}
              onChange={(event) => onEndTimeChange(event.target.value)}
              placeholder="+05:00"
              inputMode="numeric"
            />
          </label>
        </div>
      </fieldset>
    </section>
  );
}
