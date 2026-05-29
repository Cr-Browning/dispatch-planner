import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { EmployeesPage } from "../pages/EmployeesPage";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    listEmployees: vi.fn(),
    deleteEmployee: vi.fn(),
  },
}));

vi.stubGlobal("confirm", vi.fn(() => true));

describe("EmployeesPage", () => {
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
    vi.mocked(api.deleteEmployee).mockResolvedValue(undefined);
  });

  it("deletes an employee after confirmation", async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Alex Driver")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await waitFor(() => {
      expect(api.deleteEmployee).toHaveBeenCalledWith(1);
      expect(screen.queryByText("Alex Driver")).not.toBeInTheDocument();
    });
  });
});
