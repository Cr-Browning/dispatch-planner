import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Job, Skill } from "../api/types";
import { defaultJobArrivalLocal } from "../utils/dates";

type SavedRequiredSkill = Job["required_skills"][number];

type PendingRequiredSkill = {
  skill_id: number;
  skill_name: string;
  required_quantity: number;
  minimum_proficiency: number;
  is_preferred: boolean;
};

function toDatetimeLocalValue(iso: string | undefined): string {
  if (!iso) {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(8, 0, 0, 0);
    return toDatetimeLocalValue(d.toISOString());
  }
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function JobFormPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const runDateParam = searchParams.get("date");
  const [job, setJob] = useState<Job | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [skillSkillId, setSkillSkillId] = useState("");
  const [skillQuantity, setSkillQuantity] = useState("1");
  const [skillProficiency, setSkillProficiency] = useState("1");
  const [skillPreferred, setSkillPreferred] = useState(false);
  const [addingSkill, setAddingSkill] = useState(false);
  const [pendingSkills, setPendingSkills] = useState<PendingRequiredSkill[]>([]);
  const [newSkillName, setNewSkillName] = useState("");
  const [duplicating, setDuplicating] = useState(false);

  useEffect(() => {
    api.listSkills().then(setSkills).catch(() => {});
  }, []);

  useEffect(() => {
    if (isNew) return;
    api
      .getJob(Number(id))
      .then(setJob)
      .catch((e) => setError(e.message));
  }, [id, isNew]);

  async function handleDuplicate() {
    if (!job) {
      return;
    }
    setDuplicating(true);
    setError(null);
    try {
      const copy = await api.duplicateJob(
        job.id,
        runDateParam ? { run_date: runDateParam } : {}
      );
      navigate(`/jobs/${copy.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Duplicate failed");
    } finally {
      setDuplicating(false);
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const latRaw = String(form.get("latitude") ?? "").trim();
    const lngRaw = String(form.get("longitude") ?? "").trim();
    const body: Record<string, unknown> = {
      job_name: String(form.get("job_name") || "") || null,
      client_name: String(form.get("client_name") || "") || null,
      address: String(form.get("address")),
      latitude: latRaw ? Number(latRaw) : null,
      longitude: lngRaw ? Number(lngRaw) : null,
      required_arrival_time: new Date(String(form.get("required_arrival_time"))).toISOString(),
      required_headcount: Number(form.get("required_headcount")),
      tolls_allowed: form.get("tolls_allowed") === "on",
      return_trip_enabled: form.get("return_trip_enabled") === "on",
      dropoff_return_enabled: form.get("dropoff_return_enabled") === "on",
      notes: String(form.get("notes") || "") || null,
    };
    if (isNew && pendingSkills.length === 0) {
      setError("Add at least one required role before creating the job.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        const created = await api.createJob(body);
        for (const skill of pendingSkills) {
          await api.addJobRequiredSkill(created.id, {
            skill_id: skill.skill_id,
            required_quantity: skill.required_quantity,
            minimum_proficiency: skill.minimum_proficiency,
            is_preferred: skill.is_preferred,
          });
        }
        navigate(`/jobs/${created.id}`);
      } else {
        const updated = await api.updateJob(Number(id), body);
        setJob(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function resetSkillForm() {
    setSkillSkillId("");
    setSkillQuantity("1");
    setSkillProficiency("1");
    setSkillPreferred(false);
  }

  async function handleAddSkill(e: FormEvent) {
    e.preventDefault();
    if (!skillSkillId && !newSkillName.trim()) {
      setError("Select a role or enter a new role name.");
      return;
    }
    setAddingSkill(true);
    setError(null);
    let resolvedSkillId = skillSkillId ? Number(skillSkillId) : 0;
    const trimmedName = newSkillName.trim();
    if (!resolvedSkillId && trimmedName) {
      const created = await api.createSkill({ name: trimmedName });
      resolvedSkillId = created.id;
      setSkills((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
    }
    if (!resolvedSkillId) {
      setError("Select a role or enter a new role name.");
      setAddingSkill(false);
      return;
    }
    const resolvedSkill = skills.find((s) => s.id === resolvedSkillId) ?? {
      id: resolvedSkillId,
      name: trimmedName,
      active: true,
    };

    if (isNew) {
      if (pendingSkills.some((s) => s.skill_id === resolvedSkillId)) {
        setError("That role is already listed.");
        return;
      }
      setError(null);
      setPendingSkills((prev) => [
        ...prev,
        {
          skill_id: resolvedSkillId,
          skill_name: resolvedSkill.name,
          required_quantity: Number(skillQuantity),
          minimum_proficiency: Number(skillProficiency),
          is_preferred: skillPreferred,
        },
      ]);
      resetSkillForm();
      setNewSkillName("");
      setAddingSkill(false);
      return;
    }

    if (!job) {
      setAddingSkill(false);
      return;
    }
    try {
      await api.addJobRequiredSkill(job.id, {
        skill_id: resolvedSkillId,
        required_quantity: Number(skillQuantity),
        minimum_proficiency: Number(skillProficiency),
        is_preferred: skillPreferred,
      });
      const refreshed = await api.getJob(job.id);
      setJob(refreshed);
      resetSkillForm();
      setNewSkillName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add role");
    } finally {
      setAddingSkill(false);
    }
  }

  function removePendingSkill(skillId: number) {
    setPendingSkills((prev) => prev.filter((s) => s.skill_id !== skillId));
  }

  async function handleRemoveSavedSkill(requiredSkillId: number, skillName: string | null) {
    if (!job) return;
    if (!window.confirm(`Remove ${skillName ?? "this role"} from the job?`)) {
      return;
    }
    setError(null);
    try {
      await api.removeJobRequiredSkill(job.id, requiredSkillId);
      const refreshed = await api.getJob(job.id);
      setJob(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove role");
    }
  }

  if (!isNew && !job) {
    return <p>{error ?? "Loading…"}</p>;
  }

  const defaults = job ?? {
    job_name: "",
    client_name: "",
    address: "",
    latitude: null,
    longitude: null,
    required_arrival_time: runDateParam
      ? new Date(defaultJobArrivalLocal(runDateParam)).toISOString()
      : new Date(Date.now() + 86400000).toISOString(),
    required_headcount: 1,
    tolls_allowed: true,
    return_trip_enabled: false,
    dropoff_return_enabled: false,
    notes: "",
    required_skills: [],
  };

  const listedSkills: Array<SavedRequiredSkill | PendingRequiredSkill> = isNew
    ? pendingSkills
    : job?.required_skills ?? [];

  function skillRowKey(skill: SavedRequiredSkill | PendingRequiredSkill): number {
    return "id" in skill ? skill.id : skill.skill_id;
  }

  return (
    <>
      <div className="page-header">
        <h2>{isNew ? "New job" : "Edit job"}</h2>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {!isNew && (
            <button
              type="button"
              className="btn secondary"
              disabled={duplicating || saving}
              onClick={() => void handleDuplicate()}
            >
              {duplicating ? "Duplicating…" : "Duplicate job"}
            </button>
          )}
          <Link to="/jobs" className="btn secondary">
            Back
          </Link>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <form id="job-details-form" className="form-grid" onSubmit={handleSubmit}>
          <label>
            Job name
            <input name="job_name" defaultValue={defaults.job_name ?? ""} required />
          </label>
          <label>
            Client name
            <input name="client_name" defaultValue={defaults.client_name ?? ""} />
          </label>
          <label>
            Address
            <input name="address" defaultValue={defaults.address} required />
          </label>
          <label>
            Latitude
            <input
              name="latitude"
              type="number"
              step="any"
              defaultValue={defaults.latitude ?? ""}
              placeholder="e.g. 39.9526"
            />
          </label>
          <label>
            Longitude
            <input
              name="longitude"
              type="number"
              step="any"
              defaultValue={defaults.longitude ?? ""}
              placeholder="e.g. -75.1652"
            />
          </label>
          <label>
            Required arrival
            <input
              name="required_arrival_time"
              type="datetime-local"
              defaultValue={toDatetimeLocalValue(defaults.required_arrival_time)}
              required
            />
          </label>
          <label>
            Required headcount
            <input
              name="required_headcount"
              type="number"
              min={1}
              max={50}
              defaultValue={defaults.required_headcount}
              required
            />
          </label>
          <div className="form-checkbox-group">
            <label className="checkbox-label">
              <input
                name="tolls_allowed"
                type="checkbox"
                defaultChecked={defaults.tolls_allowed}
              />
              <span>Tolls allowed</span>
            </label>
            <label className="checkbox-label">
              <input
                name="return_trip_enabled"
                type="checkbox"
                defaultChecked={defaults.return_trip_enabled}
              />
              <span>Return trip</span>
            </label>
            <label className="checkbox-label">
              <input
                name="dropoff_return_enabled"
                type="checkbox"
                defaultChecked={defaults.dropoff_return_enabled}
              />
              <span>Dropoff return</span>
            </label>
          </div>
          <label>
            Notes
            <textarea name="notes" rows={3} defaultValue={defaults.notes ?? ""} />
          </label>
          <p className="form-hint">
            Latitude and longitude are used for routing and the map. Leave blank only if you will
            add coordinates later.
          </p>
        </form>

        {(isNew || job) && (
          <>
          <h3 style={{ marginTop: "1.25rem" }}>Required roles</h3>
          <p className="form-hint">
            {isNew
              ? "Add every role (skill) needed on site. Assignment will not work without at least one."
              : "Employees must match these roles to be assigned to the job."}
          </p>
          {listedSkills.length === 0 ? (
            <p className="form-hint">No roles listed yet.</p>
          ) : (
            <ul className="skill-list">
              {listedSkills.map((s) => (
                <li key={skillRowKey(s)}>
                  <span>
                    {s.skill_name}
                    {s.is_preferred ? " (preferred)" : ""} × {s.required_quantity}
                    {!s.is_preferred && ` — min proficiency ${s.minimum_proficiency}`}
                  </span>
                  {isNew ? (
                    <button
                      type="button"
                      className="btn-link danger"
                      onClick={() => removePendingSkill(s.skill_id)}
                    >
                      Remove
                    </button>
                  ) : (
                    "id" in s && (
                      <button
                        type="button"
                        className="btn-link danger"
                        onClick={() => handleRemoveSavedSkill(s.id, s.skill_name)}
                      >
                        Remove
                      </button>
                    )
                  )}
                </li>
              ))}
            </ul>
          )}
          <form className="form-grid" onSubmit={handleAddSkill} style={{ marginTop: "1rem" }}>
              <label>
                Role
                <select
                  value={skillSkillId}
                  onChange={(e) => setSkillSkillId(e.target.value)}
                >
                  <option value="">Select existing…</option>
                  {skills.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Or new role name
                <input
                  value={newSkillName}
                  onChange={(e) => setNewSkillName(e.target.value)}
                  placeholder="e.g. Waterproofing"
                />
              </label>
              <label>
                Quantity
                <input
                  type="number"
                  min={1}
                  value={skillQuantity}
                  onChange={(e) => setSkillQuantity(e.target.value)}
                />
              </label>
              <label>
                Min proficiency
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={skillProficiency}
                  onChange={(e) => setSkillProficiency(e.target.value)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={skillPreferred}
                  onChange={(e) => setSkillPreferred(e.target.checked)}
                />
                <span>Preferred only</span>
              </label>
              <button type="submit" className="btn secondary" disabled={addingSkill}>
                {addingSkill ? "Adding…" : "Add role"}
              </button>
            </form>
          </>
        )}

        <button
          type="submit"
          form="job-details-form"
          className="btn"
          disabled={saving}
          style={{ marginTop: "1rem" }}
        >
          {saving ? "Saving…" : isNew ? "Create job" : "Save changes"}
        </button>
      </div>
    </>
  );
}
