"""Mock routing provider tests (Phase 6)."""

import pytest

from app.routing.base import RoutePoint, RoutingOptions
from app.routing.mock_provider import MockRoutingProvider, haversine_miles, travel_minutes


@pytest.fixture
def mock_provider() -> MockRoutingProvider:
    return MockRoutingProvider()


@pytest.mark.phase6
def test_geocode_is_deterministic(mock_provider: MockRoutingProvider) -> None:
    a = mock_provider.geocode("100 Market St")
    b = mock_provider.geocode("100 Market St")
    c = mock_provider.geocode("200 Race St")
    assert a.latitude == b.latitude
    assert a.longitude == b.longitude
    assert (a.latitude, a.longitude) != (c.latitude, c.longitude)


@pytest.mark.phase6
def test_matrix_symmetric_legs(mock_provider: MockRoutingProvider) -> None:
    points = [
        RoutePoint(39.95, -75.16, label="A"),
        RoutePoint(39.96, -75.17, label="B"),
    ]
    matrix = mock_provider.compute_matrix(points, RoutingOptions())
    ab = matrix.get(0, 1)
    ba = matrix.get(1, 0)
    assert ab is not None and ba is not None
    assert ab.duration_minutes == ba.duration_minutes
    assert ab.distance_miles == ba.distance_miles
    assert matrix.get(0, 0).duration_minutes == 0.0


@pytest.mark.phase6
def test_tolls_increase_travel_time() -> None:
    miles = 10.0
    with_tolls = travel_minutes(miles, tolls_allowed=True)
    without_tolls = travel_minutes(miles, tolls_allowed=False)
    assert without_tolls > with_tolls


@pytest.mark.phase6
def test_compute_route_sums_legs(mock_provider: MockRoutingProvider) -> None:
    stops = [
        RoutePoint(39.9526, -75.1652, label="start"),
        RoutePoint(39.9600, -75.1700, label="pickup"),
        RoutePoint(39.9700, -75.1800, label="job"),
    ]
    result = mock_provider.compute_route(stops, RoutingOptions())
    assert result.duration_minutes > 0
    assert result.distance_miles > 0
    assert result.google_maps_url is not None
    assert "google.com/maps" in result.google_maps_url
    assert result.route_geometry_json is not None


@pytest.mark.phase6
def test_haversine_zero_for_same_point() -> None:
    assert haversine_miles(40.0, -75.0, 40.0, -75.0) == 0.0
