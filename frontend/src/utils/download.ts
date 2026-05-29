import { setToken } from "../api/client";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function downloadDispatchCsv(runId: number, filename?: string): Promise<void> {
  const token = localStorage.getItem("dispatch_token");
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE}/dispatch-runs/${runId}/export-csv/download`, {
    headers,
  });
  if (response.status === 401) {
    setToken(null);
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new Error(detail || "Download failed");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename ?? `dispatch-run-${runId}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
