import { FormEvent, useEffect, useMemo, useState } from 'react';
import { createBook, type CreateBookPayload, type BookCreationResponse } from '../api/createBook';
import { fetchVoiceInventory } from '../api/client';
import type { MacOSVoice, VoiceInventoryResponse } from '../api/dtos';
import { VOICE_OPTIONS } from '../constants/menuOptions';
import { useLanguagePreferences } from '../context/LanguageProvider';

type VoiceOption = {
  value: string;
  label: string;
};

interface CreateBookPageProps {
  onCreated?: (result: BookCreationResponse) => void;
}

interface FormState {
  input_language: string;
  output_language: string;
  voice: string;
  num_sentences: number;
  topic: string;
  book_name: string;
  genre: string;
  author: string;
}

const INITIAL_FORM_STATE: FormState = {
  input_language: 'English',
  output_language: 'Arabic',
  voice: '',
  num_sentences: 10,
  topic: '',
  book_name: '',
  genre: '',
  author: 'Me'
};

function capitalize(value: string | undefined | null): string | undefined {
  if (!value) {
    return undefined;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${capitalize(voice.gender)}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const descriptors: string[] = [voice.lang];
  if (voice.gender) {
    descriptors.push(capitalize(voice.gender) ?? '');
  }
  if (voice.quality) {
    descriptors.push(voice.quality);
  }
  const metadata = descriptors.length > 0 ? ` (${descriptors.filter(Boolean).join(', ')})` : '';
  return `${voice.name}${metadata}`;
}

function buildVoiceOptionsFromInventory(inventory: VoiceInventoryResponse | null): VoiceOption[] {
  if (!inventory) {
    return [];
  }

  const options: VoiceOption[] = [];
  inventory.macos
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((voice) => {
      options.push({
        value: formatMacOSVoiceIdentifier(voice),
        label: formatMacOSVoiceLabel(voice)
      });
    });

  return options;
}

export default function CreateBookPage({ onCreated }: CreateBookPageProps) {
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    primaryTargetLanguage,
    setPrimaryTargetLanguage
  } = useLanguagePreferences();
  const [formState, setFormState] = useState<FormState>(() => ({
    ...INITIAL_FORM_STATE,
    input_language: sharedInputLanguage ?? INITIAL_FORM_STATE.input_language,
    output_language:
      primaryTargetLanguage ?? INITIAL_FORM_STATE.output_language
  }));
  const [voiceOptions, setVoiceOptions] = useState<VoiceOption[]>(() =>
    VOICE_OPTIONS.map(({ value, label }) => ({ value, label }))
  );
  const [voiceInventoryError, setVoiceInventoryError] = useState<string | null>(null);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [result, setResult] = useState<BookCreationResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loadVoices = async () => {
      setIsLoadingVoices(true);
      try {
        const inventory = await fetchVoiceInventory();
        if (cancelled) {
          return;
        }
        const additional = buildVoiceOptionsFromInventory(inventory);
        setVoiceOptions((previous) => {
          const merged = new Map<string, VoiceOption>();
          for (const option of [...previous, ...additional]) {
            merged.set(option.value, option);
          }
          return Array.from(merged.values()).sort((a, b) => a.label.localeCompare(b.label));
        });
        setVoiceInventoryError(null);
      } catch (voiceError) {
        if (!cancelled) {
          const message =
            voiceError instanceof Error
              ? voiceError.message
              : 'Unable to load voice inventory.';
          setVoiceInventoryError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingVoices(false);
        }
      }
    };

    void loadVoices();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setFormState((previous) => {
      if (previous.input_language === sharedInputLanguage) {
        return previous;
      }
      return {
        ...previous,
        input_language: sharedInputLanguage
      };
    });
  }, [sharedInputLanguage]);

  useEffect(() => {
    const nextOutput = primaryTargetLanguage ?? '';
    setFormState((previous) => {
      if (previous.output_language === nextOutput) {
        return previous;
      }
      return {
        ...previous,
        output_language: nextOutput
      };
    });
  }, [primaryTargetLanguage]);

  const sortedVoiceOptions = useMemo(() => {
    return voiceOptions.slice().sort((a, b) => a.label.localeCompare(b.label));
  }, [voiceOptions]);

  const handleChange = <Key extends keyof FormState>(key: Key, value: FormState[Key]) => {
    setFormState((previous) => {
      if (previous[key] === value) {
        return previous;
      }
      return {
        ...previous,
        [key]: value
      };
    });

    if (key === 'input_language' && typeof value === 'string') {
      setSharedInputLanguage(value);
    } else if (key === 'output_language' && typeof value === 'string') {
      setPrimaryTargetLanguage(value);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setResult(null);

    const trimmed: CreateBookPayload = {
      input_language: formState.input_language.trim(),
      output_language: formState.output_language.trim(),
      voice: formState.voice ? formState.voice : null,
      num_sentences: Math.max(1, Math.min(500, Number(formState.num_sentences) || 1)),
      topic: formState.topic.trim(),
      book_name: formState.book_name.trim(),
      genre: formState.genre.trim(),
      author: formState.author.trim() || 'Me'
    };

    if (!trimmed.topic || !trimmed.book_name || !trimmed.genre) {
      setError('Topic, book name, and genre are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await createBook(trimmed);
      setSuccessMessage('Seed EPUB prepared successfully.');
      setResult(response);
      onCreated?.(response);
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : 'Unable to prepare the seed EPUB.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="create-book-page">
      <h2>Create a book</h2>
      <p>Generate a seed EPUB by asking the language model for source sentences, then refine the pipeline settings before submitting the job.</p>
      {successMessage ? (
        <div className="form-callout form-callout--success" role="status">
          <p style={{ margin: 0, fontWeight: 600 }}>{successMessage}</p>
          {result?.messages?.length ? (
            <ul style={{ marginTop: '0.5rem', marginBottom: 0, paddingLeft: '1.25rem' }}>
              {result.messages.map((message, index) => (
                <li key={`${message}-${index}`}>{message}</li>
              ))}
            </ul>
          ) : null}
          {result?.epub_path ? (
            <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
              <strong>Seed EPUB:</strong> {result.epub_path}
            </p>
          ) : null}
          {result?.input_file ? (
            <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
              <strong>Full path:</strong> {result.input_file}
            </p>
          ) : null}
          {result?.sentences_preview?.length ? (
            <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
              <strong>Example sentences:</strong> {result.sentences_preview.join(' ')}
            </p>
          ) : null}
        </div>
      ) : null}
      {result?.warnings?.length ? (
        <div className="form-callout form-callout--warning" role="alert">
          <p style={{ margin: 0, fontWeight: 600 }}>Warnings</p>
          <ul style={{ marginTop: '0.5rem', marginBottom: 0, paddingLeft: '1.25rem' }}>
            {result.warnings.map((message, index) => (
              <li key={`${message}-${index}`}>{message}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {error ? (
        <p className="form-help-text form-help-text--error" role="alert">
          {error}
        </p>
      ) : null}
      <form className="pipeline-form" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="create-book-input-language">Input language</label>
          <input
            id="create-book-input-language"
            type="text"
            value={formState.input_language}
            onChange={(event) => handleChange('input_language', event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="create-book-output-language">Output language</label>
          <input
            id="create-book-output-language"
            type="text"
            value={formState.output_language}
            onChange={(event) => handleChange('output_language', event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="create-book-voice">
            Voice
            {isLoadingVoices ? (
              <span className="form-help-text"> Loading voices…</span>
            ) : null}
          </label>
          <select
            id="create-book-voice"
            value={formState.voice}
            onChange={(event) => handleChange('voice', event.target.value)}
          >
            <option value="">Default (pipeline configuration)</option>
            {sortedVoiceOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {voiceInventoryError ? (
            <p className="form-help-text form-help-text--error" role="alert">
              {voiceInventoryError}
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor="create-book-sentences">Number of sentences</label>
          <input
            id="create-book-sentences"
            type="number"
            min={1}
            max={500}
            value={formState.num_sentences}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isNaN(next)) {
                return;
              }
              handleChange('num_sentences', next);
            }}
          />
        </div>
        <div>
          <label htmlFor="create-book-topic">Topic</label>
          <input
            id="create-book-topic"
            type="text"
            value={formState.topic}
            onChange={(event) => handleChange('topic', event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="create-book-name">Book name</label>
          <input
            id="create-book-name"
            type="text"
            value={formState.book_name}
            onChange={(event) => handleChange('book_name', event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="create-book-genre">Genre</label>
          <input
            id="create-book-genre"
            type="text"
            value={formState.genre}
            onChange={(event) => handleChange('genre', event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="create-book-author">Author</label>
          <input
            id="create-book-author"
            type="text"
            value={formState.author}
            onChange={(event) => handleChange('author', event.target.value)}
          />
        </div>
        <div>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Generating…' : 'Generate book'}
          </button>
        </div>
      </form>
    </section>
  );
}
