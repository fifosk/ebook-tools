import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { CreateIntakeStatusCallout } from '../../components/create-intake/CreateIntakeStatusCallout';
import styles from '../VideoDubbingPage.module.css';

type VideoDubbingFeedbackPanelProps = {
  statusMessage: string | null;
  generateError: string | null;
  isLoadingCreationTemplate: boolean;
  templateStatus: string | null;
  creationTemplateError: string | null;
  templateError: string | null;
  intakeStatus: PipelineIntakeStatusResponse | null;
  isLoadingIntakeStatus: boolean;
};

export default function VideoDubbingFeedbackPanel({
  statusMessage,
  generateError,
  isLoadingCreationTemplate,
  templateStatus,
  creationTemplateError,
  templateError,
  intakeStatus,
  isLoadingIntakeStatus
}: VideoDubbingFeedbackPanelProps) {
  const resolvedTemplateError = creationTemplateError ?? templateError;

  return (
    <>
      {statusMessage ? <p className={styles.success}>{statusMessage}</p> : null}
      {generateError ? <p className={styles.error}>{generateError}</p> : null}
      {isLoadingCreationTemplate ? <p className={styles.success}>Loading saved template...</p> : null}
      {templateStatus ? <p className={styles.success}>{templateStatus}</p> : null}
      {resolvedTemplateError ? <p className={styles.error}>{resolvedTemplateError}</p> : null}
      <CreateIntakeStatusCallout status={intakeStatus} isLoading={isLoadingIntakeStatus} />
    </>
  );
}
