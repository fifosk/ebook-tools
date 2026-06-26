import { useCallback, useState } from 'react';
import {
  generateYoutubeDub,
  saveCreationTemplate
} from '../../api/client';
import type { VideoDubbingTab } from './videoDubbingTypes';
import {
  buildVideoDubbingGeneratePayload,
  buildVideoDubbingTemplatePayload,
  type VideoDubbingGeneratePayloadInput
} from './videoDubbingUtils';

type VideoDubbingJobActionsOptions = VideoDubbingGeneratePayloadInput & {
  selectedVideoDiscoveryTemplateState: Record<string, unknown> | null;
  isIntakeAtCapacity: boolean;
  onJobCreated: (jobId: string) => void;
  onActiveTabChange: (tab: VideoDubbingTab) => void;
  onStatusMessageChange: (message: string | null) => void;
  refreshIntakeStatus: () => Promise<unknown>;
};

export function useVideoDubbingJobActions({
  selectedVideoDiscoveryTemplateState,
  isIntakeAtCapacity,
  onJobCreated,
  onActiveTabChange,
  onStatusMessageChange,
  refreshIntakeStatus,
  ...payloadInput
}: VideoDubbingJobActionsOptions) {
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [templateStatus, setTemplateStatus] = useState<string | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);

  const canGenerate = Boolean(payloadInput.selectedVideo && payloadInput.selectedSubtitle && !isGenerating && !isIntakeAtCapacity);

  const handleGenerate = useCallback(async () => {
    if (isIntakeAtCapacity) {
      setGenerateError('Job queue is at capacity. Wait for pending jobs to clear before creating a dubbed video.');
      return;
    }
    const result = buildVideoDubbingGeneratePayload(payloadInput);
    if (!result.payload) {
      setGenerateError(result.error);
      return;
    }
    setIsGenerating(true);
    setGenerateError(null);
    onStatusMessageChange(null);
    try {
      const response = await generateYoutubeDub(result.payload);
      onStatusMessageChange(`Dub job submitted as ${response.job_id}. Track progress below.`);
      onJobCreated(response.job_id);
      onActiveTabChange('jobs');
      await refreshIntakeStatus();
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to generate dubbed video.' : 'Unable to generate dubbed video.';
      setGenerateError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [
    isIntakeAtCapacity,
    onActiveTabChange,
    onJobCreated,
    onStatusMessageChange,
    payloadInput,
    refreshIntakeStatus
  ]);

  const handleSaveTemplate = useCallback(async () => {
    const result = buildVideoDubbingGeneratePayload(payloadInput);
    if (!result.payload) {
      setTemplateError(result.error);
      setTemplateStatus(null);
      return;
    }

    setIsSavingTemplate(true);
    setTemplateError(null);
    setTemplateStatus(null);
    try {
      const saved = await saveCreationTemplate(buildVideoDubbingTemplatePayload(
        result.payload,
        selectedVideoDiscoveryTemplateState
      ));
      setTemplateStatus(`Saved template "${saved.name}". Apple Create can apply it from YouTube Dub.`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to save video template.' : 'Unable to save video template.';
      setTemplateError(message);
    } finally {
      setIsSavingTemplate(false);
    }
  }, [payloadInput, selectedVideoDiscoveryTemplateState]);

  return {
    generateError,
    isGenerating,
    templateStatus,
    setTemplateStatus,
    templateError,
    setTemplateError,
    isSavingTemplate,
    canGenerate,
    handleGenerate,
    handleSaveTemplate
  };
}
