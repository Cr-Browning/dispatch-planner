import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DispatchPlannerPage } from "../pages/DispatchPlannerPage";
import { api } from "../api/client";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../api/client", () => ({
  api: {
    listJobs: vi.fn(),
    deleteJob: vi.fn(),
    getDispatchCopyTemplate: vi.fn(),
    createDispatchRun: vi.fn(),
    solveDispatchRun: vi.fn(),
    exportCsv: vi.fn(),
    validateDispatchSelection: vi.fn(),
  },
}));

vi.mock("../utils/download", () => ({
  downloadDispatchCsv: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../utils/dates", async () => {
  const actual = await vi.importActual<typeof import("../utils/dates")>("../utils/dates");
  return {
    ...actual,
    todayIsoDate: () => "2026-06-15",
  };
});

vi.stubGlobal("confirm", vi.fn(() => true));

function jobRowCheckbox() {
  const boxes = screen.getAllByRole("checkbox");
  return boxes[boxes.length - 1];
}

describe("DispatchPlannerPage", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    vi.mocked(api.validateDispatchSelection).mockResolvedValue({
      ready: true,
      issues: [],
    });
    vi.mocked(api.listJobs).mockResolvedValue([
      {
        id: 1,
        job_name: "Job A",
        client_name: "Client",
        address: "1 St",
        required_arrival_time: "2026-06-15T08:00:00Z",
        required_headcount: 3,
      },
    ]);
    vi.mocked(api.createDispatchRun).mockResolvedValue({
      id: 10,
      run_date: "2026-06-15",
      name: "Test",
      status: "draft",
      optimization_profile_id: null,
      reasoning_summary: null,
      job_ids: [1],
    });
    vi.mocked(api.solveDispatchRun).mockResolvedValue({
      dispatch_run_id: 10,
      status: "reviewed",
      assignments: [],
      vehicle_routes: [],
      warnings: [],
      reasoning_summary: "",
      route_reasoning_summary: "",
    });
    vi.mocked(api.exportCsv).mockResolvedValue({
      dispatch_run_id: 10,
      export_record_id: 1,
      file_path: "/tmp/x.csv",
      row_count: 5,
    });
  });

  it("copies jobs from previous run", async () => {
    vi.mocked(api.getDispatchCopyTemplate).mockResolvedValue({
      source_run_id: 2,
      source_run_name: "Yesterday",
      source_run_date: "2026-06-14",
      job_ids: [1],
      job_ids_on_run_date: [1],
      job_ids_off_run_date: [],
      jobs_on_run_date_count: 1,
      suggested_run_date: "2026-06-15",
      suggested_name: "Dispatch — 06-15-2026",
    });
    render(
      <MemoryRouter>
        <DispatchPlannerPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Job A")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /copy last run/i }));
    await waitFor(() => {
      expect(jobRowCheckbox()).toBeChecked();
      expect(screen.getByText(/Copied 1 job/i)).toBeInTheDocument();
    });
  });

  it("clears selection and filters jobs when run date changes", async () => {
    vi.mocked(api.listJobs).mockResolvedValue([
      {
        id: 1,
        job_name: "Job A",
        client_name: "Client",
        address: "1 St",
        required_arrival_time: "2026-06-15T08:00:00Z",
        required_headcount: 3,
      },
      {
        id: 2,
        job_name: "Job B",
        client_name: "Client",
        address: "2 St",
        required_arrival_time: "2026-06-16T08:00:00Z",
        required_headcount: 2,
      },
    ]);
    render(
      <MemoryRouter>
        <DispatchPlannerPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Job A")).toBeInTheDocument());
    fireEvent.click(jobRowCheckbox());
    expect(jobRowCheckbox()).toBeChecked();
    fireEvent.change(screen.getByLabelText(/run date/i), { target: { value: "2026-06-16" } });
    await waitFor(() => {
      expect(screen.queryByText("Job A")).not.toBeInTheDocument();
      expect(screen.getByText("Job B")).toBeInTheDocument();
      expect(jobRowCheckbox()).not.toBeChecked();
    });
  });

  it("create and solve navigates without export", async () => {
    render(
      <MemoryRouter>
        <DispatchPlannerPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Job A")).toBeInTheDocument());
    fireEvent.click(jobRowCheckbox());
    fireEvent.click(screen.getByRole("button", { name: /^create & solve$/i }));
    await waitFor(() => {
      expect(api.createDispatchRun).toHaveBeenCalled();
      expect(api.solveDispatchRun).toHaveBeenCalledWith(10);
      expect(api.exportCsv).not.toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith("/dispatch/10");
    });
  });

  it("creates, solves, exports, and navigates", async () => {
    render(
      <MemoryRouter>
        <DispatchPlannerPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Job A")).toBeInTheDocument());
    fireEvent.click(jobRowCheckbox());
    fireEvent.click(screen.getByRole("button", { name: /create, solve & download/i }));
    await waitFor(() => {
      expect(api.createDispatchRun).toHaveBeenCalled();
      expect(api.solveDispatchRun).toHaveBeenCalledWith(10);
      expect(api.exportCsv).toHaveBeenCalledWith(10);
      expect(mockNavigate).toHaveBeenCalledWith("/dispatch/10?exported=1&rows=5");
    });
  });
});
