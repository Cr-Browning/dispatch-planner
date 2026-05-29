"""Routing provider implementations."""

from app.core.config import get_settings
from app.routing.base import (
    GeocodeResult,
    RouteMatrix,
    RoutePoint,
    RouteResult,
    RoutingOptions,
    RoutingProvider,
)
from app.routing.mock_provider import MockRoutingProvider


def create_routing_provider() -> RoutingProvider:
    """Return mock provider unless Google is configured (Phase 7)."""
    settings = get_settings()
    if settings.routing_provider.lower() == "google" and settings.google_maps_api_key:
        from app.routing.google_provider import GoogleRoutingProvider

        return GoogleRoutingProvider(api_key=settings.google_maps_api_key)
    return MockRoutingProvider()


def get_provider_name() -> str:
    return create_routing_provider().provider_name


__all__ = [
    "GeocodeResult",
    "MockRoutingProvider",
    "RouteMatrix",
    "RoutePoint",
    "RouteResult",
    "RoutingOptions",
    "RoutingProvider",
    "create_routing_provider",
]
