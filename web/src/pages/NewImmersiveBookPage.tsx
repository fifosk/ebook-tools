import { useEffect, useMemo, useState } from 'react';
import type { PipelineRequestPayload } from '../api/dtos';
import PipelineSubmissionForm, {
  PIPELINE_SECTION_META,
  type PipelineFormSection
} from '../components/PipelineSubmissionForm';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs';

type TabsValue = 'settings' | 'submit';

interface NewImmersiveBookPageProps {
  activeSection: PipelineFormSection;
  onSectionChange: (section: PipelineFormSection) => void;
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  prefillInputFile?: string | null;
  submitError?: string | null;
}

const SETTINGS_SECTIONS: PipelineFormSection[] = ['source', 'language', 'output', 'performance'];

function resolveInitialSettingsSection(section: PipelineFormSection): PipelineFormSection {
  if (section === 'submit') {
    return 'source';
  }
  return section;
}

export default function NewImmersiveBookPage({
  activeSection,
  onSectionChange,
  onSubmit,
  isSubmitting = false,
  prefillInputFile = null,
  submitError = null
}: NewImmersiveBookPageProps) {
  const [tabValue, setTabValue] = useState<TabsValue>(activeSection === 'submit' ? 'submit' : 'settings');
  const [settingsSection, setSettingsSection] = useState<PipelineFormSection>(() =>
    resolveInitialSettingsSection(activeSection)
  );
  const [lastSettingsSection, setLastSettingsSection] = useState<PipelineFormSection>(() =>
    resolveInitialSettingsSection(activeSection)
  );

  useEffect(() => {
    if (activeSection === 'submit') {
      setTabValue('submit');
      return;
    }
    setTabValue('settings');
    setSettingsSection(activeSection);
    setLastSettingsSection(activeSection);
  }, [activeSection]);

  const settingsMeta = useMemo(
    () =>
      SETTINGS_SECTIONS.map((section) => ({
        key: section,
        title: PIPELINE_SECTION_META[section].title,
        description: PIPELINE_SECTION_META[section].description
      })),
    []
  );

  const effectiveSection: PipelineFormSection = tabValue === 'submit' ? 'submit' : settingsSection;

  const handleSelectSettingsSection = (section: PipelineFormSection) => {
    if (section === 'submit') {
      setTabValue('submit');
      onSectionChange('submit');
      return;
    }
    setSettingsSection(section);
    setLastSettingsSection(section);
    if (tabValue !== 'settings') {
      setTabValue('settings');
    }
    onSectionChange(section);
  };

  const handleTabChange = (value: string) => {
    if (value !== 'settings' && value !== 'submit') {
      return;
    }
    const nextValue = value as TabsValue;
    if (nextValue === tabValue) {
      return;
    }
    setTabValue(nextValue);
    if (nextValue === 'submit') {
      onSectionChange('submit');
    } else {
      const nextSection = lastSettingsSection || 'source';
      setSettingsSection(nextSection);
      onSectionChange(nextSection);
    }
  };

  return (
    <div className="new-immersive-book">
      <Tabs value={tabValue} onValueChange={handleTabChange} className="new-immersive-book__tabs">
        <TabsList className="new-immersive-book__tablist">
          <TabsTrigger value="settings">Configure settings</TabsTrigger>
          <TabsTrigger value="submit">Submit job</TabsTrigger>
        </TabsList>
        <TabsContent value="settings" className="new-immersive-book__panel" aria-label="Pipeline settings">
          <div className="new-immersive-book__accordion-list">
            {settingsMeta.map((section) => {
              const isActive = tabValue === 'settings' && settingsSection === section.key;
              return (
                <details
                  key={section.key}
                  className="new-immersive-book__accordion"
                  open={isActive}
                >
                  <summary
                    onClick={(event) => {
                      event.preventDefault();
                      handleSelectSettingsSection(section.key);
                    }}
                  >
                    <span className="new-immersive-book__accordion-title">{section.title}</span>
                    <span className="new-immersive-book__accordion-description">{section.description}</span>
                  </summary>
                </details>
              );
            })}
          </div>
        </TabsContent>
        <TabsContent value="submit" className="new-immersive-book__panel" />
      </Tabs>
      <div className="new-immersive-book__form">
        <PipelineSubmissionForm
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
          prefillInputFile={prefillInputFile}
          activeSection={effectiveSection}
          externalError={tabValue === 'submit' ? submitError : null}
        />
      </div>
    </div>
  );
}
