import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { CreateIntakeStatusCallout } from '../../components/create-intake/CreateIntakeStatusCallout';

type SubtitleToolStatusNoticesProps = {
  submitError: string | null;
  creationTemplateError: string | null;
  templateError: string | null;
  intakeStatus: PipelineIntakeStatusResponse | null;
  isLoadingIntakeStatus: boolean;
  isLoadingCreationTemplate: boolean;
  templateStatus: string | null;
  submittedSummary: string | null;
};

export default function SubtitleToolStatusNotices({
  submitError,
  creationTemplateError,
  templateError,
  intakeStatus,
  isLoadingIntakeStatus,
  isLoadingCreationTemplate,
  templateStatus,
  submittedSummary
}: SubtitleToolStatusNoticesProps) {
  const resolvedTemplateError = creationTemplateError ?? templateError;
  const templateNotice = isLoadingCreationTemplate ? 'Loading saved template...' : templateStatus;

  return (
    <>
      {submitError ? <div className="alert" role="alert">{submitError}</div> : null}
      {resolvedTemplateError ? <div className="alert" role="alert">{resolvedTemplateError}</div> : null}
      <CreateIntakeStatusCallout status={intakeStatus} isLoading={isLoadingIntakeStatus} />
      {templateNotice ? (
        <div className="notice notice--info" role="status">
          {templateNotice}
        </div>
      ) : null}
      {submittedSummary ? (
        <div className="notice notice--info" role="status">
          {submittedSummary}
        </div>
      ) : null}
    </>
  );
}
