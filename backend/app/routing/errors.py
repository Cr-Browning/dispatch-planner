"""Routing provider errors."""


class RoutingProviderError(Exception):
    """Google or other routing backend failure."""


class GeocodeNotFoundError(RoutingProviderError):
    """Address could not be geocoded."""
