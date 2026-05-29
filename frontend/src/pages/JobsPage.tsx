import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { JobListItem } from "../api/types";
import { confirmDeleteJob } from "../utils/jobActions";
import { formatDisplayDateTime } from "../utils/dates";

export function JobsPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    api
      .listJobs()
      .then(setJobs)
      .catch((e) => setError(e.message));
  }, []);

  async function handleDelete(job: JobListItem) {
    if (!confirmDeleteJob(job)) {
      return;
    }
    setDeletingId(job.id);
    setError(null);
    try {
      await api.deleteJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Jobs</h2>
        <Link to="/jobs/new" className="btn">
          Add job
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Client</th>
              <th>Roles</th>
              <th>Arrival</th>
              <th>Headcount</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.job_name}</td>
                <td>{job.client_name}</td>
                <td>{job.roles_summary ?? "—"}</td>
                <td>{formatDisplayDateTime(job.required_arrival_time)}</td>
                <td>{job.required_headcount}</td>
                <td className="table-actions">
                  <Link to={`/jobs/${job.id}`}>Edit</Link>
                  <button
                    type="button"
                    className="btn-link danger"
                    disabled={deletingId === job.id}
                    onClick={() => handleDelete(job)}
                  >
                    {deletingId === job.id ? "Deleting…" : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
