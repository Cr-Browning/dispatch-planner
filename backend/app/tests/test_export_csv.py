"""CSV export tests (Phase 12)."""

import csv
from pathlib import Path

import pytest

from app.models import ExportRecord
from app.services.export_service import CSV_COLUMNS, ExportService


def _solve_run(seed_catalog, client, auth_headers, job_keys: list[str]) -> int:
    job_ids = [seed_catalog["jobs"][k].id for k in job_keys]
    create = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-15", "name": "Export Test Run", "job_ids": job_ids},
        headers=auth_headers,
    )
    assert create.status_code == 201
    run_id = create.json()["id"]
    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    return run_id


def _read_export(path: str) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.phase12
def test_csv_has_expected_columns(
    seed_catalog, db_session, client, auth_headers, tmp_export_dir
) -> None:
    run_id = _solve_run(
        seed_catalog, client, auth_headers, ["demo_cleaning", "flooring_tile"]
    )
    result = ExportService(db_session, export_dir=tmp_export_dir).export_dispatch_run_csv(
        run_id
    )
    rows = _read_export(result.file_path)
    assert result.row_count == len(rows)
    assert rows
    assert list(rows[0].keys()) == CSV_COLUMNS


@pytest.mark.phase12
def test_export_includes_job_address_and_core_fields(
    seed_catalog, db_session, client, auth_headers, tmp_export_dir
) -> None:
    run_id = _solve_run(seed_catalog, client, auth_headers, ["demo_cleaning"])
    result = ExportService(db_session, export_dir=tmp_export_dir).export_dispatch_run_csv(
        run_id
    )
    rows = _read_export(result.file_path)
    assert rows
    row = rows[0]
    job = seed_catalog["jobs"]["demo_cleaning"]
    assert row["Date"] == "06-15-2026"
    assert row["Job Name"] == job.job_name
    assert row["Client"] == job.client_name
    assert row["Address"] == job.address
    assert row["Arrival Time"]
    assert row["Driver"]
    assert row["Employee Name"]
    assert "Driver Phone" in row


@pytest.mark.phase12
def test_includes_all_jobs_and_maps_links(
    seed_catalog, db_session, client, auth_headers, tmp_export_dir
) -> None:
    run_id = _solve_run(
        seed_catalog, client, auth_headers, ["demo_cleaning", "flooring_tile"]
    )
    result = ExportService(db_session, export_dir=tmp_export_dir).export_dispatch_run_csv(
        run_id
    )
    rows = _read_export(result.file_path)
    job_names = {r["Job Name"] for r in rows}
    assert seed_catalog["jobs"]["demo_cleaning"].job_name in job_names
    assert seed_catalog["jobs"]["flooring_tile"].job_name in job_names
    assert any(r["Google Maps Link"].startswith("http") for r in rows)
    assert "Notes" in rows[0]


@pytest.mark.phase12
def test_export_record_persisted(
    seed_catalog, db_session, client, auth_headers, tmp_export_dir
) -> None:
    run_id = _solve_run(seed_catalog, client, auth_headers, ["demo_cleaning"])
    result = ExportService(db_session, export_dir=tmp_export_dir).export_dispatch_run_csv(
        run_id
    )
    record = db_session.get(ExportRecord, result.export_record_id)
    assert record is not None
    assert record.dispatch_run_id == run_id
    assert record.export_type == "csv"
    assert Path(record.file_path).is_file()


@pytest.mark.phase12
def test_export_via_api(
    seed_catalog, client, auth_headers, tmp_export_dir
) -> None:
    run_id = _solve_run(
        seed_catalog, client, auth_headers, ["demo_cleaning", "flooring_tile"]
    )
    response = client.post(
        f"/dispatch-runs/{run_id}/export-csv",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dispatch_run_id"] == run_id
    assert body["row_count"] >= 4
    assert Path(body["file_path"]).is_file()
    rows = _read_export(body["file_path"])
    assert rows[0]["Job Name"]


@pytest.mark.phase12
def test_export_fails_without_routes(
    seed_catalog, client, auth_headers, tmp_export_dir
) -> None:
    job_ids = [seed_catalog["jobs"]["demo_cleaning"].id]
    create = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-15", "name": "Unsolved", "job_ids": job_ids},
        headers=auth_headers,
    )
    run_id = create.json()["id"]
    response = client.post(
        f"/dispatch-runs/{run_id}/export-csv",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.phase12
def test_download_export_csv(seed_catalog, client, auth_headers, tmp_export_dir) -> None:
    run_id = _solve_run(seed_catalog, client, auth_headers, ["demo_cleaning"])
    response = client.get(
        f"/dispatch-runs/{run_id}/export-csv/download",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "Date" in response.text
