"""Google Maps routing provider — backend only, never expose API key to clients."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import httpx

from app.routing.base import (
    GeocodeResult,
    MatrixCell,
    RouteMatrix,
    RoutePoint,
    RouteResult,
    RoutingOptions,
)
from app.routing.errors import GeocodeNotFoundError, RoutingProviderError

_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
_METERS_TO_MILES = 0.000621371
_PROVIDER_NAME = "google"


def _coord_str(point: RoutePoint) -> str:
    return f"{point.latitude},{point.longitude}"


def _seconds_to_minutes(seconds: float) -> float:
    return round(seconds / 60.0, 2)


def _meters_to_miles(meters: float) -> float:
    return round(meters * _METERS_TO_MILES, 2)


def parse_geocode_response(address: str, data: dict[str, Any]) -> GeocodeResult:
    status = data.get("status")
    if status == "ZERO_RESULTS":
        raise GeocodeNotFoundError(f"No results for address: {address}")
    if status != "OK":
        raise RoutingProviderError(
            data.get("error_message") or f"Geocode failed with status {status}"
        )
    results = data.get("results") or []
    if not results:
        raise GeocodeNotFoundError(f"No results for address: {address}")
    location = results[0]["geometry"]["location"]
    return GeocodeResult(
        address=address,
        latitude=float(location["lat"]),
        longitude=float(location["lng"]),
        formatted_address=results[0].get("formatted_address"),
    )


def parse_matrix_response(points: list[RoutePoint], data: dict[str, Any]) -> RouteMatrix:
    status = data.get("status")
    if status != "OK":
        raise RoutingProviderError(
            data.get("error_message") or f"Distance matrix failed with status {status}"
        )
    rows = data.get("rows") or []
    cells: list[MatrixCell] = []
    for i, row in enumerate(rows):
        elements = row.get("elements") or []
        for j, element in enumerate(elements):
            if i == j:
                cells.append(MatrixCell(i, j, 0.0, 0.0))
                continue
            elem_status = element.get("status")
            if elem_status != "OK":
                raise RoutingProviderError(
                    f"Matrix element ({i},{j}) failed with status {elem_status}"
                )
            duration = element["duration"]["value"]
            distance = element["distance"]["value"]
            cells.append(
                MatrixCell(
                    i,
                    j,
                    _seconds_to_minutes(duration),
                    _meters_to_miles(distance),
                )
            )
    return RouteMatrix(points=points, cells=cells)


def parse_directions_response(
    ordered_stops: list[RoutePoint], data: dict[str, Any]
) -> RouteResult:
    status = data.get("status")
    if status != "OK":
        raise RoutingProviderError(
            data.get("error_message") or f"Directions failed with status {status}"
        )
    routes = data.get("routes") or []
    if not routes:
        raise RoutingProviderError("Directions returned no routes")
    route = routes[0]
    total_seconds = 0
    total_meters = 0
    for leg in route.get("legs") or []:
        total_seconds += leg["duration"]["value"]
        total_meters += leg["distance"]["value"]
    polyline = route.get("overview_polyline", {}).get("points")
    geometry = None
    if polyline:
        geometry = json.dumps({"encoded_polyline": polyline})
    return RouteResult(
        ordered_stops=ordered_stops,
        duration_minutes=_seconds_to_minutes(total_seconds),
        distance_miles=_meters_to_miles(total_meters),
        google_maps_url=build_maps_directions_url(ordered_stops),
        route_geometry_json=geometry,
    )


def build_maps_directions_url(stops: list[RoutePoint]) -> str | None:
    if len(stops) < 2:
        return None
    params: dict[str, str] = {
        "api": "1",
        "origin": _coord_str(stops[0]),
        "destination": _coord_str(stops[-1]),
    }
    if len(stops) > 2:
        params["waypoints"] = "|".join(_coord_str(s) for s in stops[1:-1])
    return f"https://www.google.com/maps/dir/?{urlencode(params)}"


class GoogleRoutingProvider:
    """Google Maps Geocoding, Distance Matrix, and Directions APIs."""

    def __init__(self, api_key: str, *, client: httpx.Client | None = None) -> None:
        if not api_key:
            raise ValueError("Google Maps API key is required")
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=30.0)

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    def close(self) -> None:
        self._client.close()

    def geocode(self, address: str) -> GeocodeResult:
        data = self._request(
            _GEOCODE_URL,
            {"address": address},
        )
        return parse_geocode_response(address, data)

    def compute_matrix(
        self, points: list[RoutePoint], options: RoutingOptions
    ) -> RouteMatrix:
        if not points:
            return RouteMatrix(points=[], cells=[])
        origins = "|".join(_coord_str(p) for p in points)
        params: dict[str, str] = {
            "origins": origins,
            "destinations": origins,
            "mode": options.travel_mode,
            "units": "imperial",
        }
        if not options.tolls_allowed:
            params["avoid"] = "tolls"
        data = self._request(_MATRIX_URL, params)
        return parse_matrix_response(points, data)

    def compute_route(
        self, ordered_stops: list[RoutePoint], options: RoutingOptions
    ) -> RouteResult:
        if not ordered_stops:
            return RouteResult(ordered_stops=[], duration_minutes=0.0, distance_miles=0.0)
        if len(ordered_stops) == 1:
            return RouteResult(
                ordered_stops=ordered_stops,
                duration_minutes=0.0,
                distance_miles=0.0,
                google_maps_url=build_maps_directions_url(ordered_stops),
            )

        params: dict[str, str] = {
            "origin": _coord_str(ordered_stops[0]),
            "destination": _coord_str(ordered_stops[-1]),
            "mode": options.travel_mode,
            "units": "imperial",
        }
        if len(ordered_stops) > 2:
            params["waypoints"] = "|".join(_coord_str(s) for s in ordered_stops[1:-1])
        if not options.tolls_allowed:
            params["avoid"] = "tolls"
        data = self._request(_DIRECTIONS_URL, params)
        return parse_directions_response(ordered_stops, data)

    def _request(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        request_params = {**params, "key": self._api_key}
        try:
            response = self._client.get(url, params=request_params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RoutingProviderError(f"Google Maps HTTP error: {exc}") from exc
        return response.json()
