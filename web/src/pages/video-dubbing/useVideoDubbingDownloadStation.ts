import { useCallback, useState } from 'react';
import {
  createAcquisitionJob,
  fetchAcquisitionJobStatus
} from '../../api/client';
import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse
} from '../../api/dtos';
import {
  basenameFromPath,
  resolveDownloadStationCompletedFiles
} from './videoDubbingUtils';

type VideoDubbingDownloadStationOptions = {
  isDownloadStationAvailable: boolean;
  downloadStationUnavailableMessage: string | null;
  onStatusMessageChange: (message: string | null) => void;
  onClearSelectedDiscoveryTemplate: () => void;
  onDownloadStationCompleted?: (
    job: AcquisitionJobStatusResponse
  ) => Promise<{ selectedVideoFilename?: string | null } | null | undefined>;
};

export function useVideoDubbingDownloadStation({
  isDownloadStationAvailable,
  downloadStationUnavailableMessage,
  onStatusMessageChange,
  onClearSelectedDiscoveryTemplate,
  onDownloadStationCompleted
}: VideoDubbingDownloadStationOptions) {
  const [downloadStationSourceUri, setDownloadStationSourceUri] = useState('');
  const [downloadStationCandidate, setDownloadStationCandidate] =
    useState<AcquisitionCandidate | null>(null);
  const [downloadStationDestination, setDownloadStationDestination] = useState('');
  const [downloadStationConfirmed, setDownloadStationConfirmed] = useState(false);
  const [downloadStationJob, setDownloadStationJob] =
    useState<AcquisitionJobStatusResponse | null>(null);
  const [downloadStationError, setDownloadStationError] = useState<string | null>(null);
  const [isSubmittingDownloadStation, setIsSubmittingDownloadStation] = useState(false);
  const [isPollingDownloadStation, setIsPollingDownloadStation] = useState(false);

  const handleDownloadStationSourceUriChange = useCallback((value: string) => {
    setDownloadStationSourceUri(value);
    if (value.trim()) {
      setDownloadStationCandidate(null);
      onClearSelectedDiscoveryTemplate();
    }
  }, [onClearSelectedDiscoveryTemplate]);

  const submitDownloadStation = useCallback(async () => {
    const sourceUri = downloadStationSourceUri.trim();
    const candidateToken = downloadStationCandidate?.candidate_token?.trim() ?? '';
    if (!sourceUri && !candidateToken) {
      setDownloadStationError('Enter a reviewed URL or magnet link.');
      return;
    }
    if (!isDownloadStationAvailable) {
      setDownloadStationError(
        downloadStationUnavailableMessage ?? 'Synology Download Station is not available on this backend.'
      );
      return;
    }
    if (!downloadStationConfirmed) {
      setDownloadStationError('Confirm that you are authorized to download and process this source.');
      return;
    }
    setIsSubmittingDownloadStation(true);
    setDownloadStationError(null);
    try {
      const job = await createAcquisitionJob({
        provider: 'download_station',
        source_uri: sourceUri || null,
        candidate_token: candidateToken || null,
        confirmed: true,
        destination: downloadStationDestination.trim() || null
      });
      setDownloadStationJob(job);
      onStatusMessageChange(job.message ?? `Download Station task ${job.task_id} submitted.`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to submit Download Station task.' : 'Unable to submit Download Station task.';
      setDownloadStationError(message);
    } finally {
      setIsSubmittingDownloadStation(false);
    }
  }, [
    downloadStationCandidate,
    downloadStationConfirmed,
    downloadStationDestination,
    downloadStationSourceUri,
    downloadStationUnavailableMessage,
    isDownloadStationAvailable,
    onStatusMessageChange
  ]);

  const pollDownloadStation = useCallback(async () => {
    const taskId = downloadStationJob?.task_id?.trim();
    if (!taskId) {
      setDownloadStationError('No Download Station task is ready to poll.');
      return;
    }
    setIsPollingDownloadStation(true);
    setDownloadStationError(null);
    try {
      const job = await fetchAcquisitionJobStatus(taskId, 'download_station');
      setDownloadStationJob(job);
      if (job.status === 'completed') {
        const handoff = await onDownloadStationCompleted?.(job);
        const completedFiles = resolveDownloadStationCompletedFiles(job).map(basenameFromPath);
        const completedSummary = completedFiles.length ? ` Completed: ${completedFiles.join(', ')}.` : '';
        const selectionSummary = handoff?.selectedVideoFilename
          ? ` Selected ${handoff.selectedVideoFilename} from refreshed manual downloads.`
          : ' Refresh manual downloads to select the file.';
        onStatusMessageChange(`Download Station task completed.${completedSummary}${selectionSummary}`);
      } else {
        onStatusMessageChange(job.message ?? `Download Station task is ${job.status}.`);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to poll Download Station task.' : 'Unable to poll Download Station task.';
      setDownloadStationError(message);
    } finally {
      setIsPollingDownloadStation(false);
    }
  }, [downloadStationJob, onDownloadStationCompleted, onStatusMessageChange]);

  return {
    downloadStationSourceUri,
    setDownloadStationSourceUri,
    downloadStationCandidate,
    setDownloadStationCandidate,
    downloadStationDestination,
    setDownloadStationDestination,
    downloadStationConfirmed,
    setDownloadStationConfirmed,
    downloadStationJob,
    downloadStationError,
    isSubmittingDownloadStation,
    isPollingDownloadStation,
    handleDownloadStationSourceUriChange,
    submitDownloadStation,
    pollDownloadStation
  };
}
