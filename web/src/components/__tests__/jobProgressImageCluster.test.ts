import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import {
  buildImageClusterNodes,
  formatSecondsPerImage,
  normalizeBaseUrl,
  resolveImageClusterBaseUrls,
  resolveImageClusterSummary,
} from '../job-progress/jobProgressImageCluster';

const baseStatus: PipelineStatusResponse = {
  job_id: 'book-job',
  job_type: 'book',
  status: 'running',
  created_at: '2026-07-04T00:00:00Z',
  started_at: null,
  completed_at: null,
  result: null,
  error: null,
  latest_event: null,
  tuning: null,
};

describe('jobProgressImageCluster', () => {
  it('normalizes and deduplicates configured image node urls', () => {
    expect(normalizeBaseUrl(' http://example.local:7860/// ')).toBe('http://example.local:7860');
    expect(resolveImageClusterBaseUrls({
      image_api_base_urls: [
        'http://192.168.1.9:7860/',
        '',
        'http://custom.local:7860//',
        'http://192.168.1.9:7860',
      ],
      image_api_base_url: 'http://fallback.local:7860/',
    })).toEqual([
      'http://192.168.1.9:7860',
      'http://custom.local:7860',
      'http://fallback.local:7860',
    ]);
  });

  it('reads image cluster summaries from generated files and result fallbacks', () => {
    expect(resolveImageClusterSummary({
      ...baseStatus,
      generated_files: {
        image_cluster: {
          nodes: [{ base_url: 'http://192.168.1.9:7860', processed: 3 }],
        },
      },
    })).toEqual({
      nodes: [{ base_url: 'http://192.168.1.9:7860', processed: 3 }],
    });
    expect(resolveImageClusterSummary({
      ...baseStatus,
      result: {
        generated_files: {
          image_cluster: {
            nodes: [{ baseUrl: 'http://custom.local:7860', processed: 2 }],
          },
        },
      },
    })).toEqual({
      nodes: [{ baseUrl: 'http://custom.local:7860', processed: 2 }],
    });
  });

  it('merges known, configured, and backend-reported image nodes', () => {
    const nodes = buildImageClusterNodes(
      {
        nodes: [
          {
            base_url: 'http://192.168.1.9:7860/',
            active: false,
            processed: '7',
            avg_seconds_per_image: '1.25',
          },
          {
            baseUrl: 'http://custom.local:7860',
            active: true,
            processed: 4,
            avgSecondsPerImage: 0.42,
          },
        ],
      },
      {
        image_api_base_urls: ['http://192.168.1.157:7860/', 'http://configured.local:7860/'],
      },
      true,
    );

    expect(nodes).toContainEqual({
      baseUrl: 'http://192.168.1.9:7860',
      active: false,
      processed: 7,
      avgSecondsPerImage: 1.25,
    });
    expect(nodes).toContainEqual({
      baseUrl: 'http://192.168.1.157:7860',
      active: true,
      processed: 0,
      avgSecondsPerImage: null,
    });
    expect(nodes).toContainEqual({
      baseUrl: 'http://custom.local:7860',
      active: true,
      processed: 4,
      avgSecondsPerImage: 0.42,
    });
    expect(nodes).toContainEqual({
      baseUrl: 'http://configured.local:7860',
      active: true,
      processed: 0,
      avgSecondsPerImage: null,
    });
  });

  it('omits disabled empty clusters and formats speed labels defensively', () => {
    expect(buildImageClusterNodes(null, null, false)).toEqual([]);
    expect(formatSecondsPerImage(null)).toBe('— s/image');
    expect(formatSecondsPerImage(0.42)).toBe('0.42 s/image');
    expect(formatSecondsPerImage(3.4)).toBe('3.4 s/image');
    expect(formatSecondsPerImage(12.8)).toBe('13 s/image');
  });
});
