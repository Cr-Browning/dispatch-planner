"""Security tests (Phase 3+)."""

import json

import pytest
from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models import AppSetting
from app.services.auth_service import PASSWORD_KEY


@pytest.mark.phase3
def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret")
    assert hashed != "secret"
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


@pytest.mark.phase3
def test_dispatcher_password_stored_hashed(db_session, client) -> None:
    client.post("/auth/login", json={"password": "testpass"})
    row = db_session.scalars(select(AppSetting).where(AppSetting.key == PASSWORD_KEY)).first()
    assert row is not None
    stored = json.loads(row.value_json)
    assert stored != "testpass"
    assert verify_password("testpass", stored)
