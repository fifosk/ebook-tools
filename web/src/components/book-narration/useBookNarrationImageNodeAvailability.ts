import { useEffect, useMemo, useRef, useState } from 'react';
import { checkImageNodeAvailability } from '../../api/client';
import {
  expandImageNodeCandidates,
  getImageNodeFallbacks,
  IMAGE_API_NODE_OPTIONS,
  normalizeImageNodeUrl
} from '../../constants/imageNodes';

export type ImageNodeAvailabilityState =
  | 'available'
  | 'fallback'
  | 'unavailable'
  | 'checking'
  | 'unknown'
  | 'idle';

export type ImageNodeAvailabilityInfo = {
  state: ImageNodeAvailabilityState;
  fallbackUrl?: string | null;
};

export const IMAGE_NODE_STATUS_LABELS: Record<ImageNodeAvailabilityState, string> = {
  available: 'Available',
  fallback: 'Available (fallback)',
  unavailable: 'Unavailable',
  checking: 'Checking',
  unknown: 'Unknown',
  idle: 'Not selected'
};

const IMAGE_API_NODE_VALUE_SET = new Set(IMAGE_API_NODE_OPTIONS.map((option) => option.value));

export function imageNodeStatusLabel(info: ImageNodeAvailabilityInfo): string {
  if (info.state === 'fallback' && info.fallbackUrl) {
    return `Available (fallback ${info.fallbackUrl})`;
  }
  return IMAGE_NODE_STATUS_LABELS[info.state];
}

export function orderedImageNodeSelections(
  selectedNodes: Set<string>,
  previousUrls: string[]
): string[] {
  const ordered: string[] = [];
  for (const option of IMAGE_API_NODE_OPTIONS) {
    if (selectedNodes.has(option.value)) {
      ordered.push(option.value);
    }
  }
  for (const entry of previousUrls) {
    if (!IMAGE_API_NODE_VALUE_SET.has(entry) && selectedNodes.has(entry)) {
      ordered.push(entry);
    }
  }
  return ordered;
}

type UseBookNarrationImageNodeAvailabilityOptions = {
  addImages: boolean;
  selectedNodeUrls: string[];
};

export function useBookNarrationImageNodeAvailability({
  addImages,
  selectedNodeUrls
}: UseBookNarrationImageNodeAvailabilityOptions) {
  const selectedNodeSignature = selectedNodeUrls.join('\n');
  const stableSelectedNodeUrls = useMemo(() => selectedNodeUrls, [selectedNodeSignature]);
  const availabilityNodeUrls = useMemo(
    () => expandImageNodeCandidates(stableSelectedNodeUrls),
    [stableSelectedNodeUrls]
  );
  const [nodeStatusByUrl, setNodeStatusByUrl] = useState<Record<string, ImageNodeAvailabilityInfo>>({});
  const nodeStatusRequestId = useRef(0);

  useEffect(() => {
    if (!addImages || stableSelectedNodeUrls.length === 0) {
      setNodeStatusByUrl({});
      return;
    }

    nodeStatusRequestId.current += 1;
    const requestId = nodeStatusRequestId.current;

    setNodeStatusByUrl((prev) => {
      const next = { ...prev };
      for (const url of stableSelectedNodeUrls) {
        next[url] = { state: 'checking' };
      }
      return next;
    });

    checkImageNodeAvailability({ base_urls: availabilityNodeUrls })
      .then((response) => {
        if (nodeStatusRequestId.current !== requestId) {
          return;
        }
        const availabilityMap = new Map<string, boolean>();
        for (const entry of response.nodes) {
          const normalized = normalizeImageNodeUrl(entry.base_url);
          if (!normalized) {
            continue;
          }
          availabilityMap.set(normalized, Boolean(entry.available));
        }
        setNodeStatusByUrl((prev) => {
          const next = { ...prev };
          for (const url of stableSelectedNodeUrls) {
            const normalized = normalizeImageNodeUrl(url);
            if (!normalized) {
              continue;
            }
            const primaryAvailable = availabilityMap.get(normalized);
            if (primaryAvailable) {
              next[url] = { state: 'available' };
              continue;
            }
            const fallbacks = getImageNodeFallbacks(normalized);
            const fallback = fallbacks.find((entry) => availabilityMap.get(entry));
            if (fallback) {
              next[url] = { state: 'fallback', fallbackUrl: fallback };
              continue;
            }
            next[url] = { state: 'unavailable' };
          }
          return next;
        });
      })
      .catch(() => {
        if (nodeStatusRequestId.current !== requestId) {
          return;
        }
        setNodeStatusByUrl((prev) => {
          const next = { ...prev };
          for (const url of stableSelectedNodeUrls) {
            if (next[url]?.state === 'checking') {
              next[url] = { state: 'unknown' };
            }
          }
          return next;
        });
      });
  }, [addImages, availabilityNodeUrls, stableSelectedNodeUrls]);

  return {
    nodeStatusByUrl
  };
}
