import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DispatchRun, JobListItem } from "../api/types";
import {
  formatDisplayDate,
  jobLocalDateIso,
  todayIsoDate,
  tomorrowIsoDate,
  weekDatesFrom,
} from "../utils/dates";

type DayBriefingProps = {
  title: string;
  date: string;
  jobs: JobListItem[];
  runs: DispatchRun[];
};

function DayBriefing({ title, date, jobs, runs }: DayBriefingProps) {
  const dayJobs = jobs.filter((j) => jobLocalDateIso(j.required_arrival_time) === date);
  const dayRuns = runs.filter((r) => r.run_date === date);
  const jobsWithoutRoles = dayJobs.filter((j) => !j.roles_summary || j.roles_summary === "—");

  return (
    <div className="card">
      <h3>
        {title} — {formatDisplayDate(date)}
      </h3>
      <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.25rem" }}>
        <li>
          <strong>{dayJobs.length}</strong> job(s) scheduled
          {dayJobs.length > 0 && (
            <>
              {" "}
              (
              <Link to={`/dispatch?date=${date}`}>open planner</Link>)
            </>
          )}
        </li>
        <li>
          <strong>{dayRuns.length}</strong> dispatch run(s)
          {dayRuns.length > 0 && (
            <>
              {" "}
              —{" "}
              {dayRuns.map((r, i) => (
                <span key={r.id}>
                  {i > 0 && ", "}
                  <Link to={`/dispatch/${r.id}`}>{r.name}</Link> ({r.status})
                </span>
              ))}
            </>
          )}
        </li>
        {jobsWithoutRoles.length > 0 && (
          <li className="warning-list">
            <strong>{jobsWithoutRoles.length}</strong> job(s) missing required roles —{" "}
            {jobsWithoutRoles.map((j, i) => (
              <span key={j.id}>
                {i > 0 && ", "}
                <Link to={`/jobs/${j.id}`}>{j.job_name ?? `Job ${j.id}`}</Link>
              </span>
            ))}
          </li>
        )}
        {dayJobs.length === 0 && (
          <li>
            No jobs for {title.toLowerCase()}. <Link to={`/jobs/new?date=${date}`}>Add a job</Link>
          </li>
        )}
      </ul>
    </div>
  );
}

function WeekAtAGlance({
  jobs,
  runs,
  startDate,
}: {
  jobs: JobListItem[];
  runs: DispatchRun[];
  startDate: string;
}) {
  const dates = weekDatesFrom(startDate, 7);

  return (
    <div className="card">
      <h3>Week at a glance</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Jobs</th>
            <th>Dispatch runs</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {dates.map((date) => {
            const jobCount = jobs.filter(
              (j) => jobLocalDateIso(j.required_arrival_time) === date
            ).length;
            const dayRuns = runs.filter((r) => r.run_date === date);
            return (
              <tr key={date}>
                <td>{formatDisplayDate(date)}</td>
                <td>{jobCount}</td>
                <td>
                  {dayRuns.length === 0
                    ? "—"
                    : dayRuns.map((r, i) => (
                        <span key={r.id}>
                          {i > 0 && ", "}
                          <Link to={`/dispatch/${r.id}`}>{r.name}</Link> ({r.status})
                        </span>
                      ))}
                </td>
                <td>
                  <Link to={`/dispatch?date=${date}`}>Plan</Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function DashboardPage() {
  const [runs, setRuns] = useState<DispatchRun[]>([]);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [view, setView] = useState<"table" | "calendar">("table");
  const [error, setError] = useState<string | null>(null);
  const today = todayIsoDate();
  const tomorrow = tomorrowIsoDate();

  useEffect(() => {
    Promise.all([api.listDispatchRuns(), api.listJobs()])
      .then(([runList, jobList]) => {
        setRuns(runList);
        setJobs(jobList);
      })
      .catch((e) => setError(e.message));
  }, []);

  const byDate = useMemo(
    () =>
      runs.reduce<Record<string, DispatchRun[]>>((acc, run) => {
        const key = run.run_date;
        acc[key] = acc[key] ?? [];
        acc[key].push(run);
        return acc;
      }, {}),
    [runs]
  );

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <Link to={`/dispatch?date=${today}`} className="btn">
            Plan today&apos;s dispatch
          </Link>
          <Link to={`/dispatch?date=${tomorrow}`} className="btn secondary">
            Plan tomorrow
          </Link>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <DayBriefing title="Today" date={today} jobs={jobs} runs={runs} />
      <DayBriefing title="Tomorrow" date={tomorrow} jobs={jobs} runs={runs} />
      <WeekAtAGlance jobs={jobs} runs={runs} startDate={today} />
      <div className="view-toggle">
        <button
          type="button"
          className={`btn secondary ${view === "table" ? "active" : ""}`}
          onClick={() => setView("table")}
        >
          Table view
        </button>
        <button
          type="button"
          className={`btn secondary ${view === "calendar" ? "active" : ""}`}
          onClick={() => setView("calendar")}
        >
          Calendar view
        </button>
      </div>
      {view === "table" ? (
        <div className="card">
          <h3>Route history</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Name</th>
                <th>Status</th>
                <th>Jobs</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{formatDisplayDate(run.run_date)}</td>
                  <td>{run.name}</td>
                  <td>
                    <span className="badge">{run.status}</span>
                  </td>
                  <td>{run.job_ids.length}</td>
                  <td>
                    <Link to={`/dispatch/${run.id}`}>View plan</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card">
          <h3>By date</h3>
          {Object.entries(byDate).map(([date, dayRuns]) => (
            <div key={date} style={{ marginBottom: "1rem" }}>
              <strong>{formatDisplayDate(date)}</strong>
              <ul>
                {dayRuns.map((run) => (
                  <li key={run.id}>
                    <Link to={`/dispatch/${run.id}`}>{run.name}</Link> ({run.status})
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
