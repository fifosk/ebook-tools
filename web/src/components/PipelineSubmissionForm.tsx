import { FormEvent, useEffect, useMemo, useState } from 'react';
import { PipelineFileBrowserResponse, PipelineRequestPayload } from '../api/dtos';
import { fetchPipelineDefaults, fetchPipelineFiles } from '../api/client';
import LanguageSelector from './LanguageSelector';
import {
  AUDIO_MODE_OPTIONS,
  MenuOption,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../constants/menuOptions';
import FileSelectionDialog from './FileSelectionDialog';

type Props = {
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
};

type JsonFields =
  | 'config'
  | 'environment_overrides'
  | 'pipeline_overrides'
  | 'book_metadata';

type FormState = {
  input_file: string;
  base_output_file: string;
  input_language: string;
  target_languages: string[];
  custom_target_languages: string;
  sentences_per_output_file: number;
  start_sentence: number;
  end_sentence: string;
  stitch_full: boolean;
  generate_audio: boolean;
  audio_mode: string;
  written_mode: string;
  selected_voice: string;
  output_html: boolean;
  output_pdf: boolean;
  generate_video: boolean;
  include_transliteration: boolean;
  tempo: number;
  thread_count: string;
  queue_size: string;
  job_max_workers: string;
  slide_parallelism: string;
  slide_parallel_workers: string;
  config: string;
  environment_overrides: string;
  pipeline_overrides: string;
  book_metadata: string;
};

const DEFAULT_FORM_STATE: FormState = {
  input_file: '',
  base_output_file: '',
  input_language: 'English',
  target_languages: [],
  custom_target_languages: '',
  sentences_per_output_file: 10,
  start_sentence: 1,
  end_sentence: '',
  stitch_full: false,
  generate_audio: true,
  audio_mode: '1',
  written_mode: '4',
  selected_voice: 'gTTS',
  output_html: true,
  output_pdf: false,
  generate_video: false,
  include_transliteration: false,
  tempo: 1,
  thread_count: '',
  queue_size: '',
  job_max_workers: '',
  slide_parallelism: '',
  slide_parallel_workers: '',
  config: '{}',
  environment_overrides: '{}',
  pipeline_overrides: '{}',
  book_metadata: '{}'
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function coerceNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return undefined;
    }
    const parsed = Number(trimmed);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function extractBookMetadata(config: Record<string, unknown>): Record<string, unknown> | null {
  const metadata: Record<string, unknown> = {};
  const nested = config['book_metadata'];
  if (isRecord(nested)) {
    for (const [key, value] of Object.entries(nested)) {
      if (value !== undefined && value !== null) {
        metadata[key] = value;
      }
    }
  }

  const preferredKeys = [
    'book_cover_title',
    'book_title',
    'book_author',
    'book_year',
    'book_summary',
    'book_cover_file'
  ];

  for (const key of preferredKeys) {
    const value = config[key];
    if (value !== undefined && value !== null) {
      metadata[key] = value;
    }
  }

  return Object.keys(metadata).length > 0 ? metadata : null;
}

function applyConfigDefaults(previous: FormState, config: Record<string, unknown>): FormState {
  const next: FormState = { ...previous };

  const inputFile = config['input_file'];
  if (typeof inputFile === 'string') {
    next.input_file = inputFile;
  }

  const baseOutput = config['base_output_file'];
  if (typeof baseOutput === 'string') {
    next.base_output_file = baseOutput;
  }

  const inputLanguage = config['input_language'];
  if (typeof inputLanguage === 'string') {
    next.input_language = inputLanguage;
  }

  const targetLanguages = config['target_languages'];
  if (Array.isArray(targetLanguages)) {
    const normalized = Array.from(
      new Set(
        targetLanguages
          .filter((language): language is string => typeof language === 'string')
          .map((language) => language.trim())
          .filter((language) => language.length > 0)
      )
    );
    next.target_languages = normalized;
  }

  const sentencesPerOutput = coerceNumber(config['sentences_per_output_file']);
  if (sentencesPerOutput !== undefined) {
    next.sentences_per_output_file = sentencesPerOutput;
  }

  const startSentence = coerceNumber(config['start_sentence']);
  if (startSentence !== undefined) {
    next.start_sentence = startSentence;
  }

  const endSentence = config['end_sentence'];
  if (endSentence === null || endSentence === undefined || endSentence === '') {
    next.end_sentence = '';
  } else {
    const parsedEnd = coerceNumber(endSentence);
    if (parsedEnd !== undefined) {
      next.end_sentence = String(parsedEnd);
    }
  }

  const stitchFull = config['stitch_full'];
  if (typeof stitchFull === 'boolean') {
    next.stitch_full = stitchFull;
  }

  const generateAudio = config['generate_audio'];
  if (typeof generateAudio === 'boolean') {
    next.generate_audio = generateAudio;
  }

  const audioMode = config['audio_mode'];
  if (typeof audioMode === 'string') {
    next.audio_mode = audioMode;
  }

  const writtenMode = config['written_mode'];
  if (typeof writtenMode === 'string') {
    next.written_mode = writtenMode;
  }

  const selectedVoice = config['selected_voice'];
  if (typeof selectedVoice === 'string') {
    next.selected_voice = selectedVoice;
  }

  const outputHtml = config['output_html'];
  if (typeof outputHtml === 'boolean') {
    next.output_html = outputHtml;
  }

  const outputPdf = config['output_pdf'];
  if (typeof outputPdf === 'boolean') {
    next.output_pdf = outputPdf;
  }

  const generateVideo = config['generate_video'];
  if (typeof generateVideo === 'boolean') {
    next.generate_video = generateVideo;
  }

  const includeTransliteration = config['include_transliteration'];
  if (typeof includeTransliteration === 'boolean') {
    next.include_transliteration = includeTransliteration;
  }

  const tempo = coerceNumber(config['tempo']);
  if (tempo !== undefined) {
    next.tempo = tempo;
  }

  const threadCount = coerceNumber(config['thread_count']);
  if (threadCount !== undefined) {
    next.thread_count = String(threadCount);
  }

  const queueSize = coerceNumber(config['queue_size']);
  if (queueSize !== undefined) {
    next.queue_size = String(queueSize);
  }

  const jobMaxWorkers = coerceNumber(config['job_max_workers']);
  if (jobMaxWorkers !== undefined) {
    next.job_max_workers = String(jobMaxWorkers);
  }

  const slideParallelism = config['slide_parallelism'];
  if (typeof slideParallelism === 'string') {
    next.slide_parallelism = slideParallelism;
  }

  const slideParallelWorkers = coerceNumber(config['slide_parallel_workers']);
  if (slideParallelWorkers !== undefined) {
    next.slide_parallel_workers = String(slideParallelWorkers);
  }

  const metadata = extractBookMetadata(config);
  if (metadata) {
    next.book_metadata = JSON.stringify(metadata, null, 2);
  }

  return next;
}

function parseJsonField(label: JsonFields, value: string): Record<string, unknown> {
  if (!value.trim()) {
    return {};
  }

  try {
    const parsed = JSON.parse(value);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error(`${label} must be an object`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Invalid JSON for ${label}: ${message}`);
  }
}

function parseOptionalNumberInput(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = Number(trimmed);
  if (Number.isNaN(parsed)) {
    return undefined;
  }
  return parsed;
}

export function PipelineSubmissionForm({ onSubmit, isSubmitting = false }: Props) {
  const [formState, setFormState] = useState<FormState>(DEFAULT_FORM_STATE);
  const [error, setError] = useState<string | null>(null);
  const [fileOptions, setFileOptions] = useState<PipelineFileBrowserResponse | null>(null);
  const [fileDialogError, setFileDialogError] = useState<string | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [activeFileDialog, setActiveFileDialog] = useState<'input' | 'output' | null>(null);

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setFormState((previous) => ({
      ...previous,
      [key]: value
    }));
  };

  const handleInputFileChange = (value: string) => {
    setFormState((previous) => {
      if (previous.input_file === value) {
        return previous;
      }
      return {
        ...previous,
        input_file: value,
        book_metadata: '{}'
      };
    });
  };

  const availableAudioModes = useMemo<MenuOption[]>(() => AUDIO_MODE_OPTIONS, []);
  const availableWrittenModes = useMemo<MenuOption[]>(() => WRITTEN_MODE_OPTIONS, []);
  const availableVoices = useMemo<MenuOption[]>(() => VOICE_OPTIONS, []);

  useEffect(() => {
    let cancelled = false;
    fetchPipelineDefaults()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setFormState((previous) => applyConfigDefaults(previous, response.config));
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn('Unable to load pipeline defaults', error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setIsLoadingFiles(true);
    fetchPipelineFiles()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setFileOptions(response);
        setFileDialogError(null);
      })
      .catch((fetchError) => {
        if (cancelled) {
          return;
        }
        const message =
          fetchError instanceof Error ? fetchError.message : 'Unable to load available files.';
        setFileDialogError(message);
        setFileOptions(null);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingFiles(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      const json: Record<JsonFields, Record<string, unknown>> = {
        config: parseJsonField('config', formState.config),
        environment_overrides: parseJsonField(
          'environment_overrides',
          formState.environment_overrides
        ),
        pipeline_overrides: parseJsonField('pipeline_overrides', formState.pipeline_overrides),
        book_metadata: parseJsonField('book_metadata', formState.book_metadata)
      };

      const manualTargets = formState.custom_target_languages
        .split(',')
        .map((language) => language.trim())
        .filter(Boolean);

      const targetLanguages = Array.from(new Set([...formState.target_languages, ...manualTargets]));

      if (targetLanguages.length === 0) {
        throw new Error('Please choose at least one target language.');
      }

      const pipelineOverrides = { ...json.pipeline_overrides };

      const threadCount = parseOptionalNumberInput(formState.thread_count);
      if (threadCount !== undefined) {
        pipelineOverrides.thread_count = threadCount;
      }

      const queueSize = parseOptionalNumberInput(formState.queue_size);
      if (queueSize !== undefined) {
        pipelineOverrides.queue_size = queueSize;
      }

      const jobMaxWorkers = parseOptionalNumberInput(formState.job_max_workers);
      if (jobMaxWorkers !== undefined) {
        pipelineOverrides.job_max_workers = jobMaxWorkers;
      }

      const slideParallelism = formState.slide_parallelism.trim();
      if (slideParallelism) {
        pipelineOverrides.slide_parallelism = slideParallelism;
      }

      const slideParallelWorkers = parseOptionalNumberInput(formState.slide_parallel_workers);
      if (slideParallelWorkers !== undefined) {
        pipelineOverrides.slide_parallel_workers = slideParallelWorkers;
      }

      const payload: PipelineRequestPayload = {
        config: json.config,
        environment_overrides: json.environment_overrides,
        pipeline_overrides: pipelineOverrides,
        inputs: {
          input_file: formState.input_file,
          base_output_file: formState.base_output_file,
          input_language: formState.input_language,
          target_languages: targetLanguages,
          sentences_per_output_file: Number(formState.sentences_per_output_file),
          start_sentence: Number(formState.start_sentence),
          end_sentence: formState.end_sentence ? Number(formState.end_sentence) : null,
          stitch_full: formState.stitch_full,
          generate_audio: formState.generate_audio,
          audio_mode: formState.audio_mode,
          written_mode: formState.written_mode,
          selected_voice: formState.selected_voice,
          output_html: formState.output_html,
          output_pdf: formState.output_pdf,
          generate_video: formState.generate_video,
          include_transliteration: formState.include_transliteration,
          tempo: Number(formState.tempo),
          book_metadata: json.book_metadata
        }
      };

      await onSubmit(payload);
    } catch (submissionError) {
      const message =
        submissionError instanceof Error
          ? submissionError.message
          : 'Unable to submit pipeline request';
      setError(message);
    }
  };

  return (
    <section>
      <h2>Submit a Pipeline Job</h2>
      <p>
        Provide the input file, target languages, and any overrides to enqueue a new ebook processing
        job.
      </p>
      {error ? <div className="alert" role="alert">{error}</div> : null}
      <form onSubmit={handleSubmit} className="pipeline-form">
        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Source material</legend>
          <details open>
            <summary>Source material</summary>
            <label htmlFor="input_file">Input file path</label>
            <input
              id="input_file"
              name="input_file"
              type="text"
              value={formState.input_file}
              onChange={(event) => handleInputFileChange(event.target.value)}
              placeholder="/books/source.epub"
              required
            />
            <button
              type="button"
              className="link-button"
              onClick={() => setActiveFileDialog('input')}
              disabled={!fileOptions || isLoadingFiles}
            >
              {isLoadingFiles ? 'Loading…' : 'Browse ebooks'}
            </button>
            {fileDialogError ? (
              <p className="form-help-text" role="status">
                {fileDialogError}
              </p>
            ) : null}

            <label htmlFor="base_output_file">Base output file</label>
            <input
              id="base_output_file"
              name="base_output_file"
              type="text"
              value={formState.base_output_file}
              onChange={(event) => handleChange('base_output_file', event.target.value)}
              placeholder="ebooks/output"
              required
            />
            <button
              type="button"
              className="link-button"
              onClick={() => setActiveFileDialog('output')}
              disabled={!fileOptions || isLoadingFiles}
            >
              {isLoadingFiles ? 'Loading…' : 'Browse output paths'}
            </button>

            <label htmlFor="input_language">Input language</label>
            <input
              id="input_language"
              name="input_language"
              type="text"
              value={formState.input_language}
              onChange={(event) => handleChange('input_language', event.target.value)}
              required
              placeholder="English"
            />
          </details>
        </fieldset>

        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Target languages</legend>
          <details open>
            <summary>Target languages</summary>
            <LanguageSelector
              value={formState.target_languages}
              onChange={(next) => handleChange('target_languages', next)}
            />
            <label htmlFor="custom_target_languages">Other target languages (comma separated)</label>
            <input
              id="custom_target_languages"
              name="custom_target_languages"
              type="text"
              value={formState.custom_target_languages}
              onChange={(event) => handleChange('custom_target_languages', event.target.value)}
              placeholder="e.g. Klingon, Sindarin"
            />
          </details>
        </fieldset>

        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Sentence window</legend>
          <details open>
            <summary>Sentence window</summary>
            <div className="field-grid">
              <label htmlFor="sentences_per_output_file">
                Sentences per output file
                <input
                  id="sentences_per_output_file"
                  name="sentences_per_output_file"
                  type="number"
                  min={1}
                  value={formState.sentences_per_output_file}
                  onChange={(event) =>
                    handleChange('sentences_per_output_file', Number(event.target.value))
                  }
                />
              </label>
              <label htmlFor="start_sentence">
                Start sentence
                <input
                  id="start_sentence"
                  name="start_sentence"
                  type="number"
                  min={1}
                  value={formState.start_sentence}
                  onChange={(event) => handleChange('start_sentence', Number(event.target.value))}
                />
              </label>
              <label htmlFor="end_sentence">
                End sentence (optional)
                <input
                  id="end_sentence"
                  name="end_sentence"
                  type="number"
                  min={formState.start_sentence}
                  value={formState.end_sentence}
                  onChange={(event) => handleChange('end_sentence', event.target.value)}
                  placeholder="Leave blank for entire document"
                />
              </label>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                name="stitch_full"
                checked={formState.stitch_full}
                onChange={(event) => handleChange('stitch_full', event.target.checked)}
              />
              Stitch full document once complete
            </label>
          </details>
        </fieldset>

        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Audio narration</legend>
          <details open>
            <summary>Audio narration</summary>
            <label className="checkbox">
              <input
                type="checkbox"
                name="generate_audio"
                checked={formState.generate_audio}
                onChange={(event) => handleChange('generate_audio', event.target.checked)}
              />
              Generate narration tracks
            </label>

            <div className="option-grid">
              {availableAudioModes.map((option) => (
                <label key={option.value} className="option-card">
                  <input
                    type="radio"
                    name="audio_mode"
                    value={option.value}
                    checked={formState.audio_mode === option.value}
                    onChange={(event) => handleChange('audio_mode', event.target.value)}
                  />
                  <div>
                    <strong>{option.label}</strong>
                    <p>{option.description}</p>
                  </div>
                </label>
              ))}
            </div>

            <div className="option-grid">
              {availableVoices.map((option) => (
                <label key={option.value} className="option-card">
                  <input
                    type="radio"
                    name="selected_voice"
                    value={option.value}
                    checked={formState.selected_voice === option.value}
                    onChange={(event) => handleChange('selected_voice', event.target.value)}
                  />
                  <div>
                    <strong>{option.label}</strong>
                    <p>{option.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </details>
        </fieldset>

        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Written output</legend>
          <details open>
            <summary>Written output</summary>
            <div className="option-grid">
              {availableWrittenModes.map((option) => (
                <label key={option.value} className="option-card">
                  <input
                    type="radio"
                    name="written_mode"
                    value={option.value}
                    checked={formState.written_mode === option.value}
                    onChange={(event) => handleChange('written_mode', event.target.value)}
                  />
                  <div>
                    <strong>{option.label}</strong>
                    <p>{option.description}</p>
                  </div>
                </label>
              ))}
            </div>

            <label className="checkbox">
              <input
                type="checkbox"
                name="output_html"
                checked={formState.output_html}
                onChange={(event) => handleChange('output_html', event.target.checked)}
              />
              Generate HTML output
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                name="output_pdf"
                checked={formState.output_pdf}
                onChange={(event) => handleChange('output_pdf', event.target.checked)}
              />
              Generate PDF output
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                name="include_transliteration"
                checked={formState.include_transliteration}
                onChange={(event) => handleChange('include_transliteration', event.target.checked)}
              />
              Include transliteration in written output
            </label>
          </details>
        </fieldset>

        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Performance tuning</legend>
          <details open>
            <summary>Performance tuning</summary>
            <p className="form-help-text">
              Adjust concurrency and queue sizing to match your hardware capabilities.
            </p>
            <div className="collapsible-group">
              <details>
                <summary>Translation threads</summary>
                <p className="form-help-text">
                  Control how many translation and media workers run simultaneously. Leave blank to
                  use the backend default.
                </p>
                <label htmlFor="thread_count">
                  Worker threads
                  <input
                    id="thread_count"
                    name="thread_count"
                    type="number"
                    min={1}
                    step={1}
                    value={formState.thread_count}
                    onChange={(event) => handleChange('thread_count', event.target.value)}
                    placeholder="Default"
                  />
                </label>
              </details>
              <details>
                <summary>Job orchestration</summary>
                <p className="form-help-text">
                  Tune job level parallelism and queue pressure for large or resource constrained
                  hosts.
                </p>
                <label htmlFor="job_max_workers">
                  Maximum concurrent jobs
                  <input
                    id="job_max_workers"
                    name="job_max_workers"
                    type="number"
                    min={1}
                    step={1}
                    value={formState.job_max_workers}
                    onChange={(event) => handleChange('job_max_workers', event.target.value)}
                    placeholder="Default"
                  />
                </label>
                <label htmlFor="queue_size">
                  Translation queue size
                  <input
                    id="queue_size"
                    name="queue_size"
                    type="number"
                    min={1}
                    step={1}
                    value={formState.queue_size}
                    onChange={(event) => handleChange('queue_size', event.target.value)}
                    placeholder="Default"
                  />
                </label>
              </details>
              <details>
                <summary>Slide rendering parallelism</summary>
                <p className="form-help-text">
                  Select the rendering backend for slide generation and optionally cap worker count
                  when video output is enabled.
                </p>
                <label htmlFor="slide_parallelism">
                  Slide parallelism mode
                  <select
                    id="slide_parallelism"
                    name="slide_parallelism"
                    value={formState.slide_parallelism}
                    onChange={(event) => handleChange('slide_parallelism', event.target.value)}
                  >
                    <option value="">Use configured default</option>
                    <option value="off">Off</option>
                    <option value="auto">Auto</option>
                    <option value="thread">Thread</option>
                    <option value="process">Process</option>
                  </select>
                </label>
                <label htmlFor="slide_parallel_workers">
                  Parallel slide workers
                  <input
                    id="slide_parallel_workers"
                    name="slide_parallel_workers"
                    type="number"
                    min={1}
                    step={1}
                    value={formState.slide_parallel_workers}
                    onChange={(event) => handleChange('slide_parallel_workers', event.target.value)}
                    placeholder="Default"
                  />
                </label>
              </details>
            </div>
          </details>
        </fieldset>

        <fieldset className="collapsible-fieldset">
          <legend className="visually-hidden">Advanced options</legend>
          <details open>
            <summary>Advanced options</summary>
            <label htmlFor="tempo">
              Tempo
              <input
                id="tempo"
                name="tempo"
                type="number"
                step="0.1"
                min={0.5}
                value={formState.tempo}
                onChange={(event) => handleChange('tempo', Number(event.target.value))}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                name="generate_video"
                checked={formState.generate_video}
                onChange={(event) => handleChange('generate_video', event.target.checked)}
              />
              Generate stitched video assets
            </label>
            <details>
              <summary>Config overrides (JSON)</summary>
              <label className="visually-hidden" htmlFor="config">
                Config overrides JSON
              </label>
              <textarea
                id="config"
                name="config"
                value={formState.config}
                onChange={(event) => handleChange('config', event.target.value)}
              />
            </details>
            <details>
              <summary>Environment overrides (JSON)</summary>
              <label className="visually-hidden" htmlFor="environment_overrides">
                Environment overrides JSON
              </label>
              <textarea
                id="environment_overrides"
                name="environment_overrides"
                value={formState.environment_overrides}
                onChange={(event) => handleChange('environment_overrides', event.target.value)}
              />
            </details>
            <details>
              <summary>Pipeline overrides (JSON)</summary>
              <label className="visually-hidden" htmlFor="pipeline_overrides">
                Pipeline overrides JSON
              </label>
              <textarea
                id="pipeline_overrides"
                name="pipeline_overrides"
                value={formState.pipeline_overrides}
                onChange={(event) => handleChange('pipeline_overrides', event.target.value)}
              />
            </details>
            <details>
              <summary>Book metadata (JSON)</summary>
              <label className="visually-hidden" htmlFor="book_metadata">
                Book metadata JSON
              </label>
              <textarea
                id="book_metadata"
                name="book_metadata"
                value={formState.book_metadata}
                onChange={(event) => handleChange('book_metadata', event.target.value)}
              />
            </details>
          </details>
        </fieldset>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Submitting…' : 'Submit job'}
        </button>
      </form>
      {activeFileDialog && fileOptions ? (
        <FileSelectionDialog
          title={activeFileDialog === 'input' ? 'Select ebook file' : 'Select output path'}
          description={
            activeFileDialog === 'input'
              ? 'Choose an EPUB file from the configured books directory.'
              : 'Select an existing output file or directory as the base path.'
          }
          files={activeFileDialog === 'input' ? fileOptions.ebooks : fileOptions.outputs}
          onSelect={(path) => {
            if (activeFileDialog === 'input') {
              handleInputFileChange(path);
            } else {
              handleChange('base_output_file', path);
            }
            setActiveFileDialog(null);
          }}
          onClose={() => setActiveFileDialog(null)}
        />
      ) : null}
    </section>
  );
}

export default PipelineSubmissionForm;
