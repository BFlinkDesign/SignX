"""JWT-based authentication and authorization for APEX API.

Supports both Supabase Auth (preferred) and legacy JWT tokens.
Implements RBAC with roles: user, admin.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .deps import settings

logger = structlog.get_logger(__name__)

# JWT settings (insecure default for dev; override via env in production)
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()


class AccountInfo(BaseModel):
    """Account membership information."""

    account_id: str
    role: str


class TokenData(BaseModel):
    """Decoded JWT payload with MFA and multi-account support."""

    user_id: str
    account_id: str  # Active/current account
    email: str
    roles: list[str] = ["user"]  # Roles in current account
    mfa_verified: bool = False  # True if 2FA completed this session
    accounts: list[AccountInfo] = []  # All accounts user belongs to
    provider: str = "password"  # "azure", "google", "apple", "password"


def create_access_token(
    data: dict[str, Any], 
    expires_delta: Optional[timedelta] = None,
    mfa_verified: bool = False
) -> str:
    """Create JWT access token with enhanced claims.
    
    Args:
        data: Token payload data (must include "sub", "email", "account_id", etc.)
        expires_delta: Token expiration time (defaults to 7 days)
        mfa_verified: Whether 2FA was completed for this session
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire, 
        "iat": datetime.now(timezone.utc),
        "mfa_verified": mfa_verified,
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.debug("token.created", user_id=data.get("sub"), expires_in=expires_delta, mfa_verified=mfa_verified)
    return encoded_jwt


def create_session_token(
    user_id: str,
    email: str,
    account_id: str,
    provider: str = "password",
    expires_minutes: int = 10
) -> str:
    """Create short-lived session token for 2FA flow.
    
    Used after initial authentication, before 2FA verification.
    Short expiration (default 10 minutes) for security.
    
    Args:
        user_id: User identifier
        email: User email
        account_id: Account identifier
        provider: Auth provider
        expires_minutes: Token expiration in minutes (default 10)
    
    Returns:
        Encoded JWT session token
    """
    data = {
        "sub": user_id,
        "email": email,
        "account_id": account_id,
        "provider": provider,
        "type": "session",  # Indicates this is a session token, not final access token
    }
    return create_access_token(data, expires_delta=timedelta(minutes=expires_minutes), mfa_verified=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Extract and validate JWT from Authorization header.
    
    Supports both Supabase tokens (preferred) and legacy APEX JWT tokens.
    
    Raises:
        HTTPException: 401 if token invalid/expired/missing
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # Try Supabase token verification first
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        try:
            from .supabase_client import get_supabase_client
            from gotrue.errors import AuthApiError
            
            supabase = get_supabase_client()
            # Verify token with Supabase
            user_response = supabase.auth.get_user(token)
            
            if user_response and user_response.user:
                user = user_response.user
                # Extract metadata
                metadata = user.user_metadata or {}
                account_id = metadata.get("account_id", "unknown")
                roles = metadata.get("roles", ["user"])
                provider = metadata.get("provider", "password")
                mfa_verified = metadata.get("mfa_verified", False)
                accounts_data = metadata.get("accounts", [])
                
                # Parse accounts list
                accounts = [
                    AccountInfo(account_id=acc.get("account_id", ""), role=acc.get("role", "viewer"))
                    for acc in accounts_data
                ] if isinstance(accounts_data, list) else []
                
                token_data = TokenData(
                    user_id=user.id,
                    email=user.email or "",
                    account_id=account_id,
                    roles=roles if isinstance(roles, list) else [roles],
                    mfa_verified=mfa_verified,
                    accounts=accounts,
                    provider=provider,
                )
                logger.debug("token.validated.supabase", user_id=user.id, account_id=account_id, mfa_verified=mfa_verified)
                return token_data
        except (ValueError, ImportError) as e:
            # Supabase not available - fall back to legacy JWT
            logger.debug("token.supabase_fallback", error=str(e))
            pass
        except Exception as e:
            # AuthApiError or other - try legacy JWT
            logger.debug("token.supabase_error", error=str(e))
            pass
    
    # Fallback to legacy JWT validation
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        logger.warning("token.invalid", error=str(e))
        raise credentials_exception from e
    
    email = payload.get("email", "")
    account_id = payload.get("account_id", "")
    roles = payload.get("roles", ["user"])
    mfa_verified = payload.get("mfa_verified", False)
    provider = payload.get("provider", "password")
    accounts_data = payload.get("accounts", [])
    
    # Parse accounts list
    accounts = [
        AccountInfo(account_id=acc.get("account_id", ""), role=acc.get("role", "viewer"))
        for acc in accounts_data
    ] if isinstance(accounts_data, list) else []
    
    token_data = TokenData(
        user_id=user_id,
        email=email,
        account_id=account_id,
        roles=roles,
        mfa_verified=mfa_verified,
        accounts=accounts,
        provider=provider,
    )
    logger.debug("token.validated.legacy", user_id=user_id, account_id=account_id, mfa_verified=mfa_verified)
    return token_data


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[TokenData]:
    """Optional authentication - returns None if no token provided.
    
    Use for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(allowed_roles: list[str]):
    """Dependency factory for role-based access control.
    
    Example:
        @router.get("/admin/users")
        async def list_users(
            current_user: TokenData = Depends(require_role(["admin"]))
        ):
            ...
    """
    async def _role_check(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(role in current_user.roles for role in allowed_roles):
            logger.warning("auth.forbidden", user_id=current_user.user_id, required_roles=allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {allowed_roles}",
            )
        return current_user
    
    return _role_check


# Placeholder auth for development
class MockAuth:
    """Mock auth for local development without JWT."""
    
    @staticmethod
    def get_mock_user() -> TokenData:
        """Return a mock user for local dev."""
        return TokenData(
            user_id="dev-user",
            account_id="dev-account",
            email="dev@example.com",
            roles=["admin", "user"],
        )


# Optional: generate mock token for testing
def create_mock_token() -> str:
    """Generate a mock JWT for testing/local dev."""
    data = {
        "sub": "dev-user",
        "email": "dev@example.com",
        "account_id": "dev-account",
        "roles": ["admin", "user"],
    }
    return create_access_token(data)
