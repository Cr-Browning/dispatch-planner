import type {
  AppSettings,
  DispatchCopyTemplate,
  DispatchValidation,
  DispatchRun,
  Employee,
  EmployeeListItem,
  BackupRecord,
  ExportResult,
  Job,
  JobListItem,
  PlanResponse,
  SolveResult,
  Skill,
  SkillWithUsage,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function getToken(): string | null {
  return localStorage.getItem("dispatch_token");
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem("dispatch_token", token);
  } else {
    localStorage.removeItem("dispatch_token");
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (auth) {
    const token = getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    setToken(null);
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new Error(detail || "Request failed");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  login(password: string) {
    return request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }, false);
  },
  health() {
    return request<{ status: string }>("/health", {}, false);
  },
  listEmployees(activeOnly = false) {
    return request<EmployeeListItem[]>(
      `/employees?active_only=${activeOnly}`
    );
  },
  getEmployee(id: number) {
    return request<Employee>(`/employees/${id}`);
  },
  createEmployee(body: Record<string, unknown>) {
    return request<Employee>("/employees", { method: "POST", body: JSON.stringify(body) });
  },
  updateEmployee(id: number, body: Record<string, unknown>) {
    return request<Employee>(`/employees/${id}`, { method: "PUT", body: JSON.stringify(body) });
  },
  deleteEmployee(id: number) {
    return request<void>(`/employees/${id}`, { method: "DELETE" });
  },
  createEmployeeLocation(employeeId: number, body: Record<string, unknown>) {
    return request<Employee["locations"][number]>(`/employees/${employeeId}/locations`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateEmployeeLocation(
    employeeId: number,
    locationId: number,
    body: Record<string, unknown>
  ) {
    return request<Employee["locations"][number]>(
      `/employees/${employeeId}/locations/${locationId}`,
      { method: "PUT", body: JSON.stringify(body) }
    );
  },
  addEmployeeSkill(employeeId: number, body: Record<string, unknown>) {
    return request<Employee["skills"][number]>(`/employees/${employeeId}/skills`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateEmployeeSkill(employeeId: number, skillId: number, body: Record<string, unknown>) {
    return request<Employee["skills"][number]>(`/employees/${employeeId}/skills/${skillId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
  removeEmployeeSkill(employeeId: number, skillId: number) {
    return request<void>(`/employees/${employeeId}/skills/${skillId}`, { method: "DELETE" });
  },
  listSkills(activeOnly = true, withUsage = false) {
    return request<Skill[] | SkillWithUsage[]>(
      `/skills?active_only=${activeOnly}&with_usage=${withUsage}`
    );
  },
  createSkill(body: Record<string, unknown>) {
    return request<Skill>("/skills", { method: "POST", body: JSON.stringify(body) });
  },
  listJobs() {
    return request<JobListItem[]>("/jobs");
  },
  getJob(id: number) {
    return request<Job>(`/jobs/${id}`);
  },
  createJob(body: Record<string, unknown>) {
    return request<Job>("/jobs", { method: "POST", body: JSON.stringify(body) });
  },
  updateJob(id: number, body: Record<string, unknown>) {
    return request<Job>(`/jobs/${id}`, { method: "PUT", body: JSON.stringify(body) });
  },
  addJobRequiredSkill(jobId: number, body: Record<string, unknown>) {
    return request<Job["required_skills"][number]>(`/jobs/${jobId}/required-skills`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  removeJobRequiredSkill(jobId: number, requiredSkillId: number) {
    return request<void>(`/jobs/${jobId}/required-skills/${requiredSkillId}`, {
      method: "DELETE",
    });
  },
  deleteJob(id: number) {
    return request<void>(`/jobs/${id}`, { method: "DELETE" });
  },
  duplicateJob(id: number, body: { run_date?: string; job_name_suffix?: string } = {}) {
    return request<Job>(`/jobs/${id}/duplicate`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  validateDispatchSelection(body: { run_date: string; job_ids: number[] }) {
    return request<DispatchValidation>("/dispatch-runs/validate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  listDispatchRuns() {
    return request<DispatchRun[]>("/dispatch-runs");
  },
  createDispatchRun(body: Record<string, unknown>) {
    return request<DispatchRun>("/dispatch-runs", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  getDispatchCopyTemplate(targetRunDate?: string) {
    const query = targetRunDate ? `?target_run_date=${targetRunDate}` : "";
    return request<DispatchCopyTemplate>(`/dispatch-runs/copy-template${query}`);
  },
  solveDispatchRun(id: number) {
    return request<SolveResult>(`/dispatch-runs/${id}/solve`, { method: "POST" });
  },
  getDispatchPlan(id: number) {
    return request<PlanResponse>(`/dispatch-runs/${id}/plan`);
  },
  recalculateDispatchRun(id: number) {
    return request<PlanResponse>(`/dispatch-runs/${id}/recalculate`, { method: "POST" });
  },
  manualOverride(id: number, body: Record<string, unknown>) {
    return request<PlanResponse>(`/dispatch-runs/${id}/manual-override`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  reassignDispatchJob(runId: number, jobId: number) {
    return request<PlanResponse>(`/dispatch-runs/${runId}/jobs/${jobId}/reassign`, {
      method: "POST",
    });
  },
  exportCsv(id: number) {
    return request<ExportResult>(`/dispatch-runs/${id}/export-csv`, { method: "POST" });
  },
  getSettings() {
    return request<AppSettings>("/settings");
  },
  updateSettings() {
    return request<AppSettings>("/settings", { method: "PUT", body: "{}" });
  },
  listBackups() {
    return request<BackupRecord[]>("/backups");
  },
  createBackup(notes?: string) {
    const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
    return request<BackupRecord>(`/backups${query}`, { method: "POST" });
  },
  restoreBackup(id: number) {
    return request<void>(`/backups/${id}/restore`, { method: "POST" });
  },
};
