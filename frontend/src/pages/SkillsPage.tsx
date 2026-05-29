import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SkillWithUsage } from "../api/types";

export function SkillsPage() {
  const [skills, setSkills] = useState<SkillWithUsage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  function load() {
    return api
      .listSkills(false, true)
      .then((rows) => setSkills(rows as SkillWithUsage[]))
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.createSkill({ name: name.trim(), active: true });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create role");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Roles / skills</h2>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <h3>Add role</h3>
        <form
          className="form-grid"
          style={{ gridTemplateColumns: "1fr auto", alignItems: "end" }}
          onSubmit={handleCreate}
        >
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <button type="submit" className="btn" disabled={saving}>
            {saving ? "Saving…" : "Add"}
          </button>
        </form>
      </div>
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Active</th>
              <th>Jobs using</th>
              <th>Employees with skill</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((skill) => (
              <tr key={skill.id}>
                <td>{skill.name}</td>
                <td>{skill.active ? "Yes" : "No"}</td>
                <td>{skill.job_usage_count}</td>
                <td>{skill.employee_usage_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
