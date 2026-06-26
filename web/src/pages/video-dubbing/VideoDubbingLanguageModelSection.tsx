import LanguageSelect from '../../components/LanguageSelect';
import {
  TRANSLITERATION_MODE_OPTIONS,
  buildLlmModelOptions,
  buildTransliterationModelOptions,
  getTransliterationModeOption,
  normalizeTranslationProvider,
  normalizeTransliterationMode
} from '../../utils/translationControls';
import { DEFAULT_LLM_MODEL } from './videoDubbingConfig';
import styles from '../VideoDubbingPage.module.css';

type VideoDubbingLanguageModelSectionProps = {
  targetLanguage: string;
  sortedLanguageOptions: string[];
  voice: string;
  availableVoiceOptions: Array<{ value: string; label: string }>;
  isLoadingVoices: boolean;
  isPreviewing: boolean;
  llmModel: string;
  transliterationModel: string;
  llmModels: string[];
  isLoadingModels: boolean;
  modelError: string | null;
  translationProvider: string;
  transliterationMode: string;
  onTargetLanguageChange: (value: string) => void;
  onVoiceChange: (value: string) => void;
  onPreviewVoice: () => void;
  onModelChange: (value: string) => void;
  onTranslationProviderChange: (value: string) => void;
  onTransliterationModeChange: (value: string) => void;
  onTransliterationModelChange: (value: string) => void;
};

export default function VideoDubbingLanguageModelSection({
  targetLanguage,
  sortedLanguageOptions,
  voice,
  availableVoiceOptions,
  isLoadingVoices,
  isPreviewing,
  llmModel,
  transliterationModel,
  llmModels,
  isLoadingModels,
  modelError,
  translationProvider,
  transliterationMode,
  onTargetLanguageChange,
  onVoiceChange,
  onPreviewVoice,
  onModelChange,
  onTranslationProviderChange,
  onTransliterationModeChange,
  onTransliterationModelChange
}: VideoDubbingLanguageModelSectionProps) {
  const resolvedTranslationProvider = normalizeTranslationProvider(translationProvider);
  const usesGoogleTranslate = resolvedTranslationProvider === 'googletrans';
  const resolvedTransliterationMode = normalizeTransliterationMode(transliterationMode);
  const allowTransliterationModel = resolvedTransliterationMode !== 'python';
  const modelOptions = buildLlmModelOptions(llmModel, llmModels, [DEFAULT_LLM_MODEL]);
  const transliterationModelOptions = buildTransliterationModelOptions(transliterationModel, modelOptions);
  const selectedTransliterationOption = getTransliterationModeOption(resolvedTransliterationMode);

  return (
    <>
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
    </>
  );
}
