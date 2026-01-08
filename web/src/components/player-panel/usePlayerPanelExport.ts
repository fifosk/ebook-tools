import { useCallback, useEffect, useState } from 'react';
import type { PlayerMode } from '../../types/player';
import { appendAccessToken, createExport, withBase } from '../../api/client';
import { downloadWithSaveAs } from '../../utils/downloads';

type UsePlayerPanelExportArgs = {
  jobId: string;
  origin?: 'job' | 'library';
  playerMode?: PlayerMode;
  isBookLike: boolean;
  mediaComplete: boolean;
  hasInteractiveChunks: boolean;
  hasTextItems: boolean;
};

type UsePlayerPanelExportResult = {
  canExport: boolean;
  isExporting: boolean;
  exportError: string | null;
  handleExport: () => Promise<void>;
};

export function usePlayerPanelExport({
  jobId,
  origin = 'job',
  playerMode = 'online',
  isBookLike,
  mediaComplete,
  hasInteractiveChunks,
  hasTextItems,
}: UsePlayerPanelExportArgs): UsePlayerPanelExportResult {
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    setIsExporting(false);
    setExportError(null);
  }, [jobId]);

  const canExport = playerMode !== 'export' && isBookLike && mediaComplete && (hasInteractiveChunks || hasTextItems);

  const handleExport = useCallback(async () => {
    if (!jobId || isExporting) {
      return;
    }
    setIsExporting(true);
    setExportError(null);
    const payload = {
      source_kind: origin === 'library' ? 'library' : 'job',
      source_id: jobId,
      player_type: 'interactive-text',
    } as const;
    try {
      const result = await createExport(payload);
      const resolved =
        result.download_url.startsWith('http://') || result.download_url.startsWith('https://')
          ? result.download_url
          : withBase(result.download_url);
      const downloadUrl = appendAccessToken(resolved);
      await downloadWithSaveAs(downloadUrl, result.filename ?? null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unable to export offline player.';
      setExportError(message);
    } finally {
      setIsExporting(false);
    }
  }, [appendAccessToken, createExport, downloadWithSaveAs, isExporting, jobId, origin, withBase]);

  return {
    canExport,
    isExporting,
    exportError,
    handleExport,
  };
}
