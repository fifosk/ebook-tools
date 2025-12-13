import { useMemo, useState } from 'react';
import type { PipelineRequestPayload, PipelineStatusResponse } from '../api/dtos';
import { submitBookJob, type BookGenerationJobRequest } from '../api/createBook';
import PipelineSubmissionForm from '../components/PipelineSubmissionForm';

type GeneratorFormState = {
  topic: string;
  book_name: string;
  genre: string;
  author: string;
  num_sentences: number;
};

interface CreateBookPageProps {
  onJobSubmitted?: (jobId: string) => void;
  recentJobs?: PipelineStatusResponse[] | null;
}

const DEFAULT_GENERATOR_STATE: GeneratorFormState = {
  topic: '',
  book_name: '',
  genre: '',
  author: 'Me',
  num_sentences: 30
};

function deriveBaseOutputName(value: string): string {
  const withoutExtension = value.replace(/\.[^/.]+$/, '');
  const normalized = withoutExtension
    .trim()
    .replace(/[^A-Za-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
  if (normalized) {
    return normalized;
  }
  if (withoutExtension.trim()) {
    return withoutExtension.trim();
  }
  return 'generated-book';
}

export default function CreateBookPage({ onJobSubmitted, recentJobs = null }: CreateBookPageProps) {
  const [generatorState, setGeneratorState] = useState<GeneratorFormState>(DEFAULT_GENERATOR_STATE);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [latestJobId, setLatestJobId] = useState<string | null>(null);
  const forcedBaseOutput = useMemo(
    () => deriveBaseOutputName(generatorState.book_name || generatorState.topic || 'generated-book'),
    [generatorState.book_name, generatorState.topic]
  );

  const updateGenerator = <Key extends keyof GeneratorFormState>(
    key: Key,
    value: GeneratorFormState[Key]
  ) => {
    setGeneratorState((previous) => {
      if (previous[key] === value) {
        return previous;
      }
      return {
        ...previous,
        [key]: value
      };
    });
  };

  const normalizeSentences = (value: number): number => {
    const coerced = Number.isFinite(value) ? value : DEFAULT_GENERATOR_STATE.num_sentences;
    return Math.max(1, Math.min(500, Math.trunc(coerced)));
  };

  const handleSubmit = async (pipelinePayload: PipelineRequestPayload) => {
    setSubmitError(null);
    setSuccessMessage(null);
    setLatestJobId(null);

    const trimmedTopic = generatorState.topic.trim();
    const trimmedBookName = generatorState.book_name.trim();
    const trimmedGenre = generatorState.genre.trim();
    const trimmedAuthor = generatorState.author.trim() || 'Me';
    const sentenceCount = normalizeSentences(generatorState.num_sentences);

    if (!trimmedTopic || !trimmedBookName || !trimmedGenre) {
      setSubmitError('Topic, book name, and genre are required to generate an audiobook.');
      return;
    }

    const generatorPayload: BookGenerationJobRequest['generator'] = {
      topic: trimmedTopic,
      book_name: trimmedBookName,
      genre: trimmedGenre,
      author: trimmedAuthor,
      num_sentences: sentenceCount,
      input_language: pipelinePayload.inputs.input_language,
      output_language:
        (pipelinePayload.inputs.target_languages && pipelinePayload.inputs.target_languages[0]) ||
        pipelinePayload.inputs.input_language,
      voice: pipelinePayload.inputs.selected_voice || null
    };

    const normalizedBaseOutput = deriveBaseOutputName(trimmedBookName || trimmedTopic || forcedBaseOutput);

    const payload: BookGenerationJobRequest = {
      generator: generatorPayload,
      pipeline: {
        ...pipelinePayload,
        inputs: {
          ...pipelinePayload.inputs,
          base_output_file: normalizedBaseOutput
        }
      }
    };

    setIsSubmitting(true);
    try {
      const response = await submitBookJob(payload);
      setSuccessMessage('Audiobook generation job enqueued successfully.');
      setLatestJobId(response.job_id);
      if (response.job_id) {
        onJobSubmitted?.(response.job_id);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to submit book job.';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const bookPromptSection = (
    <section className="pipeline-card" aria-labelledby="book-prompt-section">
      <header className="pipeline-card__header">
        <h3 id="book-prompt-section">Book prompt</h3>
        <p>Describe the story you want the model to write before narration starts.</p>
      </header>
      <div className="pipeline-card__body">
        <label htmlFor="book-topic">Topic</label>
        <input
          id="book-topic"
          type="text"
          value={generatorState.topic}
          onChange={(event) => updateGenerator('topic', event.target.value)}
          placeholder="A detective solving a mystery in Cairo"
          required
        />
        <label htmlFor="book-name">Book name</label>
        <input
          id="book-name"
          type="text"
          value={generatorState.book_name}
          onChange={(event) => updateGenerator('book_name', event.target.value)}
          placeholder="The Cairo Cipher"
          required
        />
        <label htmlFor="book-genre">Genre</label>
        <input
          id="book-genre"
          type="text"
          value={generatorState.genre}
          onChange={(event) => updateGenerator('genre', event.target.value)}
          placeholder="Mystery thriller"
          required
        />
        <label htmlFor="book-author">Author</label>
        <input
          id="book-author"
          type="text"
          value={generatorState.author}
          onChange={(event) => updateGenerator('author', event.target.value)}
          placeholder="Me"
        />
        <label htmlFor="book-sentences">Number of sentences</label>
        <input
          id="book-sentences"
          type="number"
          min={1}
          max={500}
          value={generatorState.num_sentences}
          onChange={(event) => {
            const next = Number(event.target.value);
            if (Number.isNaN(next)) {
              return;
            }
            updateGenerator('num_sentences', normalizeSentences(next));
          }}
        />
      </div>
    </section>
  );

  return (
    <div className="create-book-page">
      {successMessage ? (
        <div className="form-callout form-callout--success" role="status">
          <p style={{ margin: 0, fontWeight: 600 }}>{successMessage}</p>
          {latestJobId ? <p style={{ margin: '0.25rem 0 0 0' }}>Job {latestJobId}</p> : null}
        </div>
      ) : null}
      <PipelineSubmissionForm
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        externalError={submitError}
        recentJobs={recentJobs}
        sourceMode="generated"
        submitLabel="Generate & process"
        forcedBaseOutputFile={forcedBaseOutput}
        customSourceSection={bookPromptSection}
        showInfoHeader={false}
        sectionOverrides={{
          source: {
            title: 'Book prompt',
            description: 'Use this prompt as the source material for the generated EPUB.'
          }
        }}
      />
    </div>
  );
}
