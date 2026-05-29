"""Map domain exceptions to HTTP responses."""

from fastapi import HTTPException, status

from app.services.exceptions import ConflictError, NotFoundError, ValidationError


def raise_http_for_domain(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc
    if isinstance(exc, (ValueError, ValidationError)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    raise exc
