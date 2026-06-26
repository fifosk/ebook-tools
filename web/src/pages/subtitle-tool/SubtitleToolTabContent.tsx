import type { ComponentProps, FormEventHandler } from 'react';
import SubtitleJobsPanel from './SubtitleJobsPanel';
import SubtitleMetadataPanel from './SubtitleMetadataPanel';
import SubtitleOptionsPanel from './SubtitleOptionsPanel';
import SubtitleSourcePanel from './SubtitleSourcePanel';
import SubtitleTuningPanel from './SubtitleTuningPanel';
import type { SubtitleToolTab } from './subtitleToolTypes';

type SubtitleToolTabContentProps = {
  activeTab: SubtitleToolTab;
  formId: string;
  onSubmit: FormEventHandler<HTMLFormElement>;
  sourcePanelProps: ComponentProps<typeof SubtitleSourcePanel>;
  optionsPanelProps: ComponentProps<typeof SubtitleOptionsPanel>;
  tuningPanelProps: ComponentProps<typeof SubtitleTuningPanel>;
  metadataPanelProps: ComponentProps<typeof SubtitleMetadataPanel>;
  jobsPanelProps: ComponentProps<typeof SubtitleJobsPanel>;
};

export default function SubtitleToolTabContent({
  activeTab,
  formId,
  onSubmit,
  sourcePanelProps,
  optionsPanelProps,
  tuningPanelProps,
  metadataPanelProps,
  jobsPanelProps
}: SubtitleToolTabContentProps) {
  return (
    <>
      <form id={formId} onSubmit={onSubmit} className="subtitle-form">
        {activeTab === 'subtitles' ? <SubtitleSourcePanel {...sourcePanelProps} /> : null}
        {activeTab === 'options' ? <SubtitleOptionsPanel {...optionsPanelProps} /> : null}
        {activeTab === 'tuning' ? <SubtitleTuningPanel {...tuningPanelProps} /> : null}
        {activeTab === 'metadata' ? <SubtitleMetadataPanel {...metadataPanelProps} /> : null}
      </form>

      {activeTab === 'jobs' ? <SubtitleJobsPanel {...jobsPanelProps} /> : null}
    </>
  );
}
