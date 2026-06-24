import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { BookNarrationSubmitStatus } from '../book-narration/BookNarrationSubmitStatus';

const openIntakeStatus: PipelineIntakeStatusResponse = {
  acceptingJobs: true,
  isUnderPressure: false,
  queueDepth: 1,
  activeCount: 1,
  softLimit: 3,
  hardLimit: 6,
  delayCount: 0
};

function renderStatus(overrides: Partial<Parameters<typeof BookNarrationSubmitStatus>[0]> = {}) {
  return render(
    <BookNarrationSubmitStatus
      intakeStatus={null}
      isLoadingIntakeStatus={false}
      hasMissingRequirements={false}
      missingRequirementText=""
      error={null}
      externalError={null}
      {...overrides}
    />
  );
}

describe('BookNarrationSubmitStatus', () => {
  it('renders missing requirements before submit', () => {
    renderStatus({
      hasMissingRequirements: true,
      missingRequirementText: 'input file and target language'
    });

    expect(screen.getByRole('status')).toHaveTextContent(
      'Provide input file and target language before submitting.'
    );
  });

  it('prefers internal submit errors over external errors', () => {
    renderStatus({
      error: 'Fix the JSON config',
      externalError: 'Backend unavailable'
    });

    expect(screen.getByRole('alert')).toHaveTextContent('Fix the JSON config');
  });

  it('renders intake status presentation from the shared callout', () => {
    renderStatus({ intakeStatus: openIntakeStatus });

    expect(screen.getByRole('status')).toHaveTextContent(/Job intake is available/i);
  });

  it('renders intake loading state', () => {
    renderStatus({ isLoadingIntakeStatus: true });

    expect(screen.getByRole('status')).toHaveTextContent(/Checking job intake/i);
  });
});
