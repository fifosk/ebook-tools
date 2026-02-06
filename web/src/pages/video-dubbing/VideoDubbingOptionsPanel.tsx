import LanguageSelect from '../../components/LanguageSelect';
import { DEFAULT_LLM_MODEL, RESOLUTION_OPTIONS } from './videoDubbingConfig';
import styles from '../VideoDubbingPage.module.css';

const GOOGLE_TRANSLATION_PROVIDER_ALIASES = new Set([
  'google',
  'googletrans',
  'googletranslate',
  'google-translate',
  'gtranslate',
  'gtrans'
]);

const TRANSLITERATION_MODE_OPTIONS = [
  {
    value: 'default',
    label: 'Use selected LLM model',
    description: 'Transliteration uses the selected LLM model when enabled.'
  },
  {
    value: 'python',
    label: 'Python transliteration module',
    description: 'Transliteration uses local python modules when available.'
  }
];

function normalizeTranslationProvider(value: string): string {
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return 'llm';
  }
  if (GOOGLE_TRANSLATION_PROVIDER_ALIASES.has(normalized)) {
    return 'googletrans';
  }
  if (normalized === 'llm' || normalized === 'ollama' || normalized === 'default') {
    return 'llm';
  }
  return normalized;
}

function normalizeTransliterationMode(value: string): string {
  const normalized = value.trim().toLowerCase().replace('_', '-');
  if (normalized === 'python' || normalized === 'python-module' || normalized === 'module' || normalized === 'local-module') {
    return 'python';
  }
  if (normalized === 'default' || normalized === 'llm' || normalized === 'ollama') {
    return 'default';
  }
  return 'default';
}

type VideoDubbingOptionsPanelProps = {
  targetLanguage: string;
  sortedLanguageOptions: string[];
  voice: string;
  availableVoiceOptions: Array<{ value: string; label: string }>;
  isLoadingVoices: boolean;
  voiceInventoryError: string | null;
  isPreviewing: boolean;
  previewError: string | null;
  llmModel: string;
  transliterationModel: string;
  llmModels: string[];
  isLoadingModels: boolean;
  modelError: string | null;
  translationProvider: string;
  transliterationMode: string;
  targetHeight: number;
  preserveAspectRatio: boolean;
  splitBatches: boolean;
  stitchBatches: boolean;
  includeTransliteration: boolean;
  enableLookupCache: boolean;
  originalMixPercent: number;
  startOffset: string;
  endOffset: string;
  onTargetLanguageChange: (value: string) => void;
  onVoiceChange: (value: string) => void;
  onPreviewVoice: () => void;
  onModelChange: (value: string) => void;
  onTranslationProviderChange: (value: string) => void;
  onTransliterationModeChange: (value: string) => void;
  onTransliterationModelChange: (value: string) => void;
  onTargetHeightChange: (value: number) => void;
  onPreserveAspectRatioChange: (value: boolean) => void;
  onSplitBatchesChange: (value: boolean) => void;
  onStitchBatchesChange: (value: boolean) => void;
  onIncludeTransliterationChange: (value: boolean) => void;
  onEnableLookupCacheChange: (value: boolean) => void;
  onOriginalMixPercentChange: (value: number) => void;
  onStartOffsetChange: (value: string) => void;
  onEndOffsetChange: (value: string) => void;
};

export default function VideoDubbingOptionsPanel({
  targetLanguage,
  sortedLanguageOptions,
  voice,
  availableVoiceOptions,
  isLoadingVoices,
  voiceInventoryError,
  isPreviewing,
  previewError,
  llmModel,
  transliterationModel,
  llmModels,
  isLoadingModels,
  modelError,
  translationProvider,
  transliterationMode,
  targetHeight,
  preserveAspectRatio,
  splitBatches,
  stitchBatches,
  includeTransliteration,
  enableLookupCache,
  originalMixPercent,
  startOffset,
  endOffset,
  onTargetLanguageChange,
  onVoiceChange,
  onPreviewVoice,
  onModelChange,
  onTranslationProviderChange,
  onTransliterationModeChange,
  onTransliterationModelChange,
  onTargetHeightChange,
  onPreserveAspectRatioChange,
  onSplitBatchesChange,
  onStitchBatchesChange,
  onIncludeTransliterationChange,
  onEnableLookupCacheChange,
  onOriginalMixPercentChange,
  onStartOffsetChange,
  onEndOffsetChange
}: VideoDubbingOptionsPanelProps) {
  const resolvedTranslationProvider = normalizeTranslationProvider(translationProvider);
  const usesGoogleTranslate = resolvedTranslationProvider === 'googletrans';
  const resolvedTransliterationMode = normalizeTransliterationMode(transliterationMode);
  const allowTransliterationModel = resolvedTransliterationMode !== 'python';
  const baseModelOptions = llmModels.length ? llmModels : [DEFAULT_LLM_MODEL];
  const modelOptions = Array.from(
    new Set([...(llmModel.trim() ? [llmModel.trim()] : []), ...baseModelOptions])
  );
  const transliterationModelValue = transliterationModel.trim();
  const transliterationModelOptions = Array.from(
    new Set([...(transliterationModelValue ? [transliterationModelValue] : []), ...modelOptions])
  );
  const selectedTransliterationOption =
    TRANSLITERATION_MODE_OPTIONS.find((option) => option.value === resolvedTransliterationMode) ??
    TRANSLITERATION_MODE_OPTIONS[0];
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Dubbing options</h2>
          <p className={styles.cardHint}>Translate, pick voices, and tune rendering before you submit.</p>
        </div>
      </div>
      <div className={styles.formFields}>
        <label className={styles.field}>
          <span>Translation language</span>
          <LanguageSelect
            value={targetLanguage}
            options={sortedLanguageOptions}
            onChange={onTargetLanguageChange}
            className={styles.input}
          />
          <p className={styles.fieldHint}>
            Matches the Subtitles page list; we will convert it to the correct language code automatically.
          </p>
        </label>
        <label className={styles.fieldCheckbox}>
          <input
            type="checkbox"
            checked={usesGoogleTranslate}
            onChange={(event) => onTranslationProviderChange(event.target.checked ? 'googletrans' : 'llm')}
          />
          <span>Use Google Translate (googletrans) for translations</span>
        </label>
        <p className={styles.fieldHint}>
          {usesGoogleTranslate
            ? 'Translations use googletrans; the LLM is only used for transliteration.'
            : 'Translations use the LLM. Enable googletrans when the cloud model is slow.'}
        </p>
        <label className={styles.field}>
          <span>Voice / audio mode</span>
          <div className={styles.voiceRow}>
            <select
              className={styles.input}
              value={voice}
              onChange={(event) => onVoiceChange(event.target.value)}
              disabled={availableVoiceOptions.length === 0 && isLoadingVoices}
            >
              {availableVoiceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
              {availableVoiceOptions.length === 0 ? <option value={voice}>{voice || 'gTTS'}</option> : null}
            </select>
            <button
              className={styles.secondaryButton}
              type="button"
              onClick={onPreviewVoice}
              disabled={isPreviewing}
            >
              {isPreviewing ? 'Playing…' : 'Play sample'}
            </button>
          </div>
          <p className={styles.fieldHint}>Switch between macOS voices, gTTS, or other configured modes.</p>
        </label>
        <p className={styles.fieldHint}>
          Audio pacing follows the subtitle timing automatically for each sentence.
        </p>
        <label className={styles.field}>
          <span>Translation model</span>
          <select
            className={styles.input}
            value={llmModel}
            onChange={(event) => onModelChange(event.target.value)}
            disabled={isLoadingModels}
          >
          {modelOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
          </select>
          <p className={styles.fieldHint}>
            {usesGoogleTranslate
              ? 'Model used for transliteration when googletrans is enabled.'
              : `Model used when translating subtitles before TTS (defaults to ${DEFAULT_LLM_MODEL}).`}
          </p>
          {isLoadingModels ? <p className={styles.status}>Loading models…</p> : null}
          {modelError ? <p className={styles.error}>{modelError}</p> : null}
        </label>
        <label className={styles.field}>
          <span>Transliteration model</span>
          <select
            className={styles.input}
            value={transliterationModel}
            onChange={(event) => onTransliterationModelChange(event.target.value)}
            disabled={
              !allowTransliterationModel ||
              (isLoadingModels && llmModels.length === 0 && llmModel.trim().length === 0)
            }
          >
            <option value="">Use translation model</option>
            {transliterationModelOptions.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
          <p className={styles.fieldHint}>
            {allowTransliterationModel
              ? 'Overrides the model used for transliteration. Leave blank to reuse the translation model.'
              : 'Transliteration model selection is disabled when using the python module.'}
          </p>
        </label>
        <label className={styles.field}>
          <span>Transliteration mode</span>
          <select
            className={styles.input}
            value={resolvedTransliterationMode}
            onChange={(event) => onTransliterationModeChange(event.target.value)}
          >
            {TRANSLITERATION_MODE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className={styles.fieldHint}>{selectedTransliterationOption.description}</p>
        </label>
        <label className={styles.field}>
          <span>Target resolution</span>
          <select
            className={styles.input}
            value={targetHeight}
            onChange={(event) => onTargetHeightChange(Number(event.target.value))}
          >
            {RESOLUTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className={styles.fieldHint}>Downscale dubbed batches to this height (480p default for NAS playback).</p>
        </label>
        <label className={styles.fieldCheckbox}>
          <input
            type="checkbox"
            checked={preserveAspectRatio}
            onChange={(event) => onPreserveAspectRatioChange(event.target.checked)}
          />
          <span>Keep original aspect ratio (recommended)</span>
        </label>
        <label className={styles.fieldCheckbox}>
          <input
            type="checkbox"
            checked={splitBatches}
            onChange={(event) => onSplitBatchesChange(event.target.checked)}
          />
          <span>Create separate video per batch (adds start-end sentence to filename)</span>
        </label>
        <label className={styles.fieldCheckbox}>
          <input
            type="checkbox"
            checked={stitchBatches}
            onChange={(event) => onStitchBatchesChange(event.target.checked)}
            disabled={!splitBatches}
          />
          <span>Stitch batches into a single final MP4 (default on)</span>
        </label>
        <label className={styles.fieldCheckbox}>
          <input
            type="checkbox"
            checked={includeTransliteration}
            onChange={(event) => onIncludeTransliterationChange(event.target.checked)}
          />
          <span>Include transliteration subtitle track (default on for non-Latin targets)</span>
        </label>
        <label className={styles.fieldCheckbox}>
          <input
            type="checkbox"
            checked={enableLookupCache}
            onChange={(event) => onEnableLookupCacheChange(event.target.checked)}
          />
          <span>Build word lookup cache (enables instant dictionary in player)</span>
        </label>
        <label className={styles.field}>
          <span>Original audio mix</span>
          <div className={styles.rangeRow}>
            <input
              className={styles.rangeInput}
              type="range"
              min={0}
              max={100}
              step={5}
              value={originalMixPercent}
              onChange={(event) => onOriginalMixPercentChange(Number(event.target.value))}
            />
            <span className={styles.rangeValue}>{originalMixPercent}% original</span>
          </div>
          <p className={styles.fieldHint}>
            Amount of the original track to keep under the dub (default 5%).
          </p>
        </label>
        <div className={styles.field}>
          <span>Clip window (seconds)</span>
          <div className={styles.clipInputs}>
            <input
              className={styles.input}
              type="text"
              value={startOffset}
              onChange={(event) => onStartOffsetChange(event.target.value)}
              placeholder="Start (e.g., 45 or 00:45)"
            />
            <input
              className={styles.input}
              type="text"
              value={endOffset}
              onChange={(event) => onEndOffsetChange(event.target.value)}
              placeholder="End (e.g., 01:30)"
            />
          </div>
          <p className={styles.fieldHint}>Leave blank to dub the entire video. Use offsets to render a short slice.</p>
        </div>
      </div>
      <div className={styles.actions}>
        {isLoadingVoices ? <p className={styles.status}>Loading voices…</p> : null}
        {voiceInventoryError ? <p className={styles.error}>{voiceInventoryError}</p> : null}
        {previewError ? <p className={styles.error}>{previewError}</p> : null}
      </div>
    </section>
  );
}
