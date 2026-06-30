import { useEffect, useMemo, useRef, useState } from 'react';
import type { CreationTemplateEntry, PipelineRequestPayload, PipelineStatusResponse } from '../api/dtos';
import {
  fetchBookCreationOptions,
  submitBookJob,
  type BookCreationOptionsResponse,
} from '../api/createBook';
import BookNarrationForm from '../components/book-narration/BookNarrationForm';
import type { BookNarrationSentenceSplitterOption } from '../components/book-narration/bookNarrationFormTypes';
import { buildHandoffPayloadExtras } from '../utils/creationTemplatePayloadExtras';
import {
  buildBookGenerationJobRequest,
  buildGeneratedSourceImageDefaults,
  buildGeneratedSourcePipelineDefaults,
  DEFAULT_GENERATOR_STATE,
  deriveBaseOutputName,
  extractGeneratedBookTemplateGeneratorState,
  FALLBACK_SENTENCE_BOUNDS,
  normalizeSentenceCount,
  resolveGeneratorDefaults,
  type GeneratorEditedField,
  type GeneratorFormState
} from './create-book/createBookPageUtils';

interface CreateBookPageProps {
  onJobSubmitted?: (jobId: string) => void;
  recentJobs?: PipelineStatusResponse[] | null;
  creationTemplate?: CreationTemplateEntry | null;
  creationTemplateError?: string | null;
  creationTemplateHandoffSource?: string | null;
  isLoadingCreationTemplate?: boolean;
}

export default function CreateBookPage({
  onJobSubmitted,
  recentJobs = null,
  creationTemplate = null,
  creationTemplateError = null,
  creationTemplateHandoffSource = null,
  isLoadingCreationTemplate = false
}: CreateBookPageProps) {
  const [generatorState, setGeneratorState] = useState<GeneratorFormState>(DEFAULT_GENERATOR_STATE);
  const editedGeneratorFieldsRef = useRef<Set<GeneratorEditedField>>(new Set());
  const appliedCreationTemplateRef = useRef<string | null>(null);
  const [creationOptions, setCreationOptions] = useState<BookCreationOptionsResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [latestJobId, setLatestJobId] = useState<string | null>(null);
  const sentenceBounds = creationOptions?.sentence_bounds ?? FALLBACK_SENTENCE_BOUNDS;
  const forcedBaseOutput = useMemo(
    () => deriveBaseOutputName(generatorState.book_name || generatorState.topic || 'generated-book'),
    [generatorState.book_name, generatorState.topic]
  );
  const generatedSourceImageDefaults = useMemo(
    () => buildGeneratedSourceImageDefaults(creationOptions),
    [creationOptions]
  );
  const generatedSourcePipelineDefaults = useMemo(
    () => buildGeneratedSourcePipelineDefaults(creationOptions),
    [creationOptions]
  );
  const sentenceSplitterOptions = useMemo<BookNarrationSentenceSplitterOption[] | null>(
    () =>
      creationOptions?.sentence_splitter_capabilities?.supported_modes.map((mode) => ({
        id: mode.id,
        label: mode.label,
      })) ?? null,
    [creationOptions]
  );
  const templatePayloadExtras = useMemo(() => ({
    ...(buildHandoffPayloadExtras(creationTemplateHandoffSource) ?? {}),
    generator_state: generatorState
  }), [creationTemplateHandoffSource, generatorState]);

  useEffect(() => {
    let cancelled = false;
    fetchBookCreationOptions()
      .then((options) => {
        if (cancelled) {
          return;
        }
        setCreationOptions(options);
        setGeneratorState((previous) => {
          return resolveGeneratorDefaults({
            previous,
            options,
            editedFields: editedGeneratorFieldsRef.current
          });
        });
      })
      .catch(() => {
        if (!cancelled) {
          setCreationOptions(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!creationTemplate) {
      appliedCreationTemplateRef.current = null;
      return;
    }
    const applyKey = `${creationTemplate.id}:${creationTemplate.updated_at}`;
    if (appliedCreationTemplateRef.current === applyKey) {
      return;
    }
    const templateGeneratorState = extractGeneratedBookTemplateGeneratorState(
      creationTemplate,
      sentenceBounds
    );
    if (!templateGeneratorState) {
      appliedCreationTemplateRef.current = applyKey;
      return;
    }
    for (const key of Object.keys(templateGeneratorState) as GeneratorEditedField[]) {
      editedGeneratorFieldsRef.current.add(key);
    }
    setGeneratorState((previous) => ({
      ...previous,
      ...templateGeneratorState
    }));
    appliedCreationTemplateRef.current = applyKey;
  }, [creationTemplate, sentenceBounds]);

  const updateGenerator = <Key extends keyof GeneratorFormState>(
    key: Key,
    value: GeneratorFormState[Key]
  ) => {
    editedGeneratorFieldsRef.current.add(key);
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
    return normalizeSentenceCount(value, sentenceBounds);
  };

  const handleSubmit = async (pipelinePayload: PipelineRequestPayload) => {
    setSubmitError(null);
    setSuccessMessage(null);
    setLatestJobId(null);

    const trimmedTopic = generatorState.topic.trim();
    const trimmedBookName = generatorState.book_name.trim();
    const trimmedGenre = generatorState.genre.trim();

    if (!trimmedTopic || !trimmedBookName || !trimmedGenre) {
      setSubmitError('Topic, book name, and genre are required to generate an audiobook.');
      return;
    }

    const payload = buildBookGenerationJobRequest({
      generatorState,
      pipelinePayload,
      sentenceBounds,
      forcedBaseOutput
    });

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
          min={sentenceBounds.min}
          max={sentenceBounds.max}
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
      <BookNarrationForm
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        externalError={submitError}
        recentJobs={recentJobs}
        sourceMode="generated"
        submitLabel="Generate & process"
        forcedBaseOutputFile={forcedBaseOutput}
        defaultImageSettings={generatedSourceImageDefaults}
        defaultPipelineSettings={generatedSourcePipelineDefaults}
        creationTemplate={creationTemplate}
        creationTemplateError={creationTemplateError}
        isLoadingCreationTemplate={isLoadingCreationTemplate}
        templatePayloadExtras={templatePayloadExtras}
        supportedInputLanguages={creationOptions?.supported_input_languages ?? null}
        supportedTargetLanguages={creationOptions?.supported_output_languages ?? null}
        sentenceSplitterOptions={sentenceSplitterOptions}
        customSourceSection={bookPromptSection}
        showInfoHeader={false}
        sectionOverrides={{
          source: {
            title: 'Source',
            description: 'Use this prompt as the source material for the generated EPUB.'
          }
        }}
      />
    </div>
  );
}
