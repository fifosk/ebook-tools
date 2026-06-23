import { useMemo, useState } from 'react';
import type { JobState } from '../../components/JobList';
import type { SubtitleToolTab } from './subtitleToolTypes';
import { sortSubtitleJobsNewestFirst } from './subtitleJobUtils';

export function useSubtitleTabState(subtitleJobs: JobState[]) {
  const [activeTab, setActiveTab] = useState<SubtitleToolTab>('subtitles');
  const sortedSubtitleJobs = useMemo(
    () => sortSubtitleJobsNewestFirst(subtitleJobs),
    [subtitleJobs]
  );

  return {
    activeTab,
    setActiveTab,
    sortedSubtitleJobs
  };
}
