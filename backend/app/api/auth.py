"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, get_auth_service
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    token = auth.create_token_for_password(body.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    return LoginResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_user: CurrentUser) -> None:
    """Client should discard token; stateless JWT has no server-side session."""


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser, auth: AuthService = Depends(get_auth_service)) -> UserResponse:
    data = auth.me(user)
    return UserResponse(**data)
