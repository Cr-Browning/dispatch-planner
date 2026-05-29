import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Employee, EmployeeLocation, EmployeeSkill, Skill } from "../api/types";

function primaryLocation(employee: Employee): EmployeeLocation | undefined {
  return employee.locations.find((l) => l.is_primary) ?? employee.locations[0];
}

type ProfileForm = {
  first_name: string;
  last_name: string;
  display_name: string;
  active: boolean;
  is_driver: boolean;
  is_supervisor: boolean;
  default_vehicle_capacity: number;
  phone: string;
  notes: string;
  home_address: string;
  home_latitude: string;
  home_longitude: string;
};

const EMPTY_PROFILE: ProfileForm = {
  first_name: "",
  last_name: "",
  display_name: "",
  active: true,
  is_driver: false,
  is_supervisor: false,
  default_vehicle_capacity: 4,
  phone: "",
  notes: "",
  home_address: "",
  home_latitude: "",
  home_longitude: "",
};

function profileFromEmployee(emp: Employee): ProfileForm {
  const home = primaryLocation(emp);
  return {
    first_name: emp.first_name,
    last_name: emp.last_name,
    display_name: emp.display_name ?? "",
    active: emp.active,
    is_driver: emp.is_driver,
    is_supervisor: emp.is_supervisor,
    default_vehicle_capacity: emp.default_vehicle_capacity,
    phone: emp.phone ?? "",
    notes: emp.notes ?? "",
    home_address: home?.address ?? "",
    home_latitude: home?.latitude != null ? String(home.latitude) : "",
    home_longitude: home?.longitude != null ? String(home.longitude) : "",
  };
}

export function EmployeeFormPage() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [profile, setProfile] = useState<ProfileForm>(EMPTY_PROFILE);
  const [skillCatalog, setSkillCatalog] = useState<Skill[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [skillSkillId, setSkillSkillId] = useState("");
  const [newSkillName, setNewSkillName] = useState("");
  const [skillProficiency, setSkillProficiency] = useState("3");
  const [addingSkill, setAddingSkill] = useState(false);

  useEffect(() => {
    api.listSkills().then(setSkillCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    if (isNew) {
      setProfile(EMPTY_PROFILE);
      setEmployee(null);
      return;
    }
    api
      .getEmployee(Number(id))
      .then((data) => {
        setEmployee(data);
        setProfile(profileFromEmployee(data));
      })
      .catch((e) => setError(e.message));
  }, [id, isNew]);

  function patchProfile(patch: Partial<ProfileForm>) {
    setProfile((prev) => ({ ...prev, ...patch }));
  }

  async function savePrimaryLocation(employeeId: number, data: ProfileForm) {
    const address = data.home_address.trim();
    if (!address) {
      return;
    }
    const latRaw = data.home_latitude.trim();
    const lngRaw = data.home_longitude.trim();
    const payload = {
      label: "Home",
      address,
      latitude: latRaw ? Number(latRaw) : null,
      longitude: lngRaw ? Number(lngRaw) : null,
      is_primary: true,
    };
    const primary = employee ? primaryLocation(employee) : undefined;
    if (primary) {
      await api.updateEmployeeLocation(employeeId, primary.id, payload);
    } else {
      await api.createEmployeeLocation(employeeId, payload);
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const body = {
      first_name: profile.first_name.trim(),
      last_name: profile.last_name.trim(),
      display_name: profile.display_name.trim() || null,
      active: profile.active,
      is_driver: profile.is_driver,
      is_supervisor: profile.is_supervisor,
      default_vehicle_capacity: profile.default_vehicle_capacity,
      phone: profile.phone.trim() || null,
      notes: profile.notes.trim() || null,
    };
    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        const created = await api.createEmployee(body);
        await savePrimaryLocation(created.id, profile);
        navigate(`/employees/${created.id}`);
      } else {
        const employeeId = Number(id);
        await api.updateEmployee(employeeId, body);
        await savePrimaryLocation(employeeId, profile);
        const refreshed = await api.getEmployee(employeeId);
        setEmployee(refreshed);
        setProfile(profileFromEmployee(refreshed));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleAddSkill(e: FormEvent) {
    e.preventDefault();
    if (!employee) return;
    setAddingSkill(true);
    setError(null);
    try {
      let skillId = skillSkillId ? Number(skillSkillId) : 0;
      const trimmedName = newSkillName.trim();
      if (!skillId && trimmedName) {
        const created = await api.createSkill({ name: trimmedName });
        skillId = created.id;
        setSkillCatalog((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      }
      if (!skillId) {
        setError("Select a skill or enter a new skill name");
        return;
      }
      await api.addEmployeeSkill(employee.id, {
        skill_id: skillId,
        proficiency: Number(skillProficiency),
      });
      const refreshed = await api.getEmployee(employee.id);
      setEmployee(refreshed);
      setSkillSkillId("");
      setNewSkillName("");
      setSkillProficiency("3");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add skill");
    } finally {
      setAddingSkill(false);
    }
  }

  async function handleUpdateProficiency(skill: EmployeeSkill, proficiency: number) {
    if (!employee) return;
    setError(null);
    try {
      await api.updateEmployeeSkill(employee.id, skill.skill_id, { proficiency });
      const refreshed = await api.getEmployee(employee.id);
      setEmployee(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update skill");
    }
  }

  async function handleRemoveSkill(skill: EmployeeSkill) {
    if (!employee) return;
    if (
      !window.confirm(`Remove ${skill.skill_name ?? "this skill"} from this employee?`)
    ) {
      return;
    }
    setError(null);
    try {
      await api.removeEmployeeSkill(employee.id, skill.skill_id);
      const refreshed = await api.getEmployee(employee.id);
      setEmployee(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove skill");
    }
  }

  const assignedSkillIds = new Set((employee?.skills ?? []).map((s) => s.skill_id));
  const availableSkills = skillCatalog.filter((s) => !assignedSkillIds.has(s.id));

  if (!isNew && !employee) {
    return <p>{error ?? "Loading…"}</p>;
  }

  return (
    <>
      <div className="page-header">
        <h2>{isNew ? "New employee" : "Edit employee"}</h2>
        <Link to="/employees" className="btn secondary">
          Back
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <form className="form-grid form-grid-wide" onSubmit={handleSubmit}>
          <h3 className="form-section-title">Profile</h3>
          <label>
            First name
            <input
              name="first_name"
              value={profile.first_name}
              onChange={(e) => patchProfile({ first_name: e.target.value })}
              required
            />
          </label>
          <label>
            Last name
            <input
              name="last_name"
              value={profile.last_name}
              onChange={(e) => patchProfile({ last_name: e.target.value })}
              required
            />
          </label>
          <label>
            Display name
            <input
              name="display_name"
              value={profile.display_name}
              onChange={(e) => patchProfile({ display_name: e.target.value })}
            />
          </label>
          <label>
            Vehicle capacity
            <input
              name="default_vehicle_capacity"
              type="number"
              min={1}
              max={20}
              value={profile.default_vehicle_capacity}
              onChange={(e) =>
                patchProfile({ default_vehicle_capacity: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Phone
            <input
              name="phone"
              type="tel"
              value={profile.phone}
              onChange={(e) => patchProfile({ phone: e.target.value })}
              placeholder="For CSV driver contact"
            />
          </label>
          <div className="form-checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={profile.active}
                onChange={(e) => patchProfile({ active: e.target.checked })}
              />
              <span>Active</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={profile.is_driver}
                onChange={(e) => patchProfile({ is_driver: e.target.checked })}
              />
              <span>Driver</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={profile.is_supervisor}
                onChange={(e) => patchProfile({ is_supervisor: e.target.checked })}
              />
              <span>Supervisor</span>
            </label>
          </div>
          <label>
            Notes
            <textarea
              name="notes"
              rows={3}
              value={profile.notes}
              onChange={(e) => patchProfile({ notes: e.target.value })}
            />
          </label>

          <h3 className="form-section-title">Home / pickup address</h3>
          <p className="form-hint">
            Used for pickup routing. Set coordinates when you can so routes and the map are
            accurate.
          </p>
          <label>
            Address
            <input
              name="home_address"
              value={profile.home_address}
              onChange={(e) => patchProfile({ home_address: e.target.value })}
              placeholder="Street address"
            />
          </label>
          <label>
            Latitude
            <input
              name="home_latitude"
              type="number"
              step="any"
              value={profile.home_latitude}
              onChange={(e) => patchProfile({ home_latitude: e.target.value })}
              placeholder="e.g. 39.9526"
            />
          </label>
          <label>
            Longitude
            <input
              name="home_longitude"
              type="number"
              step="any"
              value={profile.home_longitude}
              onChange={(e) => patchProfile({ home_longitude: e.target.value })}
              placeholder="e.g. -75.1652"
            />
          </label>

          <button type="submit" className="btn" disabled={saving}>
            {saving ? "Saving…" : isNew ? "Create employee" : "Save changes"}
          </button>
        </form>
      </div>

      {!isNew && employee && (
        <div className="card">
          <h3>Skills</h3>
          <p className="form-hint">
            Skills belong to this employee. Job requirements use the same skill names when you plan
            dispatch.
          </p>
          {employee.skills.length === 0 ? (
            <p className="form-hint">No skills yet — add at least one for assignment.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Proficiency (1–5)</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {employee.skills.map((s) => (
                  <tr key={s.id}>
                    <td>{s.skill_name}</td>
                    <td>
                      <select
                        value={s.proficiency}
                        onChange={(e) =>
                          handleUpdateProficiency(s, Number(e.target.value))
                        }
                      >
                        {[1, 2, 3, 4, 5].map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="table-actions">
                      <button
                        type="button"
                        className="btn-link danger"
                        onClick={() => handleRemoveSkill(s)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <form className="form-grid" onSubmit={handleAddSkill} style={{ marginTop: "1rem" }}>
            <label>
              Add existing skill
              <select
                value={skillSkillId}
                onChange={(e) => setSkillSkillId(e.target.value)}
              >
                <option value="">Select…</option>
                {availableSkills.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Or new skill name
              <input
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                placeholder="e.g. Hardwood"
              />
            </label>
            <label>
              Proficiency
              <input
                type="number"
                min={1}
                max={5}
                value={skillProficiency}
                onChange={(e) => setSkillProficiency(e.target.value)}
              />
            </label>
            <button type="submit" className="btn secondary" disabled={addingSkill}>
              {addingSkill ? "Adding…" : "Add skill"}
            </button>
          </form>
        </div>
      )}

      {isNew && (
        <p className="form-hint" style={{ marginTop: "0.5rem" }}>
          After creating the employee you can add skills on the next screen.
        </p>
      )}
    </>
  );
}
