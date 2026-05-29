import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";

export function Layout() {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Dispatch Planner</h1>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/dispatch">Dispatch</NavLink>
          <NavLink to="/employees">Employees</NavLink>
          <NavLink to="/jobs">Jobs</NavLink>
          <NavLink to="/skills">Roles</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <button type="button" className="btn secondary" onClick={toggleTheme}>
            {theme === "light" ? "Dark mode" : "Light mode"}
          </button>
          <button type="button" className="btn secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
