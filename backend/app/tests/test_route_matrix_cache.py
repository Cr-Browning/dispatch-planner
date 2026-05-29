"""Route matrix cache service tests (Phase 6)."""

import pytest
from sqlalchemy import func, select

from app.models import RouteMatrixCache
from app.routing.base import RoutePoint, RoutingOptions
from app.routing.mock_provider import MockRoutingProvider
from app.services.route_matrix_service import RouteMatrixService


@pytest.fixture
def matrix_service(db_session) -> RouteMatrixService:
    return RouteMatrixService(db_session, MockRoutingProvider(), cache_ttl_hours=24)


@pytest.mark.phase6
def test_cache_stores_after_first_lookup(matrix_service: RouteMatrixService, db_session) -> None:
    points = [
        RoutePoint(39.9526, -75.1652),
        RoutePoint(39.9600, -75.1700),
    ]
    options = RoutingOptions()
    matrix_service.get_matrix(points, options)
    db_session.commit()

    count = db_session.scalar(select(func.count()).select_from(RouteMatrixCache))
    assert count == 2  # A->B and B->A

    second = matrix_service.get_matrix(points, options)
    assert second.duration_minutes(0, 1) > 0


@pytest.mark.phase6
def test_cache_hit_avoids_duplicate_rows(
    matrix_service: RouteMatrixService, db_session
) -> None:
    points = [RoutePoint(39.95, -75.16), RoutePoint(39.96, -75.17)]
    matrix_service.get_matrix(points, RoutingOptions())
    db_session.commit()
    count_first = db_session.scalar(select(func.count()).select_from(RouteMatrixCache))

    matrix_service.get_matrix(points, RoutingOptions())
    db_session.commit()
    count_second = db_session.scalar(select(func.count()).select_from(RouteMatrixCache))
    assert count_first == count_second


@pytest.mark.phase6
def test_force_refresh_updates_values(
    matrix_service: RouteMatrixService, db_session
) -> None:
    points = [RoutePoint(39.95, -75.16), RoutePoint(39.96, -75.17)]
    first = matrix_service.get_matrix(points, RoutingOptions())
    db_session.commit()
    duration_first = first.duration_minutes(0, 1)

    matrix_service.invalidate_all()
    db_session.commit()

    refreshed = matrix_service.get_matrix(points, RoutingOptions(), force_refresh=True)
    db_session.commit()
    assert refreshed.duration_minutes(0, 1) == duration_first


@pytest.mark.phase6
def test_create_routing_provider_defaults_to_mock() -> None:
    from app.routing import create_routing_provider

    provider = create_routing_provider()
    assert provider.provider_name == "mock"
