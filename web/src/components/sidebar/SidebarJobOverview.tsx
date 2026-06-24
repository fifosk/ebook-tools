import type { JobState } from '../JobList';
import { SidebarJobRow } from './SidebarJobRow';

interface SidebarJobOverviewProps {
  sidebarJobs: JobState[];
  activeJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onOpenPlayer: (jobId?: string, options?: { autoPlay?: boolean }) => void;
}

export function SidebarJobOverview({
  sidebarJobs,
  activeJobId,
  onSelectJob,
  onOpenPlayer
}: SidebarJobOverviewProps) {
  const bookJobs = sidebarJobs.filter((job) =>
    job.status.job_type === 'pipeline' || job.status.job_type === 'book'
  );
  const subtitleJobs = sidebarJobs.filter((job) => job.status.job_type === 'subtitle');
  const youtubeDubJobs = sidebarJobs.filter((job) => job.status.job_type === 'youtube_dub');
  const hasJobOverview = bookJobs.length > 0 || subtitleJobs.length > 0 || youtubeDubJobs.length > 0;

  return (
    <details className="sidebar__section" open>
      <summary>📊 Job Overview</summary>
      <div>
        {!hasJobOverview ? <p className="sidebar__empty">No jobs yet.</p> : null}
        {bookJobs.length > 0 ? (
          <SidebarJobOverviewSection
            title="🎧 Audiobooks"
            jobs={bookJobs}
            activeJobId={activeJobId}
            onSelectJob={onSelectJob}
            onOpenPlayer={onOpenPlayer}
          />
        ) : null}
        {subtitleJobs.length > 0 ? (
          <SidebarJobOverviewSection
            title="🎞️ Subtitles"
            jobs={subtitleJobs}
            activeJobId={activeJobId}
            onSelectJob={onSelectJob}
            onOpenPlayer={onOpenPlayer}
          />
        ) : null}
        {youtubeDubJobs.length > 0 ? (
          <SidebarJobOverviewSection
            title="📺 Videos"
            jobs={youtubeDubJobs}
            activeJobId={activeJobId}
            onSelectJob={onSelectJob}
            onOpenPlayer={onOpenPlayer}
          />
        ) : null}
      </div>
    </details>
  );
}

interface SidebarJobOverviewSectionProps {
  title: string;
  jobs: JobState[];
  activeJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onOpenPlayer: (jobId?: string, options?: { autoPlay?: boolean }) => void;
}

function SidebarJobOverviewSection({
  title,
  jobs,
  activeJobId,
  onSelectJob,
  onOpenPlayer
}: SidebarJobOverviewSectionProps) {
  return (
    <details className="sidebar__section" open>
      <summary>{title}</summary>
      <ul className="sidebar__list">
        {jobs.map((job) => (
          <SidebarJobRow
            key={job.jobId}
            job={job}
            activeJobId={activeJobId}
            onSelectJob={onSelectJob}
            onOpenPlayer={onOpenPlayer}
          />
        ))}
      </ul>
    </details>
  );
}
