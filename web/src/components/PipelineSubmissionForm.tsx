import { FormEvent, useState } from 'react';
import { PipelineRequestPayload } from '../api/dtos';

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
  target_languages: string;
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
  config: string;
  environment_overrides: string;
  pipeline_overrides: string;
  book_metadata: string;
};

const DEFAULT_FORM_STATE: FormState = {
  input_file: '',
  base_output_file: '',
  input_language: 'en',
  target_languages: 'es',
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
  config: '{}',
  environment_overrides: '{}',
  pipeline_overrides: '{}',
  book_metadata: '{}'
};

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

export function PipelineSubmissionForm({ onSubmit, isSubmitting = false }: Props) {
  const [formState, setFormState] = useState<FormState>(DEFAULT_FORM_STATE);
  const [error, setError] = useState<string | null>(null);

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setFormState((previous) => ({
      ...previous,
      [key]: value
    }));
  };

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

      const targetLanguages = formState.target_languages
        .split(',')
        .map((language) => language.trim())
        .filter(Boolean);

      const payload: PipelineRequestPayload = {
        config: json.config,
        environment_overrides: json.environment_overrides,
        pipeline_overrides: json.pipeline_overrides,
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
      <form onSubmit={handleSubmit}>
        <label htmlFor="input_file">Input file path</label>
        <input
          id="input_file"
          name="input_file"
          type="text"
          value={formState.input_file}
          onChange={(event) => handleChange('input_file', event.target.value)}
          placeholder="/path/to/input.txt"
          required
        />

        <label htmlFor="base_output_file">Base output file</label>
        <input
          id="base_output_file"
          name="base_output_file"
          type="text"
          value={formState.base_output_file}
          onChange={(event) => handleChange('base_output_file', event.target.value)}
          placeholder="ebook_output"
          required
        />

        <label htmlFor="input_language">Input language</label>
        <input
          id="input_language"
          name="input_language"
          type="text"
          value={formState.input_language}
          onChange={(event) => handleChange('input_language', event.target.value)}
          required
        />

        <label htmlFor="target_languages">Target languages (comma separated)</label>
        <input
          id="target_languages"
          name="target_languages"
          type="text"
          value={formState.target_languages}
          onChange={(event) => handleChange('target_languages', event.target.value)}
          placeholder="es, fr"
        />

        <label htmlFor="sentences_per_output_file">Sentences per output file</label>
        <input
          id="sentences_per_output_file"
          name="sentences_per_output_file"
          type="number"
          min={1}
          value={formState.sentences_per_output_file}
          onChange={(event) => handleChange('sentences_per_output_file', Number(event.target.value))}
        />

        <label htmlFor="start_sentence">Start sentence</label>
        <input
          id="start_sentence"
          name="start_sentence"
          type="number"
          min={1}
          value={formState.start_sentence}
          onChange={(event) => handleChange('start_sentence', Number(event.target.value))}
        />

        <label htmlFor="end_sentence">End sentence (optional)</label>
        <input
          id="end_sentence"
          name="end_sentence"
          type="number"
          min={formState.start_sentence}
          value={formState.end_sentence}
          onChange={(event) => handleChange('end_sentence', event.target.value)}
          placeholder="Leave blank to process the entire document"
        />

        <div>
          <label>
            <input
              type="checkbox"
              name="stitch_full"
              checked={formState.stitch_full}
              onChange={(event) => handleChange('stitch_full', event.target.checked)}
            />{' '}
            Stitch full document
          </label>
        </div>

        <div>
          <label>
            <input
              type="checkbox"
              name="generate_audio"
              checked={formState.generate_audio}
              onChange={(event) => handleChange('generate_audio', event.target.checked)}
            />{' '}
            Generate audio
          </label>
        </div>

        <label htmlFor="audio_mode">Audio mode</label>
        <input
          id="audio_mode"
          name="audio_mode"
          type="text"
          value={formState.audio_mode}
          onChange={(event) => handleChange('audio_mode', event.target.value)}
        />

        <label htmlFor="written_mode">Written mode</label>
        <input
          id="written_mode"
          name="written_mode"
          type="text"
          value={formState.written_mode}
          onChange={(event) => handleChange('written_mode', event.target.value)}
        />

        <label htmlFor="selected_voice">Selected voice</label>
        <input
          id="selected_voice"
          name="selected_voice"
          type="text"
          value={formState.selected_voice}
          onChange={(event) => handleChange('selected_voice', event.target.value)}
        />

        <div>
          <label>
            <input
              type="checkbox"
              name="output_html"
              checked={formState.output_html}
              onChange={(event) => handleChange('output_html', event.target.checked)}
            />{' '}
            Generate HTML output
          </label>
        </div>

        <div>
          <label>
            <input
              type="checkbox"
              name="output_pdf"
              checked={formState.output_pdf}
              onChange={(event) => handleChange('output_pdf', event.target.checked)}
            />{' '}
            Generate PDF output
          </label>
        </div>

        <div>
          <label>
            <input
              type="checkbox"
              name="generate_video"
              checked={formState.generate_video}
              onChange={(event) => handleChange('generate_video', event.target.checked)}
            />{' '}
            Generate video assets
          </label>
        </div>

        <div>
          <label>
            <input
              type="checkbox"
              name="include_transliteration"
              checked={formState.include_transliteration}
              onChange={(event) =>
                handleChange('include_transliteration', event.target.checked)
              }
            />{' '}
            Include transliteration
          </label>
        </div>

        <label htmlFor="tempo">Tempo</label>
        <input
          id="tempo"
          name="tempo"
          type="number"
          step="0.1"
          min={0.5}
          value={formState.tempo}
          onChange={(event) => handleChange('tempo', Number(event.target.value))}
        />

        <label htmlFor="config">Config overrides (JSON)</label>
        <textarea
          id="config"
          name="config"
          value={formState.config}
          onChange={(event) => handleChange('config', event.target.value)}
        />

        <label htmlFor="environment_overrides">Environment overrides (JSON)</label>
        <textarea
          id="environment_overrides"
          name="environment_overrides"
          value={formState.environment_overrides}
          onChange={(event) => handleChange('environment_overrides', event.target.value)}
        />

        <label htmlFor="pipeline_overrides">Pipeline overrides (JSON)</label>
        <textarea
          id="pipeline_overrides"
          name="pipeline_overrides"
          value={formState.pipeline_overrides}
          onChange={(event) => handleChange('pipeline_overrides', event.target.value)}
        />

        <label htmlFor="book_metadata">Book metadata (JSON)</label>
        <textarea
          id="book_metadata"
          name="book_metadata"
          value={formState.book_metadata}
          onChange={(event) => handleChange('book_metadata', event.target.value)}
        />

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Submitting…' : 'Submit job'}
        </button>
      </form>
    </section>
  );
}

export default PipelineSubmissionForm;
