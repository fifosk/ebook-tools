import { describe, expect, it } from 'vitest';
import type { JobParameterSnapshot, SubtitleSourceEntry } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import {
  isAssSubtitleSelection,
  pickLatestSubtitleSource,
  resolveSubtitleMetadataSourceName,
  resolveSubtitleSourceFormat,
  resolveSubtitleSourceSelectionAfterRefresh,
  selectMissingCompletedSubtitleJobs,
  sortSubtitleJobsNewestFirst,
  sortSubtitleSourcesForSelection,
  updateSubtitleMediaMetadataDraft,
  updateSubtitleMediaMetadataSection
} from '../subtitle-tool/subtitleToolUtils';
import { resolveSubtitleLanguageDefaults } from '../subtitle-tool/subtitleLanguageDefaultsUtils';
import { resolveSubtitlePrefillValues } from '../subtitle-tool/subtitlePrefillUtils';
import { formatSubmittedSubtitleSummary } from '../subtitle-tool/subtitleSubmitFeedbackUtils';
import {
  buildSubtitleSubmitFormData,
  normalizeSubtitleTimecodeInput,
  resolveSubtitleSubmitValues,
  type SubtitleSubmitInput
} from '../subtitle-tool/subtitleSubmitUtils';

function source(overrides: Partial<SubtitleSourceEntry>): SubtitleSourceEntry {
  return {
    name: overrides.name ?? overrides.path ?? 'source.srt',
    path: overrides.path ?? '/media/source.srt',
    format: overrides.format ?? 'srt',
    language: overrides.language ?? null,
    modified_at: overrides.modified_at ?? null
  };
}

function job(overrides: {
  jobId: string;
  jobType?: string;
  status?: string;
  createdAt?: string;
}): JobState {
  return {
    jobId: overrides.jobId,
    status: {
      job_id: overrides.jobId,
      job_type: overrides.jobType ?? 'subtitle',
      status: overrides.status ?? 'completed',
      created_at: overrides.createdAt ?? '2026-06-23T10:00:00Z',
      started_at: null,
      completed_at: null,
      result: null,
      error: null,
      latest_event: null,
      tuning: null
    } as JobState['status'],
    isReloading: false,
    isMutating: false,
    canManage: true
  };
}

describe('sortSubtitleSourcesForSelection', () => {
  it('keeps original relative order while moving generated ASS files after source subtitles', () => {
    const inputs = [
      source({ path: '/subtitles/generated.ass', format: 'ass' }),
      source({ path: '/subtitles/source.srt', format: 'srt' }),
      source({ path: '/subtitles/source.vtt', format: 'vtt' }),
      source({ path: '/subtitles/other.ass', format: 'ass' })
    ];

    expect(sortSubtitleSourcesForSelection(inputs).map((entry) => entry.path)).toEqual([
      '/subtitles/source.srt',
      '/subtitles/source.vtt',
      '/subtitles/generated.ass',
      '/subtitles/other.ass'
    ]);
  });

  it('uses the path extension when the backend entry has no format', () => {
    const inputs = [
      source({ path: '/subtitles/generated.ass', format: '' }),
      source({ path: '/subtitles/source.srt', format: '' })
    ];

    expect(sortSubtitleSourcesForSelection(inputs).map((entry) => entry.path)).toEqual([
      '/subtitles/source.srt',
      '/subtitles/generated.ass'
    ]);
  });
});

describe('source metadata helpers', () => {
  it('resolves source format from explicit format or file extension', () => {
    expect(resolveSubtitleSourceFormat(source({ path: '/a/generated.ass', format: '' }))).toBe('ass');
    expect(resolveSubtitleSourceFormat(source({ path: '/a/source.srt', format: 'VTT' }))).toBe('vtt');
    expect(resolveSubtitleSourceFormat(null)).toBe('');
  });

  it('flags generated ASS selections only for existing-source mode', () => {
    const ass = source({ path: '/a/generated.ass', format: 'ass' });

    expect(isAssSubtitleSelection('existing', ass)).toBe(true);
    expect(isAssSubtitleSelection('upload', ass)).toBe(false);
    expect(isAssSubtitleSelection('existing', source({ path: '/a/source.srt', format: 'srt' }))).toBe(false);
  });

  it('resolves metadata source names from upload files, selected names, or path basenames', () => {
    expect(
      resolveSubtitleMetadataSourceName({
        sourceMode: 'upload',
        uploadFileName: 'upload.srt',
        selectedSourcePath: '/ignored/source.srt'
      })
    ).toBe('upload.srt');
    expect(
      resolveSubtitleMetadataSourceName({
        sourceMode: 'existing',
        selectedSourceName: 'Friendly Source',
        selectedSourcePath: '/media/source.srt'
      })
    ).toBe('Friendly Source');
    expect(
      resolveSubtitleMetadataSourceName({
        sourceMode: 'existing',
        selectedSourcePath: '/media/fallback.srt'
      })
    ).toBe('fallback.srt');
  });
});

describe('metadata draft helpers', () => {
  it('copies the current draft before applying top-level metadata edits', () => {
    const current = {
      job_label: 'Original label',
      show: { name: 'Example Show' }
    };

    const next = updateSubtitleMediaMetadataDraft(current, (draft) => {
      draft['job_label'] = 'Updated label';
    });

    expect(next).toEqual({
      job_label: 'Updated label',
      show: { name: 'Example Show' }
    });
    expect(current).toEqual({
      job_label: 'Original label',
      show: { name: 'Example Show' }
    });
    expect(next).not.toBe(current);
  });

  it('creates a draft when editing metadata without an existing payload', () => {
    expect(
      updateSubtitleMediaMetadataDraft(null, (draft) => {
        draft['job_label'] = 'New label';
      })
    ).toEqual({
      job_label: 'New label'
    });
  });

  it('copies nested metadata sections before applying edits', () => {
    const episode = { season: 1, number: 2, name: 'Old title' };
    const current = {
      episode,
      show: { name: 'Example Show' }
    };

    const next = updateSubtitleMediaMetadataSection(current, 'episode', (section) => {
      section['name'] = 'New title';
      section['number'] = 3;
    });

    expect(next).toEqual({
      episode: { season: 1, number: 3, name: 'New title' },
      show: { name: 'Example Show' }
    });
    expect(current.episode).toBe(episode);
    expect(current.episode).toEqual({ season: 1, number: 2, name: 'Old title' });
    expect(next.episode).not.toBe(episode);
  });

  it('creates missing nested metadata sections', () => {
    expect(
      updateSubtitleMediaMetadataSection(null, 'show', (section) => {
        section['name'] = 'Example Show';
      })
    ).toEqual({
      show: { name: 'Example Show' }
    });
  });
});

describe('pickLatestSubtitleSource', () => {
  it('prefers the newest non-ASS source over a newer generated ASS subtitle', () => {
    const inputs = [
      source({
        path: '/subtitles/generated.ass',
        format: 'ass',
        modified_at: '2026-06-23T12:00:00Z'
      }),
      source({
        path: '/subtitles/source.srt',
        format: 'srt',
        modified_at: '2026-06-23T10:00:00Z'
      }),
      source({
        path: '/subtitles/source.vtt',
        format: 'vtt',
        modified_at: '2026-06-23T11:00:00Z'
      })
    ];

    expect(pickLatestSubtitleSource(inputs)).toBe('/subtitles/source.vtt');
  });

  it('falls back to ASS files when they are the only available subtitle sources', () => {
    const inputs = [
      source({
        path: '/subtitles/older.ass',
        format: 'ass',
        modified_at: '2026-06-23T09:00:00Z'
      }),
      source({
        path: '/subtitles/newer.ass',
        format: 'ass',
        modified_at: '2026-06-23T10:00:00Z'
      })
    ];

    expect(pickLatestSubtitleSource(inputs)).toBe('/subtitles/newer.ass');
  });

  it('uses lexical path order as a stable tie breaker', () => {
    const inputs = [
      source({ path: '/subtitles/z.srt', modified_at: '2026-06-23T10:00:00Z' }),
      source({ path: '/subtitles/a.srt', modified_at: '2026-06-23T10:00:00Z' })
    ];

    expect(pickLatestSubtitleSource(inputs)).toBe('/subtitles/a.srt');
  });

  it('returns an empty path when no sources are available', () => {
    expect(pickLatestSubtitleSource([])).toBe('');
  });
});

describe('resolveSubtitleSourceSelectionAfterRefresh', () => {
  it('keeps the current source when it is still available and selection was not reset', () => {
    const current = source({ path: '/subtitles/current.srt', modified_at: '2026-06-23T10:00:00Z' });
    const newer = source({ path: '/subtitles/newer.srt', modified_at: '2026-06-23T11:00:00Z' });

    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [current, newer],
        currentSelection: current.path,
        resetSelection: false,
      }),
    ).toBe(current.path);
  });

  it('chooses the latest source when selection is reset or stale', () => {
    const older = source({ path: '/subtitles/older.srt', modified_at: '2026-06-23T10:00:00Z' });
    const newer = source({ path: '/subtitles/newer.srt', modified_at: '2026-06-23T11:00:00Z' });

    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [older, newer],
        currentSelection: older.path,
        resetSelection: true,
      }),
    ).toBe(newer.path);
    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [older, newer],
        currentSelection: '/subtitles/deleted.srt',
        resetSelection: false,
      }),
    ).toBe(newer.path);
  });

  it('clears the selected source when refreshed sources are empty', () => {
    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [],
        currentSelection: '/subtitles/deleted.srt',
        resetSelection: true,
      }),
    ).toBe('');
  });
});

describe('formatSubmittedSubtitleSummary', () => {
  it('describes auto-detected submissions when no tuning details were captured', () => {
    expect(
      formatSubmittedSubtitleSummary({
        jobId: 'job-1',
        workerCount: null,
        batchSize: null,
        translationBatchSize: null,
        startTime: '00:00',
        defaultStartTime: '00:00',
        endTime: null,
        model: null,
        format: null,
        assFontSize: null,
        assEmphasis: null
      })
    ).toBe(
      'Submitted subtitle job job-1 using auto-detected concurrency. Live status appears in the Jobs tab.'
    );
  });

  it('joins tuning, clip window, model, and ASS settings in display order', () => {
    expect(
      formatSubmittedSubtitleSummary({
        jobId: 'job-2',
        workerCount: 4,
        batchSize: 20,
        translationBatchSize: 8,
        startTime: '01:02',
        defaultStartTime: '00:00',
        endTime: '+03:00',
        model: 'gpt-test',
        format: 'ass',
        assFontSize: 44,
        assEmphasis: 1.2
      })
    ).toBe(
      'Submitted subtitle job job-2 using 4 threads, batch size 20, LLM batch 8, starting at 01:02, ending after 03:00, LLM gpt-test, ASS subtitles, font size 44 and scale 1.2\u00d7. Live status appears in the Jobs tab.'
    );
  });

  it('uses singular thread and absolute end time labels', () => {
    expect(
      formatSubmittedSubtitleSummary({
        jobId: 'job-3',
        workerCount: 1,
        batchSize: null,
        translationBatchSize: null,
        startTime: '00:00',
        defaultStartTime: '00:00',
        endTime: '12:34',
        model: null,
        format: 'srt',
        assFontSize: null,
        assEmphasis: null
      })
    ).toBe(
      'Submitted subtitle job job-3 using 1 thread, ending at 12:34 and SRT subtitles. Live status appears in the Jobs tab.'
    );
  });
});

describe('resolveSubtitlePrefillValues', () => {
  it('maps subtitle rerun parameters into page-ready prefill values', () => {
    const parameters: JobParameterSnapshot = {
      target_languages: ['  French  ', 'German'],
      input_language: '  English ',
      enable_transliteration: false,
      show_original: false,
      worker_count: 4,
      batch_size: 20,
      translation_batch_size: 8,
      start_time_offset_seconds: 62,
      end_time_offset_seconds: 3723,
      llm_model: ' gpt-test ',
      translation_provider: ' llm ',
      transliteration_mode: ' custom ',
      transliteration_model: ' romanizer ',
      subtitle_path: ' /media/show.srt ',
      input_file: '/fallback/input.srt'
    };

    expect(resolveSubtitlePrefillValues(parameters)).toEqual({
      targetLanguage: 'French',
      inputLanguage: 'English',
      enableTransliteration: false,
      showOriginal: false,
      workerCount: 4,
      batchSize: 20,
      translationBatchSize: 8,
      startTime: '01:02',
      endTime: '01:02:03',
      selectedModel: 'gpt-test',
      translationProvider: 'llm',
      transliterationMode: 'custom',
      transliterationModel: 'romanizer',
      sourcePath: '/media/show.srt'
    });
  });

  it('falls back to input_file when subtitle_path is absent', () => {
    expect(
      resolveSubtitlePrefillValues({
        input_file: ' /media/fallback.srt '
      }).sourcePath
    ).toBe('/media/fallback.srt');
  });

  it('preserves subtitle_path precedence even when it trims to an empty value', () => {
    expect(
      resolveSubtitlePrefillValues({
        subtitle_path: ' ',
        input_file: '/media/fallback.srt'
      }).sourcePath
    ).toBeNull();
  });

  it('ignores blank strings, invalid target languages, and non-finite numbers', () => {
    const parameters = {
      target_languages: [' ', 42, '  Spanish  '],
      input_language: ' ',
      worker_count: Number.NaN,
      batch_size: Number.POSITIVE_INFINITY,
      translation_batch_size: Number.NEGATIVE_INFINITY,
      start_time_offset_seconds: -1,
      end_time_offset_seconds: null,
      llm_model: '',
      translation_provider: '   ',
      transliteration_mode: '',
      transliteration_model: '   '
    } as unknown as JobParameterSnapshot;

    expect(resolveSubtitlePrefillValues(parameters)).toMatchObject({
      targetLanguage: 'Spanish',
      inputLanguage: null,
      workerCount: null,
      batchSize: null,
      translationBatchSize: null,
      startTime: '',
      endTime: null,
      selectedModel: null,
      translationProvider: null,
      transliterationMode: null,
      transliterationModel: null,
      sourcePath: null
    });
  });

  it('returns empty prefill values when no snapshot is available', () => {
    expect(resolveSubtitlePrefillValues(null)).toEqual({
      targetLanguage: null,
      inputLanguage: null,
      enableTransliteration: null,
      showOriginal: null,
      workerCount: null,
      batchSize: null,
      translationBatchSize: null,
      startTime: null,
      endTime: null,
      selectedModel: null,
      translationProvider: null,
      transliterationMode: null,
      transliterationModel: null,
      sourcePath: null
    });
  });
});

describe('resolveSubtitleLanguageDefaults', () => {
  it('normalizes backend target languages and input language defaults', () => {
    expect(
      resolveSubtitleLanguageDefaults(
        {
          target_languages: [' fr ', 'German', '', 42],
          input_language: ' en '
        },
        ''
      )
    ).toEqual({
      fetchedLanguages: ['French', 'German'],
      inputLanguage: 'English'
    });
  });

  it('does not replace an existing input language preference', () => {
    expect(
      resolveSubtitleLanguageDefaults(
        {
          target_languages: ['French'],
          input_language: 'English'
        },
        'Spanish'
      )
    ).toEqual({
      fetchedLanguages: ['French'],
      inputLanguage: null
    });
  });

  it('returns empty defaults for missing or malformed config', () => {
    expect(resolveSubtitleLanguageDefaults({ target_languages: 'French' }, '')).toEqual({
      fetchedLanguages: [],
      inputLanguage: null
    });
    expect(resolveSubtitleLanguageDefaults(null, '')).toEqual({
      fetchedLanguages: [],
      inputLanguage: null
    });
  });
});

describe('normalizeSubtitleTimecodeInput', () => {
  it('normalizes MM:SS and HH:MM:SS absolute timecodes', () => {
    expect(normalizeSubtitleTimecodeInput('1:02')).toBe('01:02');
    expect(normalizeSubtitleTimecodeInput('1:02:03')).toBe('01:02:03');
  });

  it('normalizes relative minute and duration offsets when enabled', () => {
    expect(normalizeSubtitleTimecodeInput('+3', { allowRelative: true })).toBe('+03:00');
    expect(normalizeSubtitleTimecodeInput('+1:02:03', { allowRelative: true })).toBe('+01:02:03');
  });

  it('rejects invalid minute and second values', () => {
    expect(normalizeSubtitleTimecodeInput('99:99')).toBeNull();
    expect(normalizeSubtitleTimecodeInput('+99:99', { allowRelative: true })).toBeNull();
  });
});

const baseSubmitInput: SubtitleSubmitInput = {
  inputLanguage: ' English ',
  targetLanguage: ' French ',
  isAssSelection: false,
  sourceMode: 'existing' as const,
  selectedSource: ' /media/source.srt ',
  hasUploadFile: false,
  startTime: '1:02',
  endTime: '+3',
  outputFormat: 'ass' as const,
  assFontSize: 130,
  assEmphasis: 1.234,
  selectedModel: ' gpt-test ',
  translationProvider: ' llm ',
  transliterationMode: ' default ',
  transliterationModel: ' romanizer ',
  workerCount: 4,
  batchSize: 20,
  translationBatchSize: 8
};

describe('resolveSubtitleSubmitValues', () => {
  it('normalizes a valid existing-source ASS submission', () => {
    expect(resolveSubtitleSubmitValues(baseSubmitInput)).toEqual({
      ok: true,
      values: {
        originalLanguage: 'English',
        targetLanguage: 'French',
        normalizedStartTime: '01:02',
        normalizedEndTime: '+03:00',
        resolvedAssFontSize: 120,
        resolvedAssEmphasis: 1.23,
        selectedModel: 'gpt-test',
        translationProvider: 'llm',
        transliterationMode: 'default',
        transliterationModel: 'romanizer',
        sourcePath: '/media/source.srt',
        workerCount: 4,
        batchSize: 20,
        translationBatchSize: 8
      }
    });
  });

  it('accepts upload submissions and omits source path and non-positive tuning fields', () => {
    expect(
      resolveSubtitleSubmitValues({
        ...baseSubmitInput,
        sourceMode: 'upload',
        selectedSource: '',
        hasUploadFile: true,
        outputFormat: 'srt',
        assFontSize: '',
        assEmphasis: '',
        selectedModel: ' ',
        translationProvider: '',
        transliterationMode: ' ',
        transliterationModel: '',
        workerCount: 0,
        batchSize: -1,
        translationBatchSize: ''
      })
    ).toEqual({
      ok: true,
      values: {
        originalLanguage: 'English',
        targetLanguage: 'French',
        normalizedStartTime: '01:02',
        normalizedEndTime: '+03:00',
        resolvedAssFontSize: null,
        resolvedAssEmphasis: null,
        selectedModel: null,
        translationProvider: null,
        transliterationMode: null,
        transliterationModel: null,
        sourcePath: null,
        workerCount: null,
        batchSize: null,
        translationBatchSize: null
      }
    });
  });

  const invalidCases: Array<[Partial<SubtitleSubmitInput>, string]> = [
    [{ inputLanguage: ' ' }, 'Choose an original language.'],
    [
      { isAssSelection: true },
      'Generated ASS files cannot be used as sources. Choose the original SRT/VTT or upload a new subtitle.'
    ],
    [{ targetLanguage: ' ' }, 'Choose a target language.'],
    [{ selectedSource: ' ' }, 'Select a subtitle file to process.'],
    [
      { sourceMode: 'upload' as const, selectedSource: '', hasUploadFile: false },
      'Choose a subtitle file to upload.'
    ],
    [{ startTime: '99:99' }, 'Enter a valid start time in MM:SS or HH:MM:SS format.'],
    [{ endTime: '+99:99' }, 'Enter a valid end time in MM:SS, HH:MM:SS, or +offset format.'],
    [{ assFontSize: '' }, 'Enter a numeric ASS base font size.'],
    [{ assEmphasis: '' }, 'Enter a numeric ASS emphasis scale.']
  ];

  it.each(invalidCases)('returns %s for invalid submit input', (overrides, expectedError) => {
    expect(resolveSubtitleSubmitValues({ ...baseSubmitInput, ...overrides })).toEqual({
      ok: false,
      error: expectedError
    });
  });

  it('clamps ASS typography values to the supported range', () => {
    const low = resolveSubtitleSubmitValues({
      ...baseSubmitInput,
      assFontSize: 1,
      assEmphasis: 0.2
    });
    expect(low).toMatchObject({
      ok: true,
      values: {
        resolvedAssFontSize: 12,
        resolvedAssEmphasis: 1
      }
    });

    const high = resolveSubtitleSubmitValues({
      ...baseSubmitInput,
      assFontSize: 500,
      assEmphasis: 9
    });
    expect(high).toMatchObject({
      ok: true,
      values: {
        resolvedAssFontSize: 120,
        resolvedAssEmphasis: 2.5
      }
    });
  });
});

describe('buildSubtitleSubmitFormData', () => {
  it('builds the existing-source subtitle payload with optional tuning and metadata fields', () => {
    const resolved = resolveSubtitleSubmitValues(baseSubmitInput);
    if (!resolved.ok) {
      throw new Error(resolved.error);
    }

    const formData = buildSubtitleSubmitFormData({
      values: resolved.values,
      enableTransliteration: true,
      enableHighlight: false,
      showOriginal: true,
      generateAudioBook: false,
      outputFormat: 'ass',
      mirrorToSourceDir: true,
      mediaMetadataDraft: {
        tv: { series: 'Example Show' },
        title: 'Episode title'
      }
    });

    expect(Object.fromEntries(formData.entries())).toMatchObject({
      input_language: 'English',
      original_language: 'English',
      target_language: 'French',
      enable_transliteration: 'true',
      highlight: 'false',
      show_original: 'true',
      generate_audio_book: 'false',
      output_format: 'ass',
      mirror_batches_to_source_dir: 'true',
      start_time: '01:02',
      end_time: '+03:00',
      ass_font_size: '120',
      ass_emphasis_scale: '1.23',
      llm_model: 'gpt-test',
      translation_provider: 'llm',
      transliteration_mode: 'default',
      transliteration_model: 'romanizer',
      source_path: '/media/source.srt',
      worker_count: '4',
      batch_size: '20',
      translation_batch_size: '8',
      media_metadata_json: JSON.stringify({
        tv: { series: 'Example Show' },
        title: 'Episode title'
      })
    });
    expect(formData.has('file')).toBe(false);
  });

  it('builds upload payloads with a file and omits blank optional fields', () => {
    const resolved = resolveSubtitleSubmitValues({
      ...baseSubmitInput,
      sourceMode: 'upload',
      selectedSource: '',
      hasUploadFile: true,
      outputFormat: 'srt',
      assFontSize: '',
      assEmphasis: '',
      selectedModel: '',
      translationProvider: '',
      transliterationMode: '',
      transliterationModel: '',
      workerCount: '',
      batchSize: '',
      translationBatchSize: '',
      endTime: ''
    });
    if (!resolved.ok) {
      throw new Error(resolved.error);
    }
    const upload = new File(['1\n00:00:01,000 --> 00:00:02,000\nHi'], 'upload.srt', {
      type: 'text/plain'
    });

    const formData = buildSubtitleSubmitFormData({
      values: resolved.values,
      enableTransliteration: false,
      enableHighlight: true,
      showOriginal: false,
      generateAudioBook: true,
      outputFormat: 'srt',
      mirrorToSourceDir: false,
      uploadFile: upload
    });

    expect(Object.fromEntries(formData.entries())).toMatchObject({
      input_language: 'English',
      original_language: 'English',
      target_language: 'French',
      enable_transliteration: 'false',
      highlight: 'true',
      show_original: 'false',
      generate_audio_book: 'true',
      output_format: 'srt',
      mirror_batches_to_source_dir: 'false',
      start_time: '01:02'
    });
    expect(formData.has('source_path')).toBe(false);
    expect(formData.has('end_time')).toBe(false);
    expect(formData.has('llm_model')).toBe(false);
    expect(formData.has('ass_font_size')).toBe(false);
    expect(formData.has('worker_count')).toBe(false);
    expect((formData.get('file') as File | null)?.name).toBe('upload.srt');
  });
});

describe('subtitle job helpers', () => {
  it('selects completed subtitle jobs that are missing cached result payloads', () => {
    const jobs = [
      job({ jobId: 'ready-missing' }),
      job({ jobId: 'ready-cached' }),
      job({ jobId: 'running', status: 'running' }),
      job({ jobId: 'book', jobType: 'book' })
    ];

    expect(selectMissingCompletedSubtitleJobs(jobs, { 'ready-cached': { ok: true } }).map((entry) => entry.jobId)).toEqual([
      'ready-missing'
    ]);
  });

  it('sorts subtitle jobs newest first without mutating the input array', () => {
    const oldest = job({ jobId: 'oldest', createdAt: '2026-06-23T09:00:00Z' });
    const newest = job({ jobId: 'newest', createdAt: '2026-06-23T11:00:00Z' });
    const middle = job({ jobId: 'middle', createdAt: '2026-06-23T10:00:00Z' });
    const input = [oldest, newest, middle];

    expect(sortSubtitleJobsNewestFirst(input).map((entry) => entry.jobId)).toEqual([
      'newest',
      'middle',
      'oldest'
    ]);
    expect(input.map((entry) => entry.jobId)).toEqual(['oldest', 'newest', 'middle']);
  });
});
