import { act, renderHook } from '@testing-library/react';
import type { FormEvent } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { submitSubtitleJob } from '../../api/client';
import { useSubtitleSubmit } from '../subtitle-tool/useSubtitleSubmit';

vi.mock('../../api/client', () => ({
  submitSubtitleJob: vi.fn()
}));

const mockSubmitSubtitleJob = vi.mocked(submitSubtitleJob);

function submitEvent(): FormEvent<HTMLFormElement> {
  return {
    preventDefault: vi.fn()
  } as unknown as FormEvent<HTMLFormElement>;
}

function baseOptions() {
  return {
    inputLanguage: 'en',
    targetLanguage: 'es',
    isAssSelection: false,
    sourceMode: 'existing' as const,
    selectedSource: '/media/source.srt',
    startTime: '00:00',
    endTime: '',
    outputFormat: 'srt' as const,
    assFontSize: '' as const,
    assEmphasis: '' as const,
    selectedModel: '',
    translationProvider: '',
    transliterationMode: '',
    transliterationModel: '',
    workerCount: 4,
    batchSize: 16,
    translationBatchSize: 8,
    enableTransliteration: true,
    enableHighlight: false,
    showOriginal: true,
    generateAudioBook: false,
    mirrorToSourceDir: true,
    uploadFile: null,
    mediaMetadataDraft: { job_label: 'Pilot' } as Record<string, unknown>,
    isIntakeAtCapacity: false,
    setSubmitError: vi.fn(),
    beginSubmit: vi.fn(),
    finishSubmit: vi.fn(),
    rejectAtCapacity: vi.fn(),
    failSubmit: vi.fn(),
    recordSubmission: vi.fn(),
    setStartTime: vi.fn(),
    setEndTime: vi.fn(),
    setAssFontSize: vi.fn(),
    setAssEmphasis: vi.fn(),
    setActiveTab: vi.fn(),
    onJobCreated: vi.fn(),
    clearUploadFile: vi.fn(),
    refreshIntakeStatus: vi.fn().mockResolvedValue(undefined)
  };
}

describe('useSubtitleSubmit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitSubtitleJob.mockResolvedValue({
      job_id: 'subtitle-job-1',
      status: 'pending',
      created_at: '2026-06-23T12:00:00Z',
      job_type: 'subtitle'
    });
  });

  it('rejects submissions while intake is at capacity', async () => {
    const options = { ...baseOptions(), isIntakeAtCapacity: true };
    const { result } = renderHook(() => useSubtitleSubmit(options));
    const event = submitEvent();

    await act(async () => {
      await result.current.handleSubmit(event);
    });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(options.setSubmitError).toHaveBeenCalledWith(null);
    expect(options.rejectAtCapacity).toHaveBeenCalled();
    expect(options.beginSubmit).not.toHaveBeenCalled();
    expect(mockSubmitSubtitleJob).not.toHaveBeenCalled();
  });

  it('surfaces validation errors before starting the backend request', async () => {
    const options = { ...baseOptions(), inputLanguage: '' };
    const { result } = renderHook(() => useSubtitleSubmit(options));

    await act(async () => {
      await result.current.handleSubmit(submitEvent());
    });

    expect(options.setSubmitError).toHaveBeenLastCalledWith('Choose an original language.');
    expect(options.beginSubmit).not.toHaveBeenCalled();
    expect(mockSubmitSubtitleJob).not.toHaveBeenCalled();
  });

  it('submits form data, records feedback, normalizes fields, and refreshes intake state', async () => {
    const options = {
      ...baseOptions(),
      startTime: '1:02',
      endTime: '+5',
      outputFormat: 'ass' as const,
      assFontSize: 999,
      assEmphasis: 0.05
    };
    const { result } = renderHook(() => useSubtitleSubmit(options));

    await act(async () => {
      await result.current.handleSubmit(submitEvent());
    });

    expect(options.beginSubmit).toHaveBeenCalled();
    expect(mockSubmitSubtitleJob).toHaveBeenCalledTimes(1);
    const formData = mockSubmitSubtitleJob.mock.calls[0][0];
    expect(formData.get('source_path')).toBe('/media/source.srt');
    expect(formData.get('start_time')).toBe('01:02');
    expect(formData.get('end_time')).toBe('+05:00');
    expect(formData.get('ass_font_size')).toBe('120');
    expect(formData.get('ass_emphasis_scale')).toBe('1');
    expect(formData.get('media_metadata_json')).toBe('{"job_label":"Pilot"}');
    expect(options.recordSubmission).toHaveBeenCalledWith(
      expect.objectContaining({
        response: expect.objectContaining({ job_id: 'subtitle-job-1' }),
        workerCount: 4,
        batchSize: 16,
        translationBatchSize: 8,
        outputFormat: 'ass'
      })
    );
    expect(options.setStartTime).toHaveBeenCalledWith('01:02');
    expect(options.setEndTime).toHaveBeenCalledWith('+05:00');
    expect(options.setAssFontSize).toHaveBeenCalledWith(120);
    expect(options.setAssEmphasis).toHaveBeenCalledWith(1);
    expect(options.onJobCreated).toHaveBeenCalledWith('subtitle-job-1');
    expect(options.setActiveTab).toHaveBeenCalledWith('jobs');
    expect(options.refreshIntakeStatus).toHaveBeenCalled();
    expect(options.finishSubmit).toHaveBeenCalled();
  });

  it('routes backend failures through submit status cleanup', async () => {
    const failure = new Error('backend unavailable');
    mockSubmitSubtitleJob.mockRejectedValue(failure);
    const options = baseOptions();
    const { result } = renderHook(() => useSubtitleSubmit(options));

    await act(async () => {
      await result.current.handleSubmit(submitEvent());
    });

    expect(options.beginSubmit).toHaveBeenCalled();
    expect(options.failSubmit).toHaveBeenCalledWith(failure);
    expect(options.onJobCreated).not.toHaveBeenCalled();
    expect(options.finishSubmit).toHaveBeenCalled();
  });
});
