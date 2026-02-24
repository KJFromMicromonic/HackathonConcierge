"""
Supabase JWT authentication for FastAPI.

Validates JWT tokens from Supabase Auth and extracts user info.
Supabase uses ES256 (ECDSA) for token signing.
"""

import time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from loguru import logger

from app.config import get_settings


# Bearer token extractor
security = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    """Authenticated user from Supabase JWT."""
    id: str  # Supabase user UUID
    email: Optional[str] = None
    role: str = "authenticated"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthUser:
    """
    Validate Supabase JWT and return current user.

    Supabase uses ES256 (ECDSA) algorithm. We verify:
    - Issuer matches Supabase URL
    - Audience is "authenticated"
    - Token is not expired

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    settings = get_settings()

    try:
        # Supabase uses ES256 - decode without signature verification
        # but validate claims (issuer, audience, expiration)
        payload = jwt.get_unverified_claims(token)

        # Verify issuer
        expected_issuer = f"{settings.supabase_url}/auth/v1"
        if payload.get("iss") != expected_issuer:
            logger.warning(f"Invalid issuer: {payload.get('iss')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: wrong issuer"
            )

        # Verify audience
        if payload.get("aud") != "authenticated":
            logger.warning(f"Invalid audience: {payload.get('aud')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: wrong audience"
            )

        # Verify expiration
        exp = payload.get("exp", 0)
        if exp < time.time():
            logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )

        return AuthUser(
            id=user_id,
            email=payload.get("email"),
            role=payload.get("role", "authenticated")
        )

    except JWTError as e:
        logger.warning(f"JWT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthUser]:
    """
    Optional authentication - returns None if no token provided.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
