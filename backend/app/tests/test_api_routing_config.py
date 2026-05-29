"""Ensure routing config does not leak secrets via API."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.phase7
def test_health_does_not_expose_google_key(client: TestClient) -> None:
    response = client.get("/health")
    body = response.text.lower()
    assert "google_maps" not in body or "api_key" not in body
    assert "secret" not in body
