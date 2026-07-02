import type { FormEvent, ReactNode } from 'react';
import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import type { BookNarrationFormSection } from './bookNarrationFormTypes';
import type { BookNarrationSubmitPresentation } from './bookNarrationFormUtils';
import { BookNarrationStepBar } from './BookNarrationStepBar';
import { BookNarrationSubmitStatus } from './BookNarrationSubmitStatus';

type BookNarrationSectionMeta = Record<
  BookNarrationFormSection,
  { title: string; description: string }
>;

interface BookNarrationFormShellProps {
  showInfoHeader: boolean;
  submitPresentation: BookNarrationSubmitPresentation;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  tabSections: BookNarrationFormSection[];
  sectionMeta: BookNarrationSectionMeta;
  activeTab: BookNarrationFormSection;
  onSectionChange: (section: BookNarrationFormSection) => void;
  isSubmitting: boolean;
  isSavingTemplate: boolean;
  onSaveTemplate: () => void;
  intakeStatus: PipelineIntakeStatusResponse | null;
  isLoadingIntakeStatus: boolean;
  error: string | null;
  externalError: string | null;
  templateStatus: string | null;
  templateError: string | null;
  children: ReactNode;
}

export function BookNarrationFormShell({
  showInfoHeader,
  submitPresentation,
  onSubmit,
  tabSections,
  sectionMeta,
  activeTab,
  onSectionChange,
  isSubmitting,
  isSavingTemplate,
  onSaveTemplate,
  intakeStatus,
  isLoadingIntakeStatus,
  error,
  externalError,
  templateStatus,
  templateError,
  children,
}: BookNarrationFormShellProps) {
  return (
    <>
      {showInfoHeader ? (
        <>
          <h2>{submitPresentation.headerTitle}</h2>
          <p>{submitPresentation.headerDescription}</p>
        </>
      ) : null}
      <form className="pipeline-form" onSubmit={onSubmit} noValidate>
        <BookNarrationStepBar
          tabSections={tabSections}
          sectionMeta={sectionMeta}
          activeTab={activeTab}
          onSectionChange={onSectionChange}
          isSubmitDisabled={submitPresentation.isSubmitDisabled}
          isSubmitting={isSubmitting}
          submitText={submitPresentation.submitText}
          isSavingTemplate={isSavingTemplate}
          onSaveTemplate={onSaveTemplate}
        />
        <BookNarrationSubmitStatus
          intakeStatus={intakeStatus}
          isLoadingIntakeStatus={isLoadingIntakeStatus}
          hasMissingRequirements={submitPresentation.hasMissingRequirements}
          missingRequirementText={submitPresentation.missingRequirementText}
          error={error}
          externalError={externalError}
          templateStatus={templateStatus}
          templateError={templateError}
        />
        {children}
      </form>
    </>
  );
}
