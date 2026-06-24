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
}

export function BookNarrationStepBar({
  tabSections,
  sectionMeta,
  activeTab,
  onSectionChange,
  isSubmitDisabled,
  isSubmitting,
  submitText
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
        <button type="submit" disabled={isSubmitDisabled}>
          {isSubmitting ? 'Submitting…' : submitText}
        </button>
      </div>
    </div>
  );
}
