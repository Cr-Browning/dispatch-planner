import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { EmployeeFormPage } from "../pages/EmployeeFormPage";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    getEmployee: vi.fn(),
    createEmployee: vi.fn(),
    updateEmployee: vi.fn(),
    createEmployeeLocation: vi.fn(),
    updateEmployeeLocation: vi.fn(),
    listSkills: vi.fn(),
    addEmployeeSkill: vi.fn(),
    updateEmployeeSkill: vi.fn(),
    removeEmployeeSkill: vi.fn(),
    createSkill: vi.fn(),
  },
}));

vi.stubGlobal("confirm", vi.fn(() => true));

const employeeFixture = {
  id: 1,
  first_name: "Alex",
  last_name: "Driver",
  display_name: "Alex Driver",
  active: true,
  is_driver: true,
  is_supervisor: false,
      default_vehicle_capacity: 4,
      phone: "215-555-0100",
      notes: null,
  locations: [
    {
      id: 10,
      label: "Home",
      address: "100 Market St",
      latitude: 39.95,
      longitude: -75.16,
      is_primary: true,
    },
  ],
  skills: [{ id: 1, skill_id: 1, proficiency: 3, skill_name: "Demo" }],
};

describe("EmployeeFormPage", () => {
  beforeEach(() => {
    vi.mocked(api.listSkills).mockResolvedValue([
      { id: 1, name: "Demo", active: true },
      { id: 2, name: "Tile", active: true },
    ]);
    vi.mocked(api.getEmployee).mockResolvedValue(employeeFixture);
    vi.mocked(api.updateEmployeeLocation).mockResolvedValue(employeeFixture.locations[0]);
  });

  it("shows address, flags, and editable skills from loaded employee", async () => {
    render(
      <MemoryRouter initialEntries={["/employees/1"]}>
        <Routes>
          <Route path="/employees/:id" element={<EmployeeFormPage />} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByDisplayValue("100 Market St")).toBeInTheDocument();
      expect(screen.getByRole("checkbox", { name: /active/i })).toBeChecked();
      expect(screen.getByRole("checkbox", { name: /driver/i })).toBeChecked();
      expect(screen.getByRole("checkbox", { name: /supervisor/i })).not.toBeChecked();
      expect(screen.getByRole("columnheader", { name: /proficiency/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /remove/i })).toBeInTheDocument();
    });
  });

  it("creates employee with home address", async () => {
    vi.mocked(api.createEmployee).mockResolvedValue({
      ...employeeFixture,
      locations: [],
      skills: [],
    });
    vi.mocked(api.createEmployeeLocation).mockResolvedValue(employeeFixture.locations[0]);

    render(
      <MemoryRouter initialEntries={["/employees/new"]}>
        <Routes>
          <Route path="/employees/:id" element={<EmployeeFormPage />} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/^first name$/i), { target: { value: "Jamie" } });
    fireEvent.change(screen.getByLabelText(/^last name$/i), { target: { value: "Worker" } });
    fireEvent.change(screen.getByLabelText(/^address$/i), { target: { value: "200 Oak Ave" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /driver/i }));
    fireEvent.click(screen.getByRole("button", { name: /create employee/i }));

    await waitFor(() => {
      expect(api.createEmployee).toHaveBeenCalledWith(
        expect.objectContaining({ is_driver: true, active: true })
      );
      expect(api.createEmployeeLocation).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ address: "200 Oak Ave", is_primary: true })
      );
    });
  });
});
