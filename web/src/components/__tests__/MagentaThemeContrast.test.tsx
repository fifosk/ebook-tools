import { cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import Sidebar from '../Sidebar';
import type { JobState } from '../JobList';
import type { SelectedView } from '../../App';
import '../../index.css';

type RGB = [number, number, number];
type RGBA = [number, number, number, number];

function parseColor(value: string): RGBA {
  const normalised = value.trim();
  if (normalised.startsWith('rgba')) {
    const [, contents] = normalised.match(/rgba\(([^)]+)\)/i) ?? [];
    if (!contents) {
      throw new Error(`Unable to parse color: ${value}`);
    }
    const [r, g, b, a] = contents.split(',').map((segment) => segment.trim());
    return [Number(r) / 255, Number(g) / 255, Number(b) / 255, Number(a)];
  }
  if (normalised.startsWith('rgb')) {
    const [, contents] = normalised.match(/rgb\(([^)]+)\)/i) ?? [];
    if (!contents) {
      throw new Error(`Unable to parse color: ${value}`);
    }
    const [r, g, b] = contents.split(',').map((segment) => segment.trim());
    return [Number(r) / 255, Number(g) / 255, Number(b) / 255, 1];
  }
  throw new Error(`Unsupported color format: ${value}`);
}

function compositeColor(color: RGBA, fallback: RGB): RGB {
  const [r, g, b, a] = color;
  const [br, bg, bb] = fallback;
  return [r * a + br * (1 - a), g * a + bg * (1 - a), b * a + bb * (1 - a)];
}

function resolveColor(value: string, fallback?: RGB): RGB {
  const [r, g, b, a] = parseColor(value);
  if (a >= 1 || !fallback) {
    return [r, g, b];
  }
  return compositeColor([r, g, b, a], fallback);
}

function relativeLuminance([r, g, b]: RGB): number {
  const transform = (channel: number) =>
    channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
  return 0.2126 * transform(r) + 0.7152 * transform(g) + 0.0722 * transform(b);
}

function contrastRatio(foreground: RGB, background: RGB): number {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

function buildJob(jobId: string, status: 'running' | 'pending' | 'failed' | 'completed'): JobState {
  const timestamp = new Date().toISOString();
  return {
    jobId,
    status: {
      job_id: jobId,
      job_type: 'pipeline',
      status,
      created_at: timestamp,
      started_at: timestamp,
      completed_at: null,
      result: null,
      error: null,
      latest_event: null,
      tuning: null
    },
    latestEvent: undefined,
    isReloading: false,
    isMutating: false,
    canManage: true
  };
}

describe('Magenta theme contrast', () => {
  beforeEach(() => {
    document.documentElement.setAttribute('data-theme', 'magenta');
  });

  afterEach(() => {
    cleanup();
    document.body.innerHTML = '';
    document.documentElement.removeAttribute('data-theme');
  });

  it('keeps sidebar navigation links above the WCAG AA contrast threshold', () => {
    const jobs: JobState[] = [
      buildJob('job-1', 'running'),
      buildJob('job-2', 'pending')
    ];

    const onSelectView = () => {};
    const { container } = render(
      <Sidebar
        selectedView={'pipeline:source' as SelectedView}
        onSelectView={onSelectView}
        sidebarJobs={jobs}
        activeJobId="job-1"
        onSelectJob={() => {}}
        onOpenPlayer={() => {}}
        isAdmin={false}
        createBookView={'books:create' as SelectedView}
        libraryView={'library:list' as SelectedView}
        subtitlesView={'subtitles:home' as SelectedView}
	        youtubeSubtitlesView={'subtitles:youtube' as SelectedView}
	        youtubeDubView={'subtitles:youtube-dub' as SelectedView}
	        jobMediaView={'job:media' as SelectedView}
	        adminUserManagementView={'admin:users' as SelectedView}
	        adminReadingBedsView={'admin:reading-beds' as SelectedView}
	      />
	    );

    const bodyColor = resolveColor(getComputedStyle(document.body).backgroundColor, [1, 1, 1]);
    const links = Array.from(container.querySelectorAll<HTMLButtonElement>('.sidebar__link'));
    const createBookLink = links.find((link) => link.textContent?.includes('Create Audiobook'));
    const activeLink = links.find((link) => link.classList.contains('is-active'));

    expect(createBookLink).toBeDefined();
    expect(activeLink).toBeDefined();

    const defaultContrast = contrastRatio(
      resolveColor(getComputedStyle(createBookLink!).color),
      resolveColor(getComputedStyle(createBookLink!).backgroundColor, bodyColor)
    );
    const activeContrast = contrastRatio(
      resolveColor(getComputedStyle(activeLink!).color),
      resolveColor(getComputedStyle(activeLink!).backgroundColor, bodyColor)
    );

    expect(defaultContrast).toBeGreaterThanOrEqual(4.5);
    expect(activeContrast).toBeGreaterThanOrEqual(4.5);
  });

  it('maintains card text contrast in magenta mode', () => {
    const { container } = render(
      <div className="auth-card">
        <h1>Welcome back</h1>
        <p>Sign in to continue your work.</p>
      </div>
    );

    const bodyColor = resolveColor(getComputedStyle(document.body).backgroundColor, [1, 1, 1]);
    const card = container.querySelector<HTMLElement>('.auth-card');
    expect(card).toBeTruthy();
    const cardBackground = resolveColor(getComputedStyle(card!).backgroundColor, bodyColor);

    const heading = card!.querySelector<HTMLElement>('h1');
    const paragraph = card!.querySelector<HTMLElement>('p');
    expect(heading).toBeTruthy();
    expect(paragraph).toBeTruthy();

    const headingContrast = contrastRatio(resolveColor(getComputedStyle(heading!).color), cardBackground);
    const paragraphContrast = contrastRatio(resolveColor(getComputedStyle(paragraph!).color), cardBackground);

    expect(headingContrast).toBeGreaterThanOrEqual(4.5);
    expect(paragraphContrast).toBeGreaterThanOrEqual(4.5);
  });

  it('ensures status badges meet contrast requirements in magenta mode', () => {
    const { container } = render(
      <div className="auth-card">
        <span className="job-status" data-state="completed">
          completed
        </span>
        <span className="job-status" data-state="running">
          running
        </span>
        <span className="job-status" data-state="failed">
          failed
        </span>
        <span className="job-status" data-state="pending">
          pending
        </span>
      </div>
    );

    const bodyColor = resolveColor(getComputedStyle(document.body).backgroundColor, [1, 1, 1]);
    const card = container.querySelector<HTMLElement>('.auth-card');
    expect(card).toBeTruthy();
    const cardBackground = resolveColor(getComputedStyle(card!).backgroundColor, bodyColor);

    const states = ['completed', 'running', 'failed', 'pending'] as const;
    for (const state of states) {
      const badge = container.querySelector<HTMLElement>(`.job-status[data-state="${state}"]`);
      expect(badge).toBeTruthy();
      const background = resolveColor(getComputedStyle(badge!).backgroundColor, cardBackground);
      const foreground = resolveColor(getComputedStyle(badge!).color);
      const ratio = contrastRatio(foreground, background);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    }
  });
});
