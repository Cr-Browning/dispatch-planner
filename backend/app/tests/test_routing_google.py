"""Google routing provider tests — parsing (unit) and live API (integration)."""

from __future__ import annotations

import os

import pytest

from app.routing.base import RoutePoint, RoutingOptions
from app.routing.errors import GeocodeNotFoundError, RoutingProviderError
from app.routing.google_provider import (
    GoogleRoutingProvider,
    build_maps_directions_url,
    parse_directions_response,
    parse_geocode_response,
    parse_matrix_response,
)

SAMPLE_GEOCODE = {
    "status": "OK",
    "results": [
        {
            "formatted_address": "Philadelphia, PA, USA",
            "geometry": {"location": {"lat": 39.9526, "lng": -75.1652}},
        }
    ],
}

SAMPLE_MATRIX = {
    "status": "OK",
    "rows": [
        {
            "elements": [
                {"status": "OK", "duration": {"value": 0}, "distance": {"value": 0}},
                {"status": "OK", "duration": {"value": 600}, "distance": {"value": 5000}},
            ]
        },
        {
            "elements": [
                {"status": "OK", "duration": {"value": 620}, "distance": {"value": 5100}},
                {"status": "OK", "duration": {"value": 0}, "distance": {"value": 0}},
            ]
        },
    ],
}

SAMPLE_DIRECTIONS = {
    "status": "OK",
    "routes": [
        {
            "overview_polyline": {"points": "abcd"},
            "legs": [
                {"duration": {"value": 900}, "distance": {"value": 8000}},
                {"duration": {"value": 300}, "distance": {"value": 2000}},
            ],
        }
    ],
}


@pytest.mark.phase7
def test_parse_geocode_response() -> None:
    result = parse_geocode_response("Philadelphia", SAMPLE_GEOCODE)
    assert result.latitude == pytest.approx(39.9526)
    assert result.longitude == pytest.approx(-75.1652)
    assert "Philadelphia" in (result.formatted_address or "")


@pytest.mark.phase7
def test_parse_geocode_zero_results() -> None:
    with pytest.raises(GeocodeNotFoundError):
        parse_geocode_response("Nowhere", {"status": "ZERO_RESULTS", "results": []})


@pytest.mark.phase7
def test_parse_matrix_response() -> None:
    points = [
        RoutePoint(39.95, -75.16),
        RoutePoint(39.96, -75.17),
    ]
    matrix = parse_matrix_response(points, SAMPLE_MATRIX)
    assert matrix.get(0, 1) is not None
    assert matrix.duration_minutes(0, 1) == 10.0
    assert matrix.distance_miles(0, 1) == pytest.approx(3.11, rel=0.01)


@pytest.mark.phase7
def test_parse_directions_response() -> None:
    stops = [
        RoutePoint(39.95, -75.16),
        RoutePoint(39.96, -75.17),
        RoutePoint(39.97, -75.18),
    ]
    result = parse_directions_response(stops, SAMPLE_DIRECTIONS)
    assert result.duration_minutes == 20.0
    assert result.distance_miles == pytest.approx(6.21, rel=0.01)
    assert result.google_maps_url is not None
    assert "google.com/maps" in result.google_maps_url
    assert result.route_geometry_json is not None


@pytest.mark.phase7
def test_build_maps_directions_url_with_waypoints() -> None:
    stops = [
        RoutePoint(1.0, 2.0),
        RoutePoint(3.0, 4.0),
        RoutePoint(5.0, 6.0),
    ]
    url = build_maps_directions_url(stops)
    assert url is not None
    assert "waypoints=3.0%2C4.0" in url or "waypoints=3.0,4.0" in url


@pytest.mark.phase7
def test_google_provider_requires_api_key() -> None:
    with pytest.raises(ValueError):
        GoogleRoutingProvider("")


@pytest.mark.phase7
def test_create_routing_provider_never_exposes_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "secret-key-12345")
    monkeypatch.setenv("ROUTING_PROVIDER", "google")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.routing import create_routing_provider

    provider = create_routing_provider()
    assert provider.provider_name == "google"
    assert "secret" not in repr(provider)
    assert not hasattr(provider, "api_key")


@pytest.mark.integration
@pytest.mark.phase7
@pytest.mark.skipif(
    not os.getenv("GOOGLE_MAPS_API_KEY"),
    reason="Set GOOGLE_MAPS_API_KEY for Google integration tests",
)
def test_google_geocode_live() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    provider = GoogleRoutingProvider(settings.google_maps_api_key or "")
    try:
        result = provider.geocode("Philadelphia, PA")
        assert 39.0 < result.latitude < 41.0
        assert -76.0 < result.longitude < -74.0
    finally:
        provider.close()


@pytest.mark.integration
@pytest.mark.phase7
@pytest.mark.skipif(
    not os.getenv("GOOGLE_MAPS_API_KEY"),
    reason="Set GOOGLE_MAPS_API_KEY for Google integration tests",
)
def test_google_matrix_and_route_live() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    provider = GoogleRoutingProvider(settings.google_maps_api_key or "")
    options = RoutingOptions(tolls_allowed=True)
    points = [
        RoutePoint(39.9526, -75.1652, label="A"),
        RoutePoint(39.9600, -75.1700, label="B"),
    ]
    try:
        matrix = provider.compute_matrix(points, options)
        assert matrix.duration_minutes(0, 1) > 0

        route = provider.compute_route(points, options)
        assert route.duration_minutes > 0
        assert route.google_maps_url is not None
    finally:
        provider.close()
