"""Backups API tests."""

from pathlib import Path

import pytest


@pytest.mark.phase15
def test_create_and_list_backups(
    client, auth_headers, tmp_path, db_session, monkeypatch
) -> None:
    from app.core.config import get_settings
    from app.core.database import engine
    from app.services.backup_service import BackupService

    db_file = tmp_path / "test.db"
    db_file.write_bytes(b"sqlite-test-content")
    monkeypatch.setattr(
        BackupService,
        "_database_path",
        lambda self: db_file,
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "backup_dir", tmp_path / "backups")
    (tmp_path / "backups").mkdir(exist_ok=True)

    service = BackupService(db_session, settings=settings)
    record = service.create_backup(notes="test")
    assert Path(record.file_path).is_file()

    listing = client.get("/backups", headers=auth_headers)
    assert listing.status_code == 200
    assert any(r["notes"] == "test" for r in listing.json())

    _ = engine  # keep fixture referenced


@pytest.mark.phase15
def test_list_backups_requires_auth(client) -> None:
    response = client.get("/backups")
    assert response.status_code == 401


@pytest.mark.phase15
def test_restore_backup(
    client, auth_headers, tmp_path, db_session, monkeypatch
) -> None:
    from app.core.config import get_settings
    from app.services.backup_service import BackupService

    db_file = tmp_path / "live.db"
    db_file.write_text("original")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(
        BackupService,
        "_database_path",
        lambda self: db_file,
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "backup_dir", backup_dir)

    service = BackupService(db_session, settings=settings)
    record = service.create_backup(notes="before-restore")
    db_file.write_text("mutated")

    restore = client.post(f"/backups/{record.id}/restore", headers=auth_headers)
    assert restore.status_code == 204
    assert db_file.read_text() == "original"
