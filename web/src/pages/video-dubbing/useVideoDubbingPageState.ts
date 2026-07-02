import { useEffect, useMemo, useRef, useState } from 'react';
import { buildHandoffPayloadExtras } from '../../utils/creationTemplatePayloadExtras';
import type { VideoDubbingTab } from './videoDubbingTypes';

type UseVideoDubbingPageStateArgs = {
  creationTemplateHandoffSource?: string | null;
};

export function useVideoDubbingPageState({
  creationTemplateHandoffSource = null
}: UseVideoDubbingPageStateArgs = {}) {
  const [activeTab, setActiveTab] = useState<VideoDubbingTab>('videos');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const templatePayloadExtras = useMemo(
    () => buildHandoffPayloadExtras(creationTemplateHandoffSource),
    [creationTemplateHandoffSource]
  );

  return {
    activeTab,
    setActiveTab,
    statusMessage,
    setStatusMessage,
    templatePayloadExtras
  };
}

export function useVideoDubbingInitialRefresh(onRefresh: () => void | Promise<void>) {
  const initialRefreshRef = useRef(onRefresh);

  useEffect(() => {
    void initialRefreshRef.current();
  }, []);
}
