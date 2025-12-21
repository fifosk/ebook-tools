import { useMemo } from 'react';
import { buildLanguageOptions, sortLanguageLabelsByName } from '../../utils/languages';
import LanguageSelect from '../LanguageSelect';

type BookNarrationLanguageSectionProps = {
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
  processingMode?: 'range' | 'chapters';
  chapterOptions?: BookNarrationChapterOption[];
  selectedChapterIds?: string[];
  chapterSummary?: string;
  chaptersLoading?: boolean;
  chaptersError?: string | null;
  chaptersDisabled?: boolean;
  estimatedAudioDurationLabel?: string | null;
  onProcessingModeChange?: (value: 'range' | 'chapters') => void;
  onChapterToggle?: (chapterId: string) => void;
  onChapterClear?: () => void;
  onInputLanguageChange: (value: string) => void;
  onTargetLanguagesChange: (value: string[]) => void;
  onCustomTargetLanguagesChange: (value: string) => void;
  onOllamaModelChange: (value: string) => void;
  onSentencesPerOutputFileChange: (value: number) => void;
  onStartSentenceChange: (value: number) => void;
  onEndSentenceChange: (value: string) => void;
  onStitchFullChange: (value: boolean) => void;
};

export type BookNarrationChapterOption = {
  id: string;
  title: string;
  startSentence: number;
  endSentence: number | null;
};

const BookNarrationLanguageSection = ({
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
  processingMode = 'range',
  chapterOptions = [],
  selectedChapterIds = [],
  chapterSummary,
  chaptersLoading = false,
  chaptersError = null,
  chaptersDisabled = false,
  estimatedAudioDurationLabel = null,
  onProcessingModeChange,
  onChapterToggle,
  onChapterClear,
  onInputLanguageChange,
  onTargetLanguagesChange,
  onOllamaModelChange,
  onSentencesPerOutputFileChange,
  onStartSentenceChange,
  onEndSentenceChange,
  onStitchFullChange
}: BookNarrationLanguageSectionProps) => {
  const sentenceRangeDisabled = disableProcessingWindow || processingMode === 'chapters';
  const showChapterPicker = processingMode === 'chapters';
  const chapterSelectDisabled = chaptersDisabled || (!chaptersLoading && chapterOptions.length === 0);
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
  const targetLanguage = targetLanguages[0] ?? '';
  const targetLanguageOptions = useMemo(
    () =>
      sortLanguageLabelsByName(
        buildLanguageOptions({
          preferredLanguages: [targetLanguage, inputLanguage],
          fallback: targetLanguage || 'Arabic'
        })
      ),
    [inputLanguage, targetLanguage]
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
        <label htmlFor="target_languages">Target language</label>
        <LanguageSelect
          id="target_languages"
          value={targetLanguage}
          options={targetLanguageOptions}
          onChange={(value) => onTargetLanguagesChange(value ? [value] : [])}
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
              disabled={sentenceRangeDisabled}
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
              disabled={sentenceRangeDisabled}
              onChange={(event) => onEndSentenceChange(event.target.value)}
              placeholder="Leave blank for full run or enter +100 for the next 100 sentences"
            />
          </label>
        </div>
        <div className="pipeline-chapter-window" aria-live="polite">
          <div className="pipeline-chapter-window__header">
            <span className="pipeline-chapter-window__label">Processing window</span>
            <div className="pipeline-chapter-window__toggle" role="group" aria-label="Processing window mode">
              <button
                type="button"
                className={`pipeline-chapter-window__toggle-button${
                  processingMode === 'range' ? ' is-active' : ''
                }`}
                onClick={() => onProcessingModeChange?.('range')}
              >
                Sentence range
              </button>
              <button
                type="button"
                className={`pipeline-chapter-window__toggle-button${
                  processingMode === 'chapters' ? ' is-active' : ''
                }`}
                onClick={() => onProcessingModeChange?.('chapters')}
                disabled={chapterSelectDisabled}
                title={
                  chapterSelectDisabled
                    ? chaptersLoading
                      ? 'Loading chapters...'
                      : 'Chapters are not available for this file'
                    : 'Select chapters'
                }
              >
                Chapters
              </button>
            </div>
          </div>
          {showChapterPicker ? (
            <div className="pipeline-chapter-window__panel">
              {chaptersLoading ? (
                <span className="form-help-text">Loading chapters…</span>
              ) : null}
              {chaptersError ? <span className="form-help-text form-help-text--error">{chaptersError}</span> : null}
              {!chaptersLoading && chapterOptions.length === 0 && !chaptersError ? (
                <span className="form-help-text">No chapter data found for this EPUB.</span>
              ) : null}
              {chapterOptions.length > 0 ? (
                <div className="pipeline-chapter-window__list" role="list">
                  {chapterOptions.map((chapter, index) => {
                    const range =
                      typeof chapter.endSentence === 'number'
                        ? `${chapter.startSentence}-${chapter.endSentence}`
                        : `${chapter.startSentence}+`;
                    const checked = selectedChapterIds.includes(chapter.id);
                    return (
                      <label
                        key={chapter.id}
                        className={`pipeline-chapter-window__option${
                          checked ? ' is-selected' : ''
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => onChapterToggle?.(chapter.id)}
                        />
                        <span className="pipeline-chapter-window__title">
                          {chapter.title || `Chapter ${index + 1}`}
                        </span>
                        <span className="pipeline-chapter-window__range">{range}</span>
                      </label>
                    );
                  })}
                </div>
              ) : null}
              {chapterSummary ? <span className="form-help-text">{chapterSummary}</span> : null}
              {selectedChapterIds.length > 0 ? (
                <button
                  type="button"
                  className="pipeline-chapter-window__clear"
                  onClick={onChapterClear}
                >
                  Clear selection
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
        {estimatedAudioDurationLabel ? (
          <span className="form-help-text">{estimatedAudioDurationLabel}</span>
        ) : null}
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

export default BookNarrationLanguageSection;
