import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { checkImageNodeAvailability } from '../../api/client';
import { IMAGE_API_NODE_OPTIONS } from '../../constants/imageNodes';
import {
  imageNodeStatusLabel,
  orderedImageNodeSelections,
  useBookNarrationImageNodeAvailability
} from '../book-narration/useBookNarrationImageNodeAvailability';

vi.mock('../../api/client', () => ({
  checkImageNodeAvailability: vi.fn()
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe('useBookNarrationImageNodeAvailability', () => {
  it('checks selected nodes with fallback URLs and reports fallback availability', async () => {
    const macBookNode = IMAGE_API_NODE_OPTIONS.find((option) => option.fallbackValues?.length);
    if (!macBookNode?.fallbackValues?.[0]) {
      throw new Error('Expected an image node with a fallback value');
    }

    vi.mocked(checkImageNodeAvailability).mockResolvedValue({
      nodes: [
        { base_url: macBookNode.value, available: false },
        { base_url: macBookNode.fallbackValues[0], available: true }
      ],
      available: [macBookNode.fallbackValues[0]],
      unavailable: [macBookNode.value]
    });

    const { result } = renderHook(() =>
      useBookNarrationImageNodeAvailability({
        addImages: true,
        selectedNodeUrls: [macBookNode.value]
      })
    );

    await waitFor(() => {
      expect(result.current.nodeStatusByUrl[macBookNode.value]?.state).toBe('fallback');
    });

    expect(checkImageNodeAvailability).toHaveBeenCalledWith({
      base_urls: [macBookNode.value, macBookNode.fallbackValues[0]]
    });
    expect(imageNodeStatusLabel(result.current.nodeStatusByUrl[macBookNode.value])).toContain(
      macBookNode.fallbackValues[0]
    );
  });

  it('clears status when image generation is disabled', async () => {
    const node = IMAGE_API_NODE_OPTIONS[0];
    vi.mocked(checkImageNodeAvailability).mockResolvedValue({
      nodes: [{ base_url: node.value, available: true }],
      available: [node.value],
      unavailable: []
    });

    const { result, rerender } = renderHook(
      ({ addImages }) =>
        useBookNarrationImageNodeAvailability({
          addImages,
          selectedNodeUrls: [node.value]
        }),
      { initialProps: { addImages: true } }
    );

    await waitFor(() => {
      expect(result.current.nodeStatusByUrl[node.value]?.state).toBe('available');
    });

    rerender({ addImages: false });

    await waitFor(() => {
      expect(result.current.nodeStatusByUrl).toEqual({});
    });
  });

  it('orders selected known nodes before preserved custom nodes', () => {
    const customNode = 'http://custom-node.local:7860';
    const selected = new Set([
      customNode,
      IMAGE_API_NODE_OPTIONS[2].value,
      IMAGE_API_NODE_OPTIONS[0].value
    ]);

    expect(orderedImageNodeSelections(selected, [customNode])).toEqual([
      IMAGE_API_NODE_OPTIONS[0].value,
      IMAGE_API_NODE_OPTIONS[2].value,
      customNode
    ]);
  });
});
