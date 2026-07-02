import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import VideoDubbingFeedbackPanel from '../video-dubbing/VideoDubbingFeedbackPanel';

describe('VideoDubbingFeedbackPanel', () => {
  it('renders page feedback and intake state in the same stack', () => {
    render(
      <VideoDubbingFeedbackPanel
        statusMessage="Download Station task completed."
        generateError="Unable to submit dubbing job."
        isLoadingCreationTemplate={true}
        templateStatus="Template saved."
        creationTemplateError="Template handoff failed."
        templateError="Template save failed."
        intakeStatus={{
          acceptingJobs: true,
          isUnderPressure: false,
          queueDepth: 2,
          activeCount: 1,
          softLimit: 10,
          hardLimit: 20,
          delayCount: 0
        }}
        isLoadingIntakeStatus={false}
      />
    );

    expect(screen.getByText('Download Station task completed.')).toBeInTheDocument();
    expect(screen.getByText('Unable to submit dubbing job.')).toBeInTheDocument();
    expect(screen.getByText('Loading saved template...')).toBeInTheDocument();
    expect(screen.getByText('Template saved.')).toBeInTheDocument();
    expect(screen.getByText('Template handoff failed.')).toBeInTheDocument();
    expect(screen.queryByText('Template save failed.')).not.toBeInTheDocument();
    expect(screen.getByText('Job intake is available: 2 pending and 1 running.')).toBeInTheDocument();
    expect(screen.getByText('Slowdown starts at 10 pending')).toBeInTheDocument();
  });

  it('falls back to template save errors and loading intake status', () => {
    render(
      <VideoDubbingFeedbackPanel
        statusMessage={null}
        generateError={null}
        isLoadingCreationTemplate={false}
        templateStatus={null}
        creationTemplateError={null}
        templateError="Template save failed."
        intakeStatus={null}
        isLoadingIntakeStatus={true}
      />
    );

    expect(screen.getByText('Template save failed.')).toBeInTheDocument();
    expect(screen.getByText('Checking job intake...')).toBeInTheDocument();
  });
});
