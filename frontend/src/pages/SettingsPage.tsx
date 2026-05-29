import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AppSettings, BackupRecord } from "../api/types";
import { formatDisplayDateTime } from "../utils/dates";

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [backingUp, setBackingUp] = useState(false);
  const [restoringId, setRestoringId] = useState<number | null>(null);

  function load() {
    return Promise.all([api.getSettings(), api.listBackups()])
      .then(([s, b]) => {
        setSettings(s);
        setBackups(b);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRestore(backup: BackupRecord) {
    const when = formatDisplayDateTime(backup.created_at);
    if (
      !window.confirm(
        `Restore the database from the backup created ${when}? All current data will be replaced.`
      )
    ) {
      return;
    }
    setRestoringId(backup.id);
    setError(null);
    try {
      await api.restoreBackup(backup.id);
      window.location.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Restore failed");
      setRestoringId(null);
    }
  }

  async function handleBackup() {
    setBackingUp(true);
    setError(null);
    try {
      await api.createBackup("manual from settings");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backup failed");
    } finally {
      setBackingUp(false);
    }
  }

  if (!settings) {
    return <p>{error ?? "Loading…"}</p>;
  }

  return (
    <>
      <div className="page-header">
        <h2>Settings</h2>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <h3>Routing</h3>
        <p>
          Active provider: <strong>{settings.routing_provider}</strong>
        </p>
        <p className="form-hint" style={{ margin: 0 }}>
          For production drive times, set <code>ROUTING_PROVIDER=google</code> and{" "}
          <code>GOOGLE_MAPS_API_KEY</code> in <code>backend/.env</code>, then restart the API.
          Mock routing is fine for local development.
        </p>
      </div>
      <div className="card">
        <h3>CSV export columns</h3>
        <p className="form-hint">Each export includes one row per pickup with:</p>
        <ul>
          {settings.export_columns.map((col) => (
            <li key={col}>{col}</li>
          ))}
        </ul>
        <p className="form-hint" style={{ margin: 0 }}>
          Use <strong>Create &amp; solve</strong> then <strong>Download CSV</strong> on route
          review, or <strong>Create, solve &amp; download CSV</strong> for a one-step export.
        </p>
      </div>
      <div className="card">
        <h3>Database backups</h3>
        <p className="form-hint">
          Backups are stored under <code>BACKUP_DIR</code>. Enable{" "}
          <code>BACKUP_ON_STARTUP=true</code> for an automatic copy when the API starts.
        </p>
        <button type="button" className="btn secondary" disabled={backingUp} onClick={handleBackup}>
          {backingUp ? "Backing up…" : "Create backup now"}
        </button>
        {backups.length > 0 && (
          <table className="data-table" style={{ marginTop: "1rem" }}>
            <thead>
              <tr>
                <th>When</th>
                <th>Notes</th>
                <th>File</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.id}>
                  <td>{formatDisplayDateTime(b.created_at)}</td>
                  <td>{b.notes ?? "—"}</td>
                  <td style={{ fontSize: "0.8rem" }}>{b.file_path}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-link danger"
                      disabled={restoringId !== null}
                      onClick={() => void handleRestore(b)}
                    >
                      {restoringId === b.id ? "Restoring…" : "Restore"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
