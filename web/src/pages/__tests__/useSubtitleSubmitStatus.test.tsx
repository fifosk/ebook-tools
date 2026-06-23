import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import {
  resolveSubtitleSubmitErrorMessage,
  SUBTITLE_INTAKE_AT_CAPACITY_MESSAGE,
  useSubtitleSubmitStatus
} from '../subtitle-tool/useSubtitleSubmitStatus';

describe('resolveSubtitleSubmitErrorMessage', () => {
  it('uses Error messages and falls back for unknown thrown values', () => {
    expect(resolveSubtitleSubmitErrorMessage(new Error('backend unavailable'))).toBe(
      'backend unavailable'
    );
    expect(resolveSubtitleSubmitErrorMessage('plain failure')).toBe('Unable to submit subtitle job.');
  });
});

describe('useSubtitleSubmitStatus', () => {
  it('starts idle and clears stale errors when submission begins', () => {
    const { result } = renderHook(() => useSubtitleSubmitStatus());

    expect(result.current.isSubmitting).toBe(false);
    expect(result.current.submitError).toBeNull();

    act(() => {
      result.current.setSubmitError('old validation error');
      result.current.beginSubmit();
    });

    expect(result.current.isSubmitting).toBe(true);
    expect(result.current.submitError).toBeNull();

    act(() => {
      result.current.finishSubmit();
    });

    expect(result.current.isSubmitting).toBe(false);
  });

  it('records queue-capacity rejections without entering submitting state', () => {
    const { result } = renderHook(() => useSubtitleSubmitStatus());

    act(() => {
      result.current.rejectAtCapacity();
    });

    expect(result.current.isSubmitting).toBe(false);
    expect(result.current.submitError).toBe(SUBTITLE_INTAKE_AT_CAPACITY_MESSAGE);
  });

  it('records submit failures and supports explicit reset', () => {
    const { result } = renderHook(() => useSubtitleSubmitStatus());

    act(() => {
      result.current.beginSubmit();
      result.current.failSubmit(new Error('request failed'));
      result.current.finishSubmit();
    });

    expect(result.current.isSubmitting).toBe(false);
    expect(result.current.submitError).toBe('request failed');

    act(() => {
      result.current.resetSubmitError();
    });

    expect(result.current.submitError).toBeNull();
  });
});
