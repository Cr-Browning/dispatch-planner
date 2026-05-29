import type { EmployeeListItem } from "../api/types";

export function employeeDisplayName(emp: EmployeeListItem): string {
  return emp.display_name ?? `${emp.first_name} ${emp.last_name}`;
}

export function confirmDeleteEmployee(emp: EmployeeListItem): boolean {
  const name = employeeDisplayName(emp);
  return window.confirm(
    `Delete employee "${name}"? This removes them from your roster and cannot be undone.`
  );
}
