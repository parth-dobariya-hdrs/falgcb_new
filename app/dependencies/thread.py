from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
import os
from typing import Optional
import asyncio
from functools import lru_cache
from app.core.database import db_manager
from app.utils.thread_permissions import verify_thread_ownership
from app.schemas.chat import ChatRequest
from app.schemas.threads import ThreadTitleUpdateRequest

# Security scheme for JWT tokens
security = HTTPBearer()

# Clerk configuration - set these in your environment
from app.core.config import settings

CLERK_INSTANCE_URL = settings.CLERK_INSTANCE_URL or "https://your-instance.clerk.accounts.dev"
CLERK_JWT_VERIFICATION_KEY = settings.CLERK_JWT_VERIFICATION_KEY  # Optional: for static key method
CLERK_JWKS_URL = f"{CLERK_INSTANCE_URL}/.well-known/jwks.json"


# Cache JWKS client to avoid repeated requests
@lru_cache(maxsize=1)
def get_jwks_client():
    """Get cached JWKS client"""
    return PyJWKClient(CLERK_JWKS_URL, cache_jwk_set=True, max_cached_keys=16)


class ClerkUser:
    def __init__(self, clerk_user_id: str, email: Optional[str] = None):
        self.id = clerk_user_id
        self.email = email


async def verify_clerk_jwt_with_jwks(token: str) -> dict:
    """
    Verify Clerk JWT token using JWKS endpoint (recommended method)
    """
    try:
        # Get the signing key from JWKS
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode the JWT token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_signature": True, "verify_aud": False}  # Clerk doesn't always use aud
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError as e:  # ✅ Fixed: Changed from jwt.JWTError to jwt.PyJWTError
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


async def verify_clerk_jwt_with_static_key(token: str) -> dict:
    """
    Verify Clerk JWT token using static verification key (fallback method)
    """
    if not CLERK_JWT_VERIFICATION_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT verification key not configured"
        )

    try:
        # Decode the JWT token
        payload = jwt.decode(
            token,
            CLERK_JWT_VERIFICATION_KEY,
            algorithms=["RS256"],
            options={"verify_signature": True, "verify_aud": False}
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError as e:  # ✅ Fixed: Changed from jwt.JWTError to jwt.PyJWTError
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def verify_clerk_jwt(token: str) -> tuple[str, dict]:  # ✅ Fixed: Changed return type from str to tuple[str, dict]
    """
    Verify Clerk JWT token and return the user ID and payload.
    Tries JWKS first, falls back to static key if available.
    """
    payload = None

    # Try JWKS method first (recommended)
    try:
        payload = await verify_clerk_jwt_with_jwks(token)
    except HTTPException as jwks_error:
        # If JWKS fails and we have a static key, try that
        if CLERK_JWT_VERIFICATION_KEY:
            try:
                payload = await verify_clerk_jwt_with_static_key(token)
            except HTTPException:
                # If both methods fail, raise the original JWKS error
                raise jwks_error
        else:
            # No static key available, raise JWKS error
            raise jwks_error

    # Extract user ID from the payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )

    return user_id, payload


async def get_or_create_user(clerk_user_id: str, payload: dict) -> ClerkUser:
    """
    Get user from database or create if doesn't exist
    """
    async with db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            # Check if user exists
            await cur.execute("SELECT id FROM users WHERE id = %s", (clerk_user_id,))
            result = await cur.fetchone()

            if not result:
                # Extract email from JWT payload if available
                email = payload.get("email")

                # Create user if doesn't exist
                if email:
                    await cur.execute(
                        "INSERT INTO users (id, email) VALUES (%s, %s)",
                        (clerk_user_id, email)
                    )
                else:
                    await cur.execute("INSERT INTO users (id) VALUES (%s)", (clerk_user_id,))

                print(f"Created new user with Clerk ID: {clerk_user_id}")

        return ClerkUser(clerk_user_id, payload.get("email"))


async def current_active_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> ClerkUser:
    """
    Dependency to get the current active user from Clerk JWT token
    """
    # Verify the JWT token and get user ID
    clerk_user_id, payload = await verify_clerk_jwt(credentials.credentials)

    # Get or create user in local database
    user = await get_or_create_user(clerk_user_id, payload)

    return user


# Dependency for request body endpoints
async def verify_from_request_body(
        request: ChatRequest,
        user: ClerkUser = Depends(current_active_user)
):
    """
    Verify thread ownership from request body
    """
    user_id_str = str(user.id)
    print(f"Verifying thread ownership for user_id: {user_id_str}, thread_id: {request.thread_id}")
    await verify_thread_ownership(request.thread_id, user_id_str)


# Dependency for thread_id in path (FIXED BUG)
async def verify_from_path(
        thread_id: str,
        user: ClerkUser = Depends(current_active_user)
):
    """
    Verify thread ownership from path parameter
    """
    user_id_str = str(user.id)
    print(f"Verifying thread ownership for user_id: {user_id_str}, thread_id: {thread_id}")
    await verify_thread_ownership(thread_id, user_id_str)  # Fixed: was request.thread_id


# Dependency for update thread title endpoint
async def verify_from_update_title_req_body(
        request: ThreadTitleUpdateRequest,
        user: ClerkUser = Depends(current_active_user)
):
    """
    Verify thread ownership for thread title update requests
    """
    user_id_str = str(user.id)
    print(f"Verifying thread ownership for user_id: {user_id_str}, thread_id: {request.thread_id}")
    await verify_thread_ownership(request.thread_id, user_id_str)


# Optional: Helper function to get current user info without verification dependencies
async def get_user_from_token(token: str) -> ClerkUser:
    """
    Get user info from token without FastAPI dependencies (useful for background tasks)
    """
    clerk_user_id, payload = await verify_clerk_jwt(token)
    return await get_or_create_user(clerk_user_id, payload)
