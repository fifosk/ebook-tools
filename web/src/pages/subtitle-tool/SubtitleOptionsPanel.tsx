import LanguageSelect from '../../components/LanguageSelect';
import type { SubtitleOutputFormat } from './subtitleToolTypes';
import {
  DEFAULT_ASS_EMPHASIS,
  DEFAULT_LLM_MODEL,
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
  availableModels: string[];
  modelsLoading: boolean;
  modelsError: string | null;
  enableTransliteration: boolean;
  enableHighlight: boolean;
  generateAudioBook: boolean;
  showOriginal: boolean;
  mirrorToSourceDir: boolean;
  outputFormat: SubtitleOutputFormat;
  assFontSize: number | '';
  assEmphasis: number | '';
  workerCount: number | '';
  batchSize: number | '';
  startTime: string;
  endTime: string;
  sourceDirectory: string;
  onInputLanguageChange: (value: string) => void;
  onTargetLanguageChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onEnableTransliterationChange: (value: boolean) => void;
  onEnableHighlightChange: (value: boolean) => void;
  onGenerateAudioBookChange: (value: boolean) => void;
  onShowOriginalChange: (value: boolean) => void;
  onMirrorToSourceDirChange: (value: boolean) => void;
  onOutputFormatChange: (value: SubtitleOutputFormat) => void;
  onAssFontSizeChange: (value: number | '') => void;
  onAssEmphasisChange: (value: number | '') => void;
  onWorkerCountChange: (value: number | '') => void;
  onBatchSizeChange: (value: number | '') => void;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
};

export default function SubtitleOptionsPanel({
  inputLanguage,
  targetLanguage,
  sortedLanguageOptions,
  selectedModel,
  availableModels,
  modelsLoading,
  modelsError,
  enableTransliteration,
  enableHighlight,
  generateAudioBook,
  showOriginal,
  mirrorToSourceDir,
  outputFormat,
  assFontSize,
  assEmphasis,
  workerCount,
  batchSize,
  startTime,
  endTime,
  sourceDirectory,
  onInputLanguageChange,
  onTargetLanguageChange,
  onModelChange,
  onEnableTransliterationChange,
  onEnableHighlightChange,
  onGenerateAudioBookChange,
  onShowOriginalChange,
  onMirrorToSourceDirChange,
  onOutputFormatChange,
  onAssFontSizeChange,
  onAssEmphasisChange,
  onWorkerCountChange,
  onBatchSizeChange,
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
      <fieldset>
        <legend>Languages</legend>
        <div className="field">
          <label className="field-label" htmlFor="subtitle-input-language">Original language</label>
          <LanguageSelect
            id="subtitle-input-language"
            value={inputLanguage}
            options={sortedLanguageOptions}
            onChange={onInputLanguageChange}
          />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="subtitle-target-language">Translation language</label>
          <LanguageSelect
            id="subtitle-target-language"
            value={targetLanguage}
            options={sortedLanguageOptions}
            onChange={onTargetLanguageChange}
          />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="subtitle-llm-model">LLM model (optional)</label>
          <select
            id="subtitle-llm-model"
            value={selectedModel}
            onChange={(event) => onModelChange(event.target.value)}
            disabled={modelsLoading && availableModels.length === 0 && selectedModel.trim().length === 0}
          >
            <option value="">Use server default</option>
            {Array.from(
              new Set([
                ...(selectedModel.trim() ? [selectedModel.trim()] : []),
                ...(availableModels.length ? availableModels : [DEFAULT_LLM_MODEL])
              ])
            ).map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
          <small className="field-note">
            {modelsLoading
              ? 'Loading models from Ollama…'
              : modelsError
              ? `Unable to load models (${modelsError}).`
              : 'Leave blank to use the default server model.'}
          </small>
        </div>
        <div className="field-inline">
          <label>
            <input
              type="checkbox"
              checked={enableTransliteration}
              onChange={(event) => onEnableTransliterationChange(event.target.checked)}
            />
            Enable transliteration for non-Latin scripts
          </label>
          <label>
            <input
              type="checkbox"
              checked={enableHighlight}
              onChange={(event) => onEnableHighlightChange(event.target.checked)}
            />
            Dynamic word highlighting
          </label>
          <label>
            <input
              type="checkbox"
              checked={generateAudioBook}
              onChange={(event) => onGenerateAudioBookChange(event.target.checked)}
            />
            Generate Interactive Player audio book
          </label>
          <label>
            <input
              type="checkbox"
              checked={showOriginal}
              onChange={(event) => onShowOriginalChange(event.target.checked)}
            />
            Show original language part
          </label>
          <label>
            <input
              type="checkbox"
              checked={mirrorToSourceDir}
              onChange={(event) => onMirrorToSourceDirChange(event.target.checked)}
            />
            Write batches to <code>{sourceDirectory}</code>
          </label>
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
            Worker threads
            <input
              type="number"
              min={1}
              max={32}
              value={workerCount}
              onChange={(event) => {
                const raw = event.target.value;
                if (!raw.trim()) {
                  onWorkerCountChange('');
                  return;
                }
                const parsed = Number(raw);
                if (Number.isNaN(parsed)) {
                  return;
                }
                onWorkerCountChange(Math.min(Math.max(1, parsed), 32));
              }}
            />
          </label>
          <label>
            Batch size
            <input
              type="number"
              min={1}
              max={500}
              value={batchSize}
              onChange={(event) => {
                const raw = event.target.value;
                if (!raw.trim()) {
                  onBatchSizeChange('');
                  return;
                }
                const parsed = Number(raw);
                if (Number.isNaN(parsed)) {
                  return;
                }
                onBatchSizeChange(Math.min(Math.max(1, parsed), 500));
              }}
            />
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
