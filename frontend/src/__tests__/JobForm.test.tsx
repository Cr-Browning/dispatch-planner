import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { JobFormPage } from "../pages/JobFormPage";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    getJob: vi.fn(),
    createJob: vi.fn(),
    updateJob: vi.fn(),
    listSkills: vi.fn(),
    addJobRequiredSkill: vi.fn(),
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn() };
});

describe("JobFormPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSkills).mockResolvedValue([
      { id: 2, name: "Tile", active: true },
    ]);
  });

  it("shows job details when editing", async () => {
    vi.mocked(api.getJob).mockResolvedValue({
      id: 1,
      job_name: "Flooring Job",
      client_name: "Client B",
      address: "2 Main St",
      latitude: 39.95,
      longitude: -75.16,
      required_arrival_time: "2026-06-15T13:00:00.000Z",
      required_headcount: 3,
      tolls_allowed: true,
      return_trip_enabled: false,
      dropoff_return_enabled: false,
      notes: null,
      required_skills: [
        {
          id: 1,
          skill_id: 2,
          skill_name: "Tile",
          required_quantity: 1,
          minimum_proficiency: 1,
          is_preferred: false,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/jobs/1"]}>
        <Routes>
          <Route path="/jobs/:id" element={<JobFormPage />} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByDisplayValue("Flooring Job")).toBeInTheDocument();
      expect(screen.getByText(/min proficiency 1/)).toBeInTheDocument();
    });
  });

  it("creates a new job with required roles", async () => {
    vi.mocked(api.addJobRequiredSkill).mockResolvedValue({
      id: 1,
      skill_id: 2,
      skill_name: "Tile",
      required_quantity: 1,
      minimum_proficiency: 2,
      is_preferred: false,
    });
    vi.mocked(api.createJob).mockResolvedValue({
      id: 42,
      job_name: "New Site",
      client_name: "ACME",
      address: "100 Market St",
      latitude: 39.95,
      longitude: -75.16,
      required_arrival_time: "2026-07-01T12:00:00.000Z",
      required_headcount: 2,
      tolls_allowed: true,
      return_trip_enabled: false,
      dropoff_return_enabled: false,
      notes: null,
      required_skills: [],
    });

    render(
      <MemoryRouter initialEntries={["/jobs/new"]}>
        <Routes>
          <Route path="/jobs/:id" element={<JobFormPage />} />
          <Route path="/jobs/42" element={<JobFormPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByLabelText(/^role$/i)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/job name/i), { target: { value: "New Site" } });
    fireEvent.change(screen.getByLabelText(/^address$/i), { target: { value: "100 Market St" } });
    fireEvent.change(screen.getByLabelText(/required headcount/i), { target: { value: "2" } });
    const roleSelect = screen.getByLabelText(/^role$/i);
    fireEvent.change(roleSelect, { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText(/min proficiency/i), { target: { value: "2" } });
    await waitFor(() => expect(roleSelect).toHaveValue("2"));
    fireEvent.submit(roleSelect.closest("form")!);
    await waitFor(() => expect(screen.getByText(/Tile × 1/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    await waitFor(() => {
      expect(api.createJob).toHaveBeenCalled();
      expect(api.addJobRequiredSkill).toHaveBeenCalledWith(42, {
        skill_id: 2,
        required_quantity: 1,
        minimum_proficiency: 2,
        is_preferred: false,
      });
      const body = vi.mocked(api.createJob).mock.calls[0][0];
      expect(body.address).toBe("100 Market St");
      expect(body.job_name).toBe("New Site");
    });
  });

  it("requires at least one role before creating", async () => {
    render(
      <MemoryRouter initialEntries={["/jobs/new"]}>
        <Routes>
          <Route path="/jobs/:id" element={<JobFormPage />} />
        </Routes>
      </MemoryRouter>
    );
    fireEvent.change(screen.getByLabelText(/job name/i), { target: { value: "New Site" } });
    fireEvent.change(screen.getByLabelText(/^address$/i), { target: { value: "100 Market St" } });
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));
    await waitFor(() => {
      expect(screen.getByText(/at least one required role/i)).toBeInTheDocument();
      expect(api.createJob).not.toHaveBeenCalled();
    });
  });
});
