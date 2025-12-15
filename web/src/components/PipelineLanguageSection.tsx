import { useMemo } from 'react';
import { buildLanguageOptions, sortLanguageLabelsByName } from '../utils/languages';
import LanguageSelect from './LanguageSelect';
import LanguageSelector from './LanguageSelector';

type LanguageSectionProps = {
  headingId: string;
  title: string;
  description: string;
  inputLanguage: string;
  targetLanguages: string[];
  customTargetLanguages: string;
  ollamaModel: string;
  llmModels: string[];
  llmModelsLoading: boolean;
  llmModelsError: string | null;
  sentencesPerOutputFile: number;
  startSentence: number;
  endSentence: string;
  stitchFull: boolean;
  disableProcessingWindow?: boolean;
  onInputLanguageChange: (value: string) => void;
  onTargetLanguagesChange: (value: string[]) => void;
  onCustomTargetLanguagesChange: (value: string) => void;
  onOllamaModelChange: (value: string) => void;
  onSentencesPerOutputFileChange: (value: number) => void;
  onStartSentenceChange: (value: number) => void;
  onEndSentenceChange: (value: string) => void;
  onStitchFullChange: (value: boolean) => void;
};

const PipelineLanguageSection = ({
  headingId,
  title,
  description,
  inputLanguage,
  targetLanguages,
  ollamaModel,
  llmModels,
  llmModelsLoading,
  llmModelsError,
  sentencesPerOutputFile,
  startSentence,
  endSentence,
  stitchFull,
  disableProcessingWindow = false,
  onInputLanguageChange,
  onTargetLanguagesChange,
  onOllamaModelChange,
  onSentencesPerOutputFileChange,
  onStartSentenceChange,
  onEndSentenceChange,
  onStitchFullChange
}: LanguageSectionProps) => {
  const currentModel = ollamaModel.trim();
  const resolvedModels = llmModels.length ? llmModels : currentModel ? [currentModel] : [];
  const modelOptions = Array.from(new Set([...(currentModel ? [currentModel] : []), ...resolvedModels]));
  const inputLanguageOptions = useMemo(
    () =>
      sortLanguageLabelsByName(
        buildLanguageOptions({
          preferredLanguages: [inputLanguage],
          fallback: 'English'
        })
      ),
    [inputLanguage]
  );
  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="pipeline-card__body">
        <label htmlFor="input_language">Input language</label>
        <LanguageSelect
          id="input_language"
          value={inputLanguage}
          options={inputLanguageOptions}
          onChange={onInputLanguageChange}
        />
        <label htmlFor="target_languages">Target languages</label>
        <LanguageSelector
          id="target_languages"
          value={targetLanguages}
          onChange={onTargetLanguagesChange}
        />
        <label htmlFor="ollama_model">LLM model (optional)</label>
        <select
          id="ollama_model"
          name="ollama_model"
          value={ollamaModel}
          onChange={(event) => onOllamaModelChange(event.target.value)}
          disabled={llmModelsLoading && llmModels.length === 0 && currentModel.length === 0}
        >
          <option value="">Use server default</option>
          {modelOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
        <small className="form-help-text">
          {llmModelsLoading
            ? 'Loading available models…'
            : llmModelsError
            ? `Unable to load models (${llmModelsError}).`
            : 'Leave blank to use the default server model.'}
        </small>
        <div className="field-grid">
          <label htmlFor="sentences_per_output_file">
            Sentences per output file
            <input
              id="sentences_per_output_file"
              name="sentences_per_output_file"
              type="number"
              min={1}
              value={sentencesPerOutputFile}
              onChange={(event) => onSentencesPerOutputFileChange(Number(event.target.value))}
            />
          </label>
          <label htmlFor="start_sentence">
            Start sentence
            <input
              id="start_sentence"
              name="start_sentence"
              type="number"
              min={1}
              value={startSentence}
              disabled={disableProcessingWindow}
              onChange={(event) => onStartSentenceChange(Number(event.target.value))}
            />
          </label>
          <label htmlFor="end_sentence">
            End sentence (optional, supports +offset)
            <input
              id="end_sentence"
              name="end_sentence"
              type="text"
              inputMode="numeric"
              value={endSentence}
              disabled={disableProcessingWindow}
              onChange={(event) => onEndSentenceChange(event.target.value)}
              placeholder="Leave blank for full run or enter +100 for the next 100 sentences"
            />
          </label>
        </div>
        <label className="checkbox">
          <input
            type="checkbox"
            name="stitch_full"
            checked={stitchFull}
            onChange={(event) => onStitchFullChange(event.target.checked)}
          />
          Stitch full document once complete
        </label>
      </div>
    </section>
  );
};

export default PipelineLanguageSection;
