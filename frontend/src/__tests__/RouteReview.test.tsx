import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DispatchReviewPage } from "../pages/DispatchReviewPage";
import { api } from "../api/client";

vi.mock("../components/RouteMapPreview", () => ({
  RouteMapPreview: () => <div data-testid="route-map-preview">Map preview</div>,
}));

vi.mock("../api/client", () => ({
  api: {
    getDispatchPlan: vi.fn(),
    listEmployees: vi.fn(),
    listJobs: vi.fn(),
    recalculateDispatchRun: vi.fn(),
    exportCsv: vi.fn(),
    manualOverride: vi.fn(),
  },
}));

describe("DispatchReviewPage", () => {
  beforeEach(() => {
    vi.mocked(api.listEmployees).mockResolvedValue([
      {
        id: 1,
        first_name: "Alex",
        last_name: "Driver",
        display_name: "Alex Driver",
        active: true,
        is_driver: true,
        is_supervisor: false,
        default_vehicle_capacity: 4,
        phone: null,
      },
    ]);
    vi.mocked(api.listJobs).mockResolvedValue([
      {
        id: 1,
        job_name: "Demo Job",
        client_name: "C",
        address: "1 St",
        required_arrival_time: "2026-06-15T08:00:00Z",
        required_headcount: 3,
      },
    ]);
    vi.mocked(api.getDispatchPlan).mockResolvedValue({
      dispatch_run_id: 5,
      status: "reviewed",
      assignments: [
        {
          employee_id: 1,
          job_id: 1,
          assigned_skill_id: 1,
          assigned_role: "driver",
          substitution_used: false,
          substitution_reason: null,
          manually_overridden: false,
          warnings: [],
        },
      ],
      vehicle_routes: [
        {
          id: 99,
          job_id: 1,
          driver_employee_id: 1,
          vehicle_capacity: 4,
          passenger_ids: [],
          route_order: 1,
          total_duration_minutes: 10,
          total_distance_miles: 5,
          arrival_time: "2026-06-15T08:00:00Z",
          is_late: false,
          google_maps_url: "https://maps.google.com",
          route_geometry_json: null,
          reasoning: "On time route",
          warnings: [],
          stops: [],
        },
      ],
      warnings: [],
      reasoning_summary: "Assigned Alex",
    });
  });

  it("renders assignments and vehicle routes", async () => {
    render(
      <MemoryRouter initialEntries={["/dispatch/5"]}>
        <Routes>
          <Route path="/dispatch/:id" element={<DispatchReviewPage />} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/Route review/)).toBeInTheDocument();
      expect(screen.getByText(/On time route/)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /google maps/i })).toBeInTheDocument();
      expect(screen.getByTestId("route-map-preview")).toBeInTheDocument();
    });
  });
});
