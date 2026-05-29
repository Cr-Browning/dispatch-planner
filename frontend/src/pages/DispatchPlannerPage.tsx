import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { DispatchValidation, JobListItem } from "../api/types";
import { confirmDeleteJob } from "../utils/jobActions";
import {
  defaultDispatchName,
  formatDisplayDate,
  formatDisplayDateTime,
  jobLocalDateIso,
  todayIsoDate,
} from "../utils/dates";
import { downloadDispatchCsv } from "../utils/download";

function initialRunDate(searchParams: URLSearchParams): string {
  const param = searchParams.get("date");
  if (param && /^\d{4}-\d{2}-\d{2}$/.test(param)) {
    return param;
  }
  return todayIsoDate();
}

export function DispatchPlannerPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [runDate, setRunDate] = useState(() => initialRunDate(searchParams));
  const [name, setName] = useState(() => defaultDispatchName(initialRunDate(searchParams)));
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copying, setCopying] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [validation, setValidation] = useState<DispatchValidation | null>(null);
  const [validating, setValidating] = useState(false);
  const validateTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function loadJobs() {
    return api
      .listJobs()
      .then(setJobs)
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadJobs();
  }, []);

  useEffect(() => {
    if (validateTimer.current) {
      clearTimeout(validateTimer.current);
    }
    if (selected.size === 0) {
      setValidation(null);
      return;
    }
    validateTimer.current = setTimeout(() => {
      setValidating(true);
      api
        .validateDispatchSelection({
          run_date: runDate,
          job_ids: Array.from(selected),
        })
        .then(setValidation)
        .catch(() => setValidation(null))
        .finally(() => setValidating(false));
    }, 300);
    return () => {
      if (validateTimer.current) {
        clearTimeout(validateTimer.current);
      }
    };
  }, [runDate, selected]);

  function onRunDateChange(value: string) {
    setRunDate(value);
    setName(defaultDispatchName(value));
    setSelected(new Set());
    setInfo(null);
  }

  const jobsForDay = jobs.filter(
    (job) => jobLocalDateIso(job.required_arrival_time) === runDate
  );

  function toggleJob(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function selectAllForDay() {
    setSelected(new Set(jobsForDay.map((j) => j.id)));
    setInfo(`Selected ${jobsForDay.length} job(s) for ${formatDisplayDate(runDate)}.`);
  }

  function clearSelection() {
    setSelected(new Set());
  }

  async function handleCopyPrevious() {
    setCopying(true);
    setError(null);
    setInfo(null);
    try {
      const template = await api.getDispatchCopyTemplate(runDate);
      const onDateIds = template.job_ids_on_run_date ?? template.job_ids;
      setSelected(new Set(onDateIds));
      setRunDate(template.suggested_run_date);
      setName(template.suggested_name);
      const offCount = (template.job_ids_off_run_date ?? []).length;
      let message = `Copied ${template.job_ids.length} job(s) from "${template.source_run_name}" (${formatDisplayDate(template.source_run_date)}). `;
      message += `${template.jobs_on_run_date_count ?? onDateIds.length} scheduled for ${formatDisplayDate(template.suggested_run_date)}.`;
      if (offCount > 0) {
        message += ` ${offCount} job(s) are on other dates — edit arrival times or pick another date.`;
      }
      setInfo(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not copy previous run");
    } finally {
      setCopying(false);
    }
  }

  async function handleDelete(job: JobListItem) {
    if (!confirmDeleteJob(job)) {
      return;
    }
    setDeletingId(job.id);
    setError(null);
    try {
      await api.deleteJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(job.id);
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  async function runDispatch(downloadCsv: boolean) {
    if (selected.size === 0) {
      setError("Select at least one job");
      return;
    }
    if (validation && !validation.ready) {
      setError("Fix validation errors before solving.");
      return;
    }
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const run = await api.createDispatchRun({
        run_date: runDate,
        name,
        job_ids: Array.from(selected),
      });
      await api.solveDispatchRun(run.id);
      if (downloadCsv) {
        const exportResult = await api.exportCsv(run.id);
        await downloadDispatchCsv(run.id);
        navigate(`/dispatch/${run.id}?exported=1&rows=${exportResult.row_count}`);
      } else {
        navigate(`/dispatch/${run.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Solve failed");
    } finally {
      setLoading(false);
    }
  }

  function handleSolveOnly(e: FormEvent) {
    e.preventDefault();
    void runDispatch(false);
  }

  function handleSolveAndExport(e: FormEvent) {
    e.preventDefault();
    void runDispatch(true);
  }

  const allDaySelected =
    jobsForDay.length > 0 && jobsForDay.every((j) => selected.has(j.id));

  return (
    <>
      <div className="page-header">
        <h2>Daily dispatch planner</h2>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn secondary"
            disabled={copying || loading}
            onClick={handleCopyPrevious}
          >
            {copying ? "Copying…" : "Copy last run's jobs"}
          </button>
          <Link to={`/jobs/new?date=${runDate}`} className="btn">
            Add job
          </Link>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {info && <p className="card">{info}</p>}
      {selected.size > 0 && (
        <div className="card validation-panel">
          <h3 style={{ marginTop: 0 }}>Pre-solve checks</h3>
          {validating && <p className="form-hint">Checking selection…</p>}
          {!validating && validation && (
            <>
              <p style={{ margin: "0 0 0.5rem" }}>
                {validation.ready ? (
                  <strong>Ready to solve</strong>
                ) : (
                  <strong className="error">Not ready — fix errors below</strong>
                )}
              </p>
              {validation.issues.length > 0 && (
                <ul className="warning-list">
                  {validation.issues.map((issue, index) => (
                    <li
                      key={`${issue.level}-${index}`}
                      style={issue.level === "error" ? { color: "var(--danger)" } : undefined}
                    >
                      {issue.message}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      )}
      <div className="card form-grid">
        <label>
          Run date
          <input
            type="date"
            value={runDate}
            onChange={(e) => onRunDateChange(e.target.value)}
            required
          />
        </label>
        <label>
          Run name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
      </div>
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <h3 style={{ margin: 0 }}>Select jobs for {formatDisplayDate(runDate)}</h3>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              className="btn secondary"
              disabled={jobsForDay.length === 0 || loading}
              onClick={selectAllForDay}
            >
              Select all for this date
            </button>
            {selected.size > 0 && (
              <button type="button" className="btn-link" onClick={clearSelection}>
                Clear selection
              </button>
            )}
          </div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  aria-label="Select all jobs for this date"
                  checked={allDaySelected}
                  disabled={jobsForDay.length === 0}
                  onChange={() => (allDaySelected ? clearSelection() : selectAllForDay())}
                />
              </th>
              <th>Job</th>
              <th>Client</th>
              <th>Roles</th>
              <th>Arrival</th>
              <th>Headcount</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={7}>
                  No jobs yet.{" "}
                  <Link to={`/jobs/new?date=${runDate}`}>Add a job</Link> to start planning.
                </td>
              </tr>
            )}
            {jobs.length > 0 && jobsForDay.length === 0 && (
              <tr>
                <td colSpan={7}>
                  No jobs scheduled for {formatDisplayDate(runDate)}.{" "}
                  <Link to={`/jobs/new?date=${runDate}`}>Add a job</Link> or pick another date.
                </td>
              </tr>
            )}
            {jobsForDay.map((job) => (
              <tr key={job.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(job.id)}
                    onChange={() => toggleJob(job.id)}
                  />
                </td>
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
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1rem" }}>
        <button
          type="button"
          className="btn"
          disabled={loading || copying || (validation !== null && !validation.ready)}
          onClick={handleSolveOnly}
        >
          {loading ? "Working…" : "Create & solve"}
        </button>
        <button
          type="button"
          className="btn secondary"
          disabled={loading || copying || (validation !== null && !validation.ready)}
          onClick={handleSolveAndExport}
        >
          {loading ? "Working…" : "Create, solve & download CSV"}
        </button>
      </div>
    </>
  );
}
