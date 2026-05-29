import { describe, expect, it, vi } from "vitest";
import { confirmDeleteEmployee } from "../utils/employeeActions";

describe("confirmDeleteEmployee", () => {
  it("prompts with the employee name", () => {
    const confirm = vi.fn(() => false);
    vi.stubGlobal("confirm", confirm);
    confirmDeleteEmployee({
      id: 1,
      first_name: "Alex",
      last_name: "Driver",
      display_name: "Alex Driver",
      active: true,
      is_driver: true,
      is_supervisor: false,
      default_vehicle_capacity: 4,
      phone: null,
    });
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("Alex Driver"));
  });
});
