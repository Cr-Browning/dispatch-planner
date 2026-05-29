import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { EmployeeListItem, JobListItem, PlanResponse } from "../api/types";
import { RouteMapPreview } from "../components/RouteMapPreview";
import { downloadDispatchCsv } from "../utils/download";
import { formatDisplayTime } from "../utils/dates";

export function DispatchReviewPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const runId = Number(id);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(() => {
    if (searchParams.get("exported") === "1") {
      const rows = searchParams.get("rows");
      return rows ? `CSV downloaded (${rows} rows).` : "CSV downloaded.";
    }
    return null;
  });
  const [exporting, setExporting] = useState(false);
  const [needsRecalculate, setNeedsRecalculate] = useState(false);
  const [reassigningJobId, setReassigningJobId] = useState<number | null>(null);
  const [moveEmployeeId, setMoveEmployeeId] = useState("");
  const [moveJobId, setMoveJobId] = useState("");
  const [reorderRouteId, setReorderRouteId] = useState("");
  const [reorderIds, setReorderIds] = useState("");

  const runJobIds = useMemo(() => {
    if (!plan) return new Set<number>();
    return new Set(plan.assignments.map((a) => a.job_id));
  }, [plan]);

  function load() {
    return api.getDispatchPlan(runId).then(setPlan).catch((e) => {
      setError(e.message);
    });
  }

  useEffect(() => {
    load();
    api.listEmployees(true).then(setEmployees);
    api.listJobs().then(setJobs);
  }, [runId]);

  async function handleRecalculate() {
    setError(null);
    try {
      const result = await api.recalculateDispatchRun(runId);
      setPlan(result);
      setNeedsRecalculate(false);
      setExportMsg(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recalculate failed");
    }
  }

  async function handleExport() {
    if (needsRecalculate) {
      setError("Recalculate routes after manual changes before exporting.");
      return;
    }
    setExporting(true);
    setError(null);
    try {
      const result = await api.exportCsv(runId);
      await downloadDispatchCsv(runId);
      setExportMsg(`Downloaded CSV (${result.row_count} rows).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleMoveAssignment(e: FormEvent) {
    e.preventDefault();
    if (!moveEmployeeId || !moveJobId) return;
    setError(null);
    try {
      const result = await api.manualOverride(runId, {
        move_assignment: {
          employee_id: Number(moveEmployeeId),
          to_job_id: Number(moveJobId),
          assigned_role: "worker",
        },
      });
      setPlan(result);
      setNeedsRecalculate(true);
      setExportMsg(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Override failed");
    }
  }

  async function handleReorder(e: FormEvent) {
    e.preventDefault();
    const pickupIds = reorderIds.split(",").map((s) => Number(s.trim())).filter(Boolean);
    if (!reorderRouteId || pickupIds.length === 0) return;
    setError(null);
    try {
      const result = await api.manualOverride(runId, {
        reorder_pickups: {
          vehicle_route_id: Number(reorderRouteId),
          pickup_employee_ids: pickupIds,
        },
      });
      setPlan(result);
      setNeedsRecalculate(true);
      setExportMsg(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reorder failed");
    }
  }

  async function handleReassignJob(jobId: number) {
    if (!window.confirm("Re-run assignment for this job only? Other jobs stay as-is.")) {
      return;
    }
    setReassigningJobId(jobId);
    setError(null);
    try {
      const result = await api.reassignDispatchJob(runId, jobId);
      setPlan(result);
      setNeedsRecalculate(false);
      setExportMsg(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reassign failed");
    } finally {
      setReassigningJobId(null);
    }
  }

  if (!plan) {
    return <p>{error ?? "Loading plan…"}</p>;
  }

  const employeeName = (empId: number) => {
    const emp = employees.find((e) => e.id === empId);
    return emp?.display_name ?? (emp ? `${emp.first_name} ${emp.last_name}` : `#${empId}`);
  };

  const jobName = (jobId: number) =>
    jobs.find((j) => j.id === jobId)?.job_name ?? `Job ${jobId}`;

  const hasManualOverrides = plan.assignments.some((a) => a.manually_overridden);

  return (
    <>
      <div className="page-header">
        <h2>Route review — run #{runId}</h2>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" className="btn secondary" onClick={handleRecalculate}>
            Recalculate all routes
          </button>
          <button
            type="button"
            className="btn"
            onClick={handleExport}
            disabled={exporting || needsRecalculate}
            title={
              needsRecalculate
                ? "Recalculate after manual changes before exporting"
                : undefined
            }
          >
            {exporting ? "Exporting…" : "Download CSV"}
          </button>
          <Link to="/dispatch" className="btn secondary">
            New dispatch
          </Link>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {exportMsg && <p className="card">{exportMsg}</p>}
      {(needsRecalculate || hasManualOverrides) && (
        <div className="card" style={{ borderColor: "var(--warning)" }}>
          <strong>Routes may be stale.</strong> Manual changes were applied. Click{" "}
          <strong>Recalculate all routes</strong> before downloading CSV so ETAs and pickup
          order match assignments.
        </div>
      )}
      {plan.warnings.length > 0 && (
        <div className="card">
          <h3>Warnings</h3>
          <ul className="warning-list">
            {plan.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {plan.reasoning_summary && (
        <div className="card">
          <h3>Assignment reasoning</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: "0.85rem" }}>
            {plan.reasoning_summary}
          </pre>
        </div>
      )}
      <div className="card">
        <h3>Assignments</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Job</th>
              <th>Role</th>
              <th>Substitution</th>
              <th>Manual</th>
            </tr>
          </thead>
          <tbody>
            {plan.assignments.map((a) => (
              <tr key={`${a.employee_id}-${a.job_id}`}>
                <td>{employeeName(a.employee_id)}</td>
                <td>{jobName(a.job_id)}</td>
                <td>{a.assigned_role}</td>
                <td>{a.substitution_used ? "Yes" : "No"}</td>
                <td>{a.manually_overridden ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Re-solve single job</h3>
        <p className="form-hint">
          Re-run crew assignment for one site without changing other jobs.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {Array.from(runJobIds).map((jobId) => (
            <button
              key={jobId}
              type="button"
              className="btn secondary"
              disabled={reassigningJobId !== null}
              onClick={() => handleReassignJob(jobId)}
            >
              {reassigningJobId === jobId ? "Working…" : `Re-solve ${jobName(jobId)}`}
            </button>
          ))}
        </div>
      </div>
      {plan.vehicle_routes.map((route) => (
        <div className="card" key={route.id}>
          <h3>
            Vehicle {route.route_order} — {jobName(route.job_id)}{" "}
            {route.is_late ? (
              <span className="badge late">Late</span>
            ) : (
              <span className="badge ok">On time</span>
            )}
          </h3>
          <p>
            Driver: {employeeName(route.driver_employee_id)} | Capacity: {route.vehicle_capacity}{" "}
            | {route.total_duration_minutes?.toFixed(1)} min /{" "}
            {route.total_distance_miles?.toFixed(2)} mi
          </p>
          {route.reasoning && <p>{route.reasoning}</p>}
          {route.google_maps_url && (
            <p>
              <a href={route.google_maps_url} target="_blank" rel="noreferrer">
                Open in Google Maps
              </a>
            </p>
          )}
          <table className="data-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Type</th>
                <th>Employee</th>
                <th>ETA</th>
                <th>Ride (min)</th>
              </tr>
            </thead>
            <tbody>
              {route.stops.map((stop) => (
                <tr key={stop.stop_order}>
                  <td>{stop.stop_order}</td>
                  <td>{stop.stop_type}</td>
                  <td>{stop.employee_id ? employeeName(stop.employee_id) : "—"}</td>
                  <td>{stop.eta ? formatDisplayTime(stop.eta) : "—"}</td>
                  <td>{stop.ride_time_minutes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <div className="card">
        <h3>Map preview</h3>
        <RouteMapPreview
          routes={plan.vehicle_routes}
          employeeName={employeeName}
          jobName={jobName}
        />
      </div>
      <div className="card">
        <h3>Manual override — move assignment</h3>
        <form className="form-grid" onSubmit={handleMoveAssignment}>
          <label>
            Employee
            <select
              value={moveEmployeeId}
              onChange={(e) => setMoveEmployeeId(e.target.value)}
              required
            >
              <option value="">Select…</option>
              {plan.assignments.map((a) => (
                <option key={a.employee_id} value={a.employee_id}>
                  {employeeName(a.employee_id)}
                </option>
              ))}
            </select>
          </label>
          <label>
            To job
            <select value={moveJobId} onChange={(e) => setMoveJobId(e.target.value)} required>
              <option value="">Select…</option>
              {jobs
                .filter((j) => runJobIds.has(j.id))
                .map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.job_name}
                  </option>
                ))}
            </select>
          </label>
          <button type="submit" className="btn">
            Apply move
          </button>
        </form>
      </div>
      <div className="card">
        <h3>Manual override — reorder pickups</h3>
        <form className="form-grid" onSubmit={handleReorder}>
          <label>
            Vehicle route ID
            <select
              value={reorderRouteId}
              onChange={(e) => setReorderRouteId(e.target.value)}
              required
            >
              <option value="">Select…</option>
              {plan.vehicle_routes.map((r) => (
                <option key={r.id} value={r.id}>
                  Route {r.route_order} (id {r.id})
                </option>
              ))}
            </select>
          </label>
          <label>
            Pickup employee IDs (comma-separated)
            <input
              value={reorderIds}
              onChange={(e) => setReorderIds(e.target.value)}
              placeholder="e.g. 3, 5, 4"
              required
            />
          </label>
          <button type="submit" className="btn">
            Reorder pickups
          </button>
        </form>
      </div>
    </>
  );
}
