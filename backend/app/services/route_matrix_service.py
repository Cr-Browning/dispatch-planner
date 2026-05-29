"""Route matrix cache and provider orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RouteMatrixCache
from app.routing.base import MatrixCell, RouteMatrix, RoutePoint, RoutingOptions, RoutingProvider

COORD_PRECISION = 5
DEFAULT_CACHE_TTL_HOURS = 24


def round_coord(value: float) -> float:
    return round(value, COORD_PRECISION)


class RouteMatrixService:
    def __init__(
        self,
        db: Session,
        provider: RoutingProvider,
        *,
        cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS,
    ) -> None:
        self._db = db
        self._provider = provider
        self._cache_ttl = timedelta(hours=cache_ttl_hours)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    def get_matrix(
        self,
        points: list[RoutePoint],
        options: RoutingOptions,
        *,
        force_refresh: bool = False,
    ) -> RouteMatrix:
        if not points:
            return RouteMatrix(points=[], cells=[])

        if not force_refresh:
            cached_matrix = self._matrix_from_cache(points, options)
            if cached_matrix is not None:
                return cached_matrix

        matrix = self._provider.compute_matrix(points, options)
        for cell in matrix.cells:
            if cell.origin_index == cell.destination_index:
                continue
            origin = points[cell.origin_index]
            dest = points[cell.destination_index]
            self._store_cache(origin, dest, options, cell.duration_minutes, cell.distance_miles)
        return matrix

    def _matrix_from_cache(
        self, points: list[RoutePoint], options: RoutingOptions
    ) -> RouteMatrix | None:
        cells: list[MatrixCell] = []
        for i, origin in enumerate(points):
            for j, dest in enumerate(points):
                if i == j:
                    cells.append(MatrixCell(i, j, 0.0, 0.0))
                    continue
                row = self._lookup_cache(origin, dest, options)
                if row is None:
                    return None
                cells.append(MatrixCell(i, j, row.duration_minutes, row.distance_miles))
        return RouteMatrix(points=points, cells=cells)

    def _lookup_cache(
        self,
        origin: RoutePoint,
        destination: RoutePoint,
        options: RoutingOptions,
    ) -> RouteMatrixCache | None:
        row = self._db.scalars(
            select(RouteMatrixCache).where(
                RouteMatrixCache.provider == self.provider_name,
                RouteMatrixCache.origin_latitude == round_coord(origin.latitude),
                RouteMatrixCache.origin_longitude == round_coord(origin.longitude),
                RouteMatrixCache.destination_latitude == round_coord(destination.latitude),
                RouteMatrixCache.destination_longitude == round_coord(destination.longitude),
                RouteMatrixCache.travel_mode == options.travel_mode,
                RouteMatrixCache.tolls_allowed == options.tolls_allowed,
            )
        ).first()
        if row is None:
            return None
        if self._is_stale(row):
            return None
        return row

    def _is_stale(self, row: RouteMatrixCache) -> bool:
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return datetime.now(UTC) - created > self._cache_ttl

    def _store_cache(
        self,
        origin: RoutePoint,
        destination: RoutePoint,
        options: RoutingOptions,
        duration_minutes: float,
        distance_miles: float,
    ) -> RouteMatrixCache:
        existing = self._db.scalars(
            select(RouteMatrixCache).where(
                RouteMatrixCache.provider == self.provider_name,
                RouteMatrixCache.origin_latitude == round_coord(origin.latitude),
                RouteMatrixCache.origin_longitude == round_coord(origin.longitude),
                RouteMatrixCache.destination_latitude == round_coord(destination.latitude),
                RouteMatrixCache.destination_longitude == round_coord(destination.longitude),
                RouteMatrixCache.travel_mode == options.travel_mode,
                RouteMatrixCache.tolls_allowed == options.tolls_allowed,
            )
        ).first()
        payload = json.dumps(
            {"duration_minutes": duration_minutes, "distance_miles": distance_miles}
        )
        if existing is None:
            row = RouteMatrixCache(
                provider=self.provider_name,
                origin_latitude=round_coord(origin.latitude),
                origin_longitude=round_coord(origin.longitude),
                destination_latitude=round_coord(destination.latitude),
                destination_longitude=round_coord(destination.longitude),
                travel_mode=options.travel_mode,
                tolls_allowed=options.tolls_allowed,
                duration_minutes=duration_minutes,
                distance_miles=distance_miles,
                raw_response_json=payload,
            )
            self._db.add(row)
        else:
            existing.duration_minutes = duration_minutes
            existing.distance_miles = distance_miles
            existing.raw_response_json = payload
            row = existing
        self._db.flush()
        return row

    def invalidate_all(self) -> int:
        rows = list(self._db.scalars(select(RouteMatrixCache)).all())
        for row in rows:
            self._db.delete(row)
        self._db.flush()
        return len(rows)
