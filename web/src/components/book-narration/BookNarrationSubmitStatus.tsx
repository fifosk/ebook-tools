import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { CreateIntakeStatusCallout } from '../create-intake/CreateIntakeStatusCallout';

interface BookNarrationSubmitStatusProps {
  intakeStatus: PipelineIntakeStatusResponse | null;
  isLoadingIntakeStatus: boolean;
  hasMissingRequirements: boolean;
  missingRequirementText: string;
  error: string | null;
  externalError: string | null;
}

export function BookNarrationSubmitStatus({
  intakeStatus,
  isLoadingIntakeStatus,
  hasMissingRequirements,
  missingRequirementText,
  error,
  externalError
}: BookNarrationSubmitStatusProps) {
  return (
    <>
      <CreateIntakeStatusCallout status={intakeStatus} isLoading={isLoadingIntakeStatus} />
      {hasMissingRequirements ? (
        <div className="form-callout form-callout--warning" role="status">
          Provide {missingRequirementText} before submitting.
        </div>
      ) : null}
      {error || externalError ? (
        <div className="alert" role="alert">
          {error ?? externalError}
        </div>
      ) : null}
    </>
  );
}
