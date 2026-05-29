function formatLocalIsoDate(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayIsoDate(): string {
  return formatLocalIsoDate(new Date());
}

export function tomorrowIsoDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return formatLocalIsoDate(d);
}

/** User-facing calendar date: MM-DD-YYYY (from YYYY-MM-DD or ISO datetime). */
export function formatDisplayDate(value: string | Date): string {
  let year: number;
  let month: number;
  let day: number;
  if (value instanceof Date) {
    year = value.getFullYear();
    month = value.getMonth() + 1;
    day = value.getDate();
  } else if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    [year, month, day] = value.split("-").map(Number);
  } else {
    const d = new Date(value);
    year = d.getFullYear();
    month = d.getMonth() + 1;
    day = d.getDate();
  }
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(month)}-${pad(day)}-${year}`;
}

const timeFormat: Intl.DateTimeFormatOptions = {
  hour: "numeric",
  minute: "2-digit",
};

/** User-facing date and time: MM-DD-YYYY h:mm AM/PM */
export function formatDisplayDateTime(iso: string): string {
  const d = new Date(iso);
  return `${formatDisplayDate(d)} ${d.toLocaleTimeString("en-US", timeFormat)}`;
}

/** User-facing clock time: h:mm AM/PM */
export function formatDisplayTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", timeFormat);
}

export function defaultDispatchName(runDate: string): string {
  return `Dispatch — ${formatDisplayDate(runDate)}`;
}

/** Default required arrival for a new job on a dispatch run date (8:00 local). */
export function defaultJobArrivalLocal(runDate: string, hour = 8): string {
  const [y, m, d] = runDate.split("-").map(Number);
  const dt = new Date(y, m - 1, d, hour, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

export function addDaysIsoDate(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  return formatLocalIsoDate(dt);
}

export function weekDatesFrom(startIso: string, count = 7): string[] {
  return Array.from({ length: count }, (_, i) => addDaysIsoDate(startIso, i));
}

export function jobLocalDateIso(iso: string): string {
  const d = new Date(iso);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
