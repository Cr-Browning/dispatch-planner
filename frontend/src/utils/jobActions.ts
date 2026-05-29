import type { JobListItem } from "../api/types";

export function confirmDeleteJob(job: JobListItem): boolean {
  const label = job.job_name ?? job.client_name ?? `Job #${job.id}`;
  return window.confirm(`Delete "${label}"? This removes the job from your list and cannot be undone.`);
}
