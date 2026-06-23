import type { SubtitleOutputFormat } from './subtitleToolTypes';

export type SubmittedSubtitleSummary = {
  jobId: string;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
  startTime: string;
  defaultStartTime: string;
  endTime: string | null;
  model: string | null;
  format: SubtitleOutputFormat | null;
  assFontSize: number | null;
  assEmphasis: number | null;
};

export function formatSubmittedSubtitleSummary(summary: SubmittedSubtitleSummary): string {
  const details: string[] = [];
  if (summary.workerCount) {
    details.push(`${summary.workerCount} thread${summary.workerCount === 1 ? '' : 's'}`);
  }
  if (summary.batchSize) {
    details.push(`batch size ${summary.batchSize}`);
  }
  if (summary.translationBatchSize) {
    details.push(`LLM batch ${summary.translationBatchSize}`);
  }
  if (summary.startTime && summary.startTime !== summary.defaultStartTime) {
    details.push(`starting at ${summary.startTime}`);
  }
  if (summary.endTime) {
    const display = summary.endTime.startsWith('+')
      ? `ending after ${summary.endTime.slice(1)}`
      : `ending at ${summary.endTime}`;
    details.push(display);
  }
  if (summary.model) {
    details.push(`LLM ${summary.model}`);
  }
  if (summary.format) {
    const label = summary.format === 'ass' ? 'ASS subtitles' : 'SRT subtitles';
    details.push(label);
    if (summary.format === 'ass' && summary.assFontSize) {
      details.push(`font size ${summary.assFontSize}`);
    }
    if (summary.format === 'ass' && summary.assEmphasis) {
      details.push(`scale ${summary.assEmphasis}\u00d7`);
    }
  }
  if (details.length === 0) {
    return `Submitted subtitle job ${summary.jobId} using auto-detected concurrency. Live status appears in the Jobs tab.`;
  }
  const detailText =
    details.length === 1
      ? details[0]
      : `${details.slice(0, -1).join(', ')} and ${details[details.length - 1]}`;
  return `Submitted subtitle job ${summary.jobId} using ${detailText}. Live status appears in the Jobs tab.`;
}
