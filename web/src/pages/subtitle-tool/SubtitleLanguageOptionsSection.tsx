import LanguageSelect from '../../components/LanguageSelect';
import {
  TRANSLITERATION_MODE_OPTIONS,
  buildLlmModelOptions,
  buildTransliterationModelOptions,
  getTransliterationModeOption,
  normalizeTranslationProvider,
  normalizeTransliterationMode
} from '../../utils/translationControls';
import { DEFAULT_LLM_MODEL } from './subtitleToolConfig';

type SubtitleLanguageOptionsSectionProps = {
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
};

export default function SubtitleLanguageOptionsSection({
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
  onMirrorToSourceDirChange
}: SubtitleLanguageOptionsSectionProps) {
  const resolvedTranslationProvider = normalizeTranslationProvider(translationProvider);
  const usesGoogleTranslate = resolvedTranslationProvider === 'googletrans';
  const resolvedTransliterationMode = normalizeTransliterationMode(transliterationMode);
  const allowTransliterationModel = resolvedTransliterationMode !== 'python';
  const modelOptions = buildLlmModelOptions(selectedModel, availableModels, [DEFAULT_LLM_MODEL]);
  const transliterationModelOptions = buildTransliterationModelOptions(transliterationModel, modelOptions);
  const selectedTransliterationOption = getTransliterationModeOption(resolvedTransliterationMode);

  return (
    <fieldset>
      <legend>Languages & models</legend>
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
        <label>
          <input
            type="checkbox"
            checked={usesGoogleTranslate}
            onChange={(event) => onTranslationProviderChange(event.target.checked ? 'googletrans' : 'llm')}
          />
          Use Google Translate (googletrans) for translations
        </label>
        <small className="field-note">
          {usesGoogleTranslate
            ? 'Translations use googletrans; the LLM is only used for transliteration.'
            : 'Translations use the LLM. Enable googletrans when the cloud model is slow.'}
        </small>
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
          {modelOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
        <small className="field-note">
          {modelsLoading
            ? 'Loading models from Ollama...'
            : modelsError
            ? `Unable to load models (${modelsError}).`
            : usesGoogleTranslate
            ? 'Leave blank to use the default server model for transliteration.'
            : 'Leave blank to use the default server model.'}
        </small>
      </div>
      <div className="field">
        <label className="field-label" htmlFor="subtitle-transliteration-model">Transliteration model (optional)</label>
        <select
          id="subtitle-transliteration-model"
          value={transliterationModel}
          onChange={(event) => onTransliterationModelChange(event.target.value)}
          disabled={
            !allowTransliterationModel ||
            (modelsLoading && availableModels.length === 0 && selectedModel.trim().length === 0)
          }
        >
          <option value="">Use translation model</option>
          {transliterationModelOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
        <small className="field-note">
          {allowTransliterationModel
            ? 'Overrides the model used for transliteration. Leave blank to reuse the translation model.'
            : 'Transliteration model selection is disabled when using the python module.'}
        </small>
      </div>
      <div className="field">
        <label className="field-label" htmlFor="subtitle-transliteration-mode">Transliteration mode</label>
        <select
          id="subtitle-transliteration-mode"
          value={resolvedTransliterationMode}
          onChange={(event) => onTransliterationModeChange(event.target.value)}
        >
          {TRANSLITERATION_MODE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <small className="field-note">
          {selectedTransliterationOption.description} Transliteration only appears when enabled.
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
      </div>
    </fieldset>
  );
}
