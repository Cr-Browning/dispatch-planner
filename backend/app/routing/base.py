"""Routing provider contract and value types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class RoutePoint:
    latitude: float
    longitude: float
    label: str | None = None
    address: str | None = None


@dataclass(frozen=True)
class RoutingOptions:
    travel_mode: str = "driving"
    tolls_allowed: bool = True
    departure_time: datetime | None = None


@dataclass(frozen=True)
class GeocodeResult:
    address: str
    latitude: float
    longitude: float
    formatted_address: str | None = None


@dataclass(frozen=True)
class MatrixCell:
    origin_index: int
    destination_index: int
    duration_minutes: float
    distance_miles: float


@dataclass
class RouteMatrix:
    points: list[RoutePoint]
    cells: list[MatrixCell] = field(default_factory=list)

    def get(self, origin_index: int, destination_index: int) -> MatrixCell | None:
        for cell in self.cells:
            if cell.origin_index == origin_index and cell.destination_index == destination_index:
                return cell
        return None

    def duration_minutes(self, origin_index: int, destination_index: int) -> float:
        cell = self.get(origin_index, destination_index)
        if cell is None:
            raise KeyError(f"No matrix cell for ({origin_index}, {destination_index})")
        return cell.duration_minutes

    def distance_miles(self, origin_index: int, destination_index: int) -> float:
        cell = self.get(origin_index, destination_index)
        if cell is None:
            raise KeyError(f"No matrix cell for ({origin_index}, {destination_index})")
        return cell.distance_miles


@dataclass
class RouteResult:
    ordered_stops: list[RoutePoint]
    duration_minutes: float
    distance_miles: float
    google_maps_url: str | None = None
    route_geometry_json: str | None = None


class RoutingProvider(Protocol):
    """Replaceable routing backend (mock, Google, etc.)."""

    @property
    def provider_name(self) -> str: ...

    def geocode(self, address: str) -> GeocodeResult: ...

    def compute_matrix(
        self, points: list[RoutePoint], options: RoutingOptions
    ) -> RouteMatrix: ...

    def compute_route(
        self, ordered_stops: list[RoutePoint], options: RoutingOptions
    ) -> RouteResult: ...
