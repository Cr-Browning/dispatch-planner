import { describe, expect, it } from "vitest";
import {
  formatDisplayDate,
  formatDisplayDateTime,
  jobLocalDateIso,
  todayIsoDate,
  tomorrowIsoDate,
} from "../utils/dates";

describe("jobLocalDateIso", () => {
  it("uses local calendar date from ISO timestamp", () => {
    const iso = new Date(2026, 5, 15, 8, 0, 0).toISOString();
    expect(jobLocalDateIso(iso)).toBe("2026-06-15");
  });
});

describe("formatDisplayDate", () => {
  it("formats YYYY-MM-DD as MM-DD-YYYY", () => {
    expect(formatDisplayDate("2026-06-15")).toBe("06-15-2026");
  });

  it("formats ISO datetime", () => {
    const iso = new Date(2026, 5, 15, 8, 0, 0).toISOString();
    expect(formatDisplayDate(iso)).toBe("06-15-2026");
  });
});

describe("formatDisplayDateTime", () => {
  it("includes date and time", () => {
    const iso = new Date(2026, 5, 15, 14, 30, 0).toISOString();
    expect(formatDisplayDateTime(iso)).toMatch(/^06-15-2026 /);
    expect(formatDisplayDateTime(iso)).toMatch(/2:30 PM/);
  });
});

describe("tomorrowIsoDate", () => {
  it("is one day after today", () => {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const pad = (n: number) => String(n).padStart(2, "0");
    const expected = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}`;
    expect(tomorrowIsoDate()).toBe(expected);
    expect(tomorrowIsoDate()).not.toBe(todayIsoDate());
  });
});
