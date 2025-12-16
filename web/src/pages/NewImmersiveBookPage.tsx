import { useMemo } from 'react';
import type { JobParameterSnapshot, PipelineRequestPayload, PipelineStatusResponse } from '../api/dtos';
import PipelineSubmissionForm, { type PipelineFormSection } from '../components/PipelineSubmissionForm';

interface NewImmersiveBookPageProps {
  activeSection: PipelineFormSection;
  onSectionChange: (section: PipelineFormSection) => void;
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  prefillInputFile?: string | null;
  submitError?: string | null;
  recentJobs?: PipelineStatusResponse[] | null;
  prefillParameters?: JobParameterSnapshot | null;
}

export default function NewImmersiveBookPage({
  activeSection,
  onSectionChange,
  onSubmit,
  isSubmitting = false,
  prefillInputFile = null,
  submitError = null,
  recentJobs = null,
  prefillParameters = null
}: NewImmersiveBookPageProps) {
  const effectiveSection: PipelineFormSection = useMemo(() => activeSection, [activeSection]);

  return (
    <div className="new-immersive-book">
      <PipelineSubmissionForm
        onSubmit={onSubmit}
        isSubmitting={isSubmitting}
        prefillInputFile={prefillInputFile}
        prefillParameters={prefillParameters}
        activeSection={effectiveSection}
        onSectionChange={onSectionChange}
        externalError={submitError}
        recentJobs={recentJobs}
        implicitEndOffsetThreshold={200}
        showInfoHeader={false}
        showOutputPathControls={false}
      />
    </div>
  );
}
