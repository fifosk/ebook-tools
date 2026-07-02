import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import SubtitleToolStatusNotices from '../subtitle-tool/SubtitleToolStatusNotices';

describe('SubtitleToolStatusNotices', () => {
  it('renders submit, template, intake, and submitted-summary notices', () => {
    render(
      <SubtitleToolStatusNotices
        submitError="Unable to submit subtitle job."
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
        isLoadingCreationTemplate={true}
        templateStatus="Template saved."
        submittedSummary="Submitted subtitles for episode one."
      />
    );

    expect(screen.getByText('Unable to submit subtitle job.')).toBeInTheDocument();
    expect(screen.getByText('Template handoff failed.')).toBeInTheDocument();
    expect(screen.queryByText('Template save failed.')).not.toBeInTheDocument();
    expect(screen.getByText('Job intake is available: 2 pending and 1 running.')).toBeInTheDocument();
    expect(screen.getByText('Loading saved template...')).toBeInTheDocument();
    expect(screen.queryByText('Template saved.')).not.toBeInTheDocument();
    expect(screen.getByText('Submitted subtitles for episode one.')).toBeInTheDocument();
  });

  it('falls back to template save errors and loading intake status', () => {
    render(
      <SubtitleToolStatusNotices
        submitError={null}
        creationTemplateError={null}
        templateError="Template save failed."
        intakeStatus={null}
        isLoadingIntakeStatus={true}
        isLoadingCreationTemplate={false}
        templateStatus="Template saved."
        submittedSummary={null}
      />
    );

    expect(screen.getByText('Template save failed.')).toBeInTheDocument();
    expect(screen.getByText('Checking job intake...')).toBeInTheDocument();
    expect(screen.getByText('Template saved.')).toBeInTheDocument();
  });
});
