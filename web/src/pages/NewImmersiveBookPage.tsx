import { useMemo } from 'react';
import type {
  CreationTemplateEntry,
  JobParameterSnapshot,
  PipelineRequestPayload,
  PipelineStatusResponse
} from '../api/dtos';
import BookNarrationForm, { type BookNarrationFormSection } from '../components/book-narration/BookNarrationForm';

interface NewImmersiveBookPageProps {
  activeSection: BookNarrationFormSection;
  onSectionChange: (section: BookNarrationFormSection) => void;
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  prefillInputFile?: string | null;
  submitError?: string | null;
  recentJobs?: PipelineStatusResponse[] | null;
  prefillParameters?: JobParameterSnapshot | null;
  creationTemplate?: CreationTemplateEntry | null;
  creationTemplateError?: string | null;
  isLoadingCreationTemplate?: boolean;
}

export default function NewImmersiveBookPage({
  activeSection,
  onSectionChange,
  onSubmit,
  isSubmitting = false,
  prefillInputFile = null,
  submitError = null,
  recentJobs = null,
  prefillParameters = null,
  creationTemplate = null,
  creationTemplateError = null,
  isLoadingCreationTemplate = false
}: NewImmersiveBookPageProps) {
  const effectiveSection: BookNarrationFormSection = useMemo(() => activeSection, [activeSection]);

  return (
    <div className="new-immersive-book">
      <BookNarrationForm
        onSubmit={onSubmit}
        isSubmitting={isSubmitting}
        prefillInputFile={prefillInputFile}
        prefillParameters={prefillParameters}
        creationTemplate={creationTemplate}
        creationTemplateError={creationTemplateError}
        isLoadingCreationTemplate={isLoadingCreationTemplate}
        activeSection={effectiveSection}
        onSectionChange={onSectionChange}
        externalError={submitError}
        recentJobs={recentJobs}
        implicitEndOffsetThreshold={200}
        defaultImageSettings={{
          add_images: false,
          image_style_template: 'wireframe',
          image_prompt_context_sentences: 0,
          image_width: '256',
          image_height: '256'
        }}
        showInfoHeader={false}
        showOutputPathControls={false}
      />
    </div>
  );
}
