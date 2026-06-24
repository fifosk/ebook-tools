import type { BookNarrationFormSection } from './bookNarrationFormTypes';

type BookNarrationSectionMeta = Record<
  BookNarrationFormSection,
  { title: string; description: string }
>;

interface BookNarrationStepBarProps {
  tabSections: BookNarrationFormSection[];
  sectionMeta: BookNarrationSectionMeta;
  activeTab: BookNarrationFormSection;
  onSectionChange: (section: BookNarrationFormSection) => void;
  isSubmitDisabled: boolean;
  isSubmitting: boolean;
  submitText: string;
  isSavingTemplate?: boolean;
  onSaveTemplate?: () => void;
}

export function BookNarrationStepBar({
  tabSections,
  sectionMeta,
  activeTab,
  onSectionChange,
  isSubmitDisabled,
  isSubmitting,
  submitText,
  isSavingTemplate = false,
  onSaveTemplate
}: BookNarrationStepBarProps) {
  return (
    <div className="pipeline-step-bar">
      <div className="pipeline-step-tabs" role="tablist" aria-label="Pipeline steps">
        {tabSections.map((section) => {
          const meta = sectionMeta[section];
          const isActive = activeTab === section;
          return (
            <button
              type="button"
              key={section}
              className={`pipeline-step-tab ${isActive ? 'is-active' : ''}`}
              onClick={() => onSectionChange(section)}
              aria-selected={isActive}
              role="tab"
            >
              <span className="pipeline-step-tab__label">{meta.title}</span>
            </button>
          );
        })}
      </div>
      <div className="pipeline-step-actions">
        {onSaveTemplate ? (
          <button
            type="button"
            className="pipeline-step-action-secondary"
            onClick={onSaveTemplate}
            disabled={isSavingTemplate}
          >
            {isSavingTemplate ? 'Saving…' : 'Save template'}
          </button>
        ) : null}
        <button type="submit" disabled={isSubmitDisabled}>
          {isSubmitting ? 'Submitting…' : submitText}
        </button>
      </div>
    </div>
  );
}
