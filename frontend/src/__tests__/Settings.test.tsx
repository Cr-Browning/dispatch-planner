import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SettingsPage } from "../pages/SettingsPage";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    getSettings: vi.fn(),
    listBackups: vi.fn(),
    createBackup: vi.fn(),
  },
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.mocked(api.getSettings).mockResolvedValue({
      routing_provider: "mock",
      export_columns: ["Date", "Job Name", "Client"],
    });
    vi.mocked(api.listBackups).mockResolvedValue([]);
  });

  it("shows routing and export column info", async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText(/Active provider/i)).toBeInTheDocument();
      expect(screen.getByText("Job Name")).toBeInTheDocument();
    });
  });
});
