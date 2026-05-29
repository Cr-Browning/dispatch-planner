import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { EmployeeListItem } from "../api/types";
import { confirmDeleteEmployee } from "../utils/employeeActions";

export function EmployeesPage() {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    api
      .listEmployees()
      .then(setEmployees)
      .catch((e) => setError(e.message));
  }, []);

  async function handleDelete(emp: EmployeeListItem) {
    if (!confirmDeleteEmployee(emp)) {
      return;
    }
    setDeletingId(emp.id);
    setError(null);
    try {
      await api.deleteEmployee(emp.id);
      setEmployees((prev) => prev.filter((e) => e.id !== emp.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Employees</h2>
        <Link to="/employees/new" className="btn">
          Add employee
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Driver</th>
              <th>Supervisor</th>
              <th>Capacity</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {employees.map((emp) => (
              <tr key={emp.id}>
                <td>{emp.display_name ?? `${emp.first_name} ${emp.last_name}`}</td>
                <td>{emp.is_driver ? "Yes" : "No"}</td>
                <td>{emp.is_supervisor ? "Yes" : "No"}</td>
                <td>{emp.default_vehicle_capacity}</td>
                <td>{emp.active ? "Yes" : "No"}</td>
                <td className="table-actions">
                  <Link to={`/employees/${emp.id}`}>Edit</Link>
                  <button
                    type="button"
                    className="btn-link danger"
                    disabled={deletingId === emp.id}
                    onClick={() => handleDelete(emp)}
                  >
                    {deletingId === emp.id ? "Deleting…" : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
