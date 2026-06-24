import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { CreateIntakeStatusCallout } from '../create-intake/CreateIntakeStatusCallout';

interface BookNarrationSubmitStatusProps {
  intakeStatus: PipelineIntakeStatusResponse | null;
  isLoadingIntakeStatus: boolean;
  hasMissingRequirements: boolean;
  missingRequirementText: string;
  error: string | null;
  externalError: string | null;
  templateStatus?: string | null;
  templateError?: string | null;
}

export function BookNarrationSubmitStatus({
  intakeStatus,
  isLoadingIntakeStatus,
  hasMissingRequirements,
  missingRequirementText,
  error,
  externalError,
  templateStatus = null,
  templateError = null
}: BookNarrationSubmitStatusProps) {
  return (
    <>
      <CreateIntakeStatusCallout status={intakeStatus} isLoading={isLoadingIntakeStatus} />
      {templateStatus ? (
        <div className="form-callout form-callout--success" role="status">
          {templateStatus}
        </div>
      ) : null}
      {hasMissingRequirements ? (
        <div className="form-callout form-callout--warning" role="status">
          Provide {missingRequirementText} before submitting.
        </div>
      ) : null}
      {templateError || error || externalError ? (
        <div className="alert" role="alert">
          {templateError ?? error ?? externalError}
        </div>
      ) : null}
    </>
  );
}
