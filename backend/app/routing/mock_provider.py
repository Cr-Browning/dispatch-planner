"""Deterministic routing for tests and local development."""

from __future__ import annotations

import json
import math
from urllib.parse import urlencode

from app.routing.base import (
    GeocodeResult,
    MatrixCell,
    RouteMatrix,
    RoutePoint,
    RouteResult,
    RoutingOptions,
)

# Approximate center used for deterministic geocoding offsets
_MOCK_BASE_LAT = 39.9526
_MOCK_BASE_LNG = -75.1652
_MOCK_SPEED_MPH = 30.0
_PROVIDER_NAME = "mock"


def _address_coords(address: str) -> tuple[float, float]:
    """Map an address string to stable coordinates near the mock base."""
    digest = sum(ord(c) for c in address.strip().lower())
    return (
        _MOCK_BASE_LAT + (digest % 500) * 0.0001,
        _MOCK_BASE_LNG + (digest // 500) * 0.0001,
    )


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def travel_minutes(distance_miles: float, *, tolls_allowed: bool) -> float:
    """Deterministic drive time from distance."""
    factor = 1.0 if tolls_allowed else 1.08
    if distance_miles <= 0:
        return 0.0
    return (distance_miles / _MOCK_SPEED_MPH) * 60.0 * factor


def leg_metrics(
    origin: RoutePoint, destination: RoutePoint, options: RoutingOptions
) -> tuple[float, float]:
    miles = haversine_miles(origin.latitude, origin.longitude, destination.latitude, destination.longitude)
    minutes = travel_minutes(miles, tolls_allowed=options.tolls_allowed)
    return minutes, miles


class MockRoutingProvider:
    """Deterministic routing — no network, no randomness."""

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    def geocode(self, address: str) -> GeocodeResult:
        lat, lng = _address_coords(address)
        return GeocodeResult(
            address=address,
            latitude=lat,
            longitude=lng,
            formatted_address=address,
        )

    def compute_matrix(
        self, points: list[RoutePoint], options: RoutingOptions
    ) -> RouteMatrix:
        cells: list[MatrixCell] = []
        for i, origin in enumerate(points):
            for j, destination in enumerate(points):
                if i == j:
                    cells.append(MatrixCell(i, j, 0.0, 0.0))
                    continue
                minutes, miles = leg_metrics(origin, destination, options)
                cells.append(MatrixCell(i, j, minutes, miles))
        return RouteMatrix(points=points, cells=cells)

    def compute_route(
        self, ordered_stops: list[RoutePoint], options: RoutingOptions
    ) -> RouteResult:
        if not ordered_stops:
            return RouteResult(ordered_stops=[], duration_minutes=0.0, distance_miles=0.0)

        total_minutes = 0.0
        total_miles = 0.0
        for i in range(len(ordered_stops) - 1):
            minutes, miles = leg_metrics(ordered_stops[i], ordered_stops[i + 1], options)
            total_minutes += minutes
            total_miles += miles

        url = self._build_maps_url(ordered_stops)
        geometry = json.dumps(
            {
                "type": "LineString",
                "coordinates": [[p.longitude, p.latitude] for p in ordered_stops],
            }
        )
        return RouteResult(
            ordered_stops=ordered_stops,
            duration_minutes=round(total_minutes, 2),
            distance_miles=round(total_miles, 2),
            google_maps_url=url,
            route_geometry_json=geometry,
        )

    @staticmethod
    def _build_maps_url(stops: list[RoutePoint]) -> str | None:
        if len(stops) < 2:
            return None
        origin = f"{stops[0].latitude},{stops[0].longitude}"
        destination = f"{stops[-1].latitude},{stops[-1].longitude}"
        params: dict[str, str] = {"origin": origin, "destination": destination}
        if len(stops) > 2:
            waypoints = "|".join(f"{s.latitude},{s.longitude}" for s in stops[1:-1])
            params["waypoints"] = waypoints
        return f"https://www.google.com/maps/dir/?{urlencode(params)}"
