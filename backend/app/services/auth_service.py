"""Authentication: single dispatcher password stored hashed in app_settings."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import AppSetting

PASSWORD_KEY = "dispatcher_password_hash"
DISPATCHER_USERNAME = "dispatcher"


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ensure_password_initialized(self) -> None:
        row = self._db.execute(
            select(AppSetting).where(AppSetting.key == PASSWORD_KEY)
        ).scalar_one_or_none()
        if row is None:
            settings = get_settings()
            hashed = hash_password(settings.dispatcher_password)
            self._db.add(
                AppSetting(key=PASSWORD_KEY, value_json=json.dumps(hashed))
            )
            self._db.commit()

    def _get_password_hash(self) -> str:
        self.ensure_password_initialized()
        row = self._db.execute(
            select(AppSetting).where(AppSetting.key == PASSWORD_KEY)
        ).scalar_one()
        return json.loads(row.value_json)

    def authenticate(self, password: str) -> str | None:
        if not verify_password(password, self._get_password_hash()):
            return None
        return DISPATCHER_USERNAME

    def create_token_for_password(self, password: str) -> str | None:
        user = self.authenticate(password)
        if user is None:
            return None
        return create_access_token(user)

    def validate_session_user(self, username: str) -> bool:
        return username == DISPATCHER_USERNAME

    def me(self, username: str) -> dict[str, str]:
        return {"username": username, "role": "dispatcher"}
