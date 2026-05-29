import { describe, expect, it, vi } from "vitest";
import { confirmDeleteJob } from "../utils/jobActions";

describe("confirmDeleteJob", () => {
  it("uses job name in the confirmation message", () => {
    const confirm = vi.fn(() => true);
    vi.stubGlobal("confirm", confirm);
    confirmDeleteJob({
      id: 1,
      job_name: "Roof repair",
      client_name: "ACME",
      address: "1 St",
      required_arrival_time: "2026-06-15T08:00:00Z",
      required_headcount: 2,
    });
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("Roof repair"));
  });
});
