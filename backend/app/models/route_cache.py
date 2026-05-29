"""Cached route matrix entries from routing providers."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RouteMatrixCache(Base):
    __tablename__ = "route_matrix_cache"
    __table_args__ = (
        Index(
            "ix_route_matrix_lookup",
            "provider",
            "origin_latitude",
            "origin_longitude",
            "destination_latitude",
            "destination_longitude",
            "travel_mode",
            "tolls_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    origin_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    origin_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    destination_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    destination_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    travel_mode: Mapped[str] = mapped_column(String(50), default="driving", nullable=False)
    tolls_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    distance_miles: Mapped[float] = mapped_column(Float, nullable=False)
    raw_response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
