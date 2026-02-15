# SignX/APEX Security Architecture Plan

## Executive Summary

SignX/APEX is a structural engineering calculation system that produces PE-stampable calculations with legal liability implications. This document outlines the comprehensive security architecture to protect:

- **Client Project Data**: Confidential engineering designs and calculations
- **PE Stamps**: Legal documents with professional liability
- **User Accounts**: Authentication credentials and access controls
- **Regulatory Compliance**: GDPR, CCPA, and professional engineering regulations

**Current Security Posture**: The system has foundational security controls in place, including JWT authentication with Supabase, Duo 2FA integration, RBAC, audit logging, and container security hardening. This plan builds on these foundations to create a defense-in-depth security architecture.

---

## 1. Authentication Architecture

### 1.1 Current Implementation (Existing)

The system currently supports:
- **Supabase Auth** (primary): OAuth2/OIDC with JWT tokens
- **Legacy JWT** (fallback): HS256 signed tokens
- **OAuth Providers**: Azure AD, Google, Apple
- **Duo 2FA**: Optional push/SMS/phone/passcode verification
- **Account Lockout**: 5 failed attempts, 15-minute lockout

**File Locations**:
- `/home/user/SignX/services/api/src/apex/api/auth.py` - Core authentication
- `/home/user/SignX/services/api/src/apex/api/routes/auth.py` - Auth endpoints
- `/home/user/SignX/services/api/src/apex/api/duo_client.py` - 2FA integration

### 1.2 Enhanced OAuth 2.0 / OIDC Implementation

```python
# /services/api/src/apex/api/oauth_config.py

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class OAuthProvider(str, Enum):
    AZURE = "azure"
    GOOGLE = "google"
    APPLE = "apple"
    SUPABASE = "supabase"

class OAuthConfig(BaseModel):
    """OAuth 2.0 provider configuration."""

    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str] = ["openid", "email", "profile"]

    # PKCE settings (required for mobile/SPA)
    use_pkce: bool = True
    code_challenge_method: str = "S256"

    # Token settings
    access_token_expire_minutes: int = 60  # 1 hour
    refresh_token_expire_days: int = 7

    # Security
    state_ttl_seconds: int = 600  # 10 minutes for CSRF state
    nonce_ttl_seconds: int = 600  # 10 minutes for replay protection


# Azure AD specific configuration for tenant restrictions
AZURE_CONFIG = OAuthConfig(
    provider=OAuthProvider.AZURE,
    client_id="${AZURE_CLIENT_ID}",
    client_secret="${AZURE_CLIENT_SECRET}",
    authorization_url="https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/authorize",
    token_url="https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/token",
    userinfo_url="https://graph.microsoft.com/oidc/userinfo",
    scopes=["openid", "email", "profile", "offline_access"],
    use_pkce=True,
)


class PKCEVerifier:
    """PKCE code verifier generation and validation."""

    @staticmethod
    def generate_verifier(length: int = 64) -> str:
        """Generate cryptographically secure code verifier."""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "-._~"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_challenge(verifier: str) -> str:
        """Generate S256 code challenge from verifier."""
        import hashlib
        import base64
        digest = hashlib.sha256(verifier.encode('ascii')).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
```

### 1.3 MFA Requirements Policy

```python
# /services/api/src/apex/api/mfa_policy.py

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel

class MFARequirement(str, Enum):
    DISABLED = "disabled"      # MFA not required
    OPTIONAL = "optional"      # User can opt-in
    REQUIRED = "required"      # Must enable MFA
    ENFORCED = "enforced"      # MFA on every login

class MFAPolicy(BaseModel):
    """MFA enforcement policy per role/action."""

    # Role-based MFA requirements
    role_requirements: dict[str, MFARequirement] = {
        "admin": MFARequirement.ENFORCED,
        "pe": MFARequirement.ENFORCED,       # PE stamp requires MFA
        "engineer": MFARequirement.REQUIRED,
        "approver": MFARequirement.REQUIRED,
        "viewer": MFARequirement.OPTIONAL,
    }

    # Action-based MFA requirements (override role)
    action_requirements: dict[str, MFARequirement] = {
        "calculation.stamp": MFARequirement.ENFORCED,
        "calculation.approve": MFARequirement.ENFORCED,
        "project.delete": MFARequirement.ENFORCED,
        "admin.manage_users": MFARequirement.ENFORCED,
        "file.delete": MFARequirement.REQUIRED,
    }

    # Session-based MFA (re-verify after idle)
    session_mfa_timeout_minutes: int = 30  # Re-verify after 30 min idle for sensitive actions

    def requires_mfa(self, role: str, action: Optional[str] = None) -> MFARequirement:
        """Determine MFA requirement for role/action combination."""
        # Action-level takes precedence
        if action and action in self.action_requirements:
            return self.action_requirements[action]

        # Fall back to role-level
        return self.role_requirements.get(role, MFARequirement.OPTIONAL)


# Enforcement decorator
from functools import wraps
from fastapi import HTTPException, status

def require_mfa_for_action(action: str):
    """Decorator to enforce MFA for specific actions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            policy = MFAPolicy()
            requirement = policy.requires_mfa(
                role=current_user.roles[0] if current_user.roles else "viewer",
                action=action
            )

            if requirement in (MFARequirement.REQUIRED, MFARequirement.ENFORCED):
                if not current_user.mfa_verified:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"MFA verification required for action: {action}",
                        headers={"X-MFA-Required": "true"}
                    )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

### 1.4 Session Management

```python
# /services/api/src/apex/api/session_manager.py

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from pydantic import BaseModel
from redis.asyncio import Redis

from .deps import settings

logger = structlog.get_logger(__name__)


class SessionConfig:
    """Session security configuration."""

    # Session duration
    SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days max session
    IDLE_TIMEOUT_SECONDS = 30 * 60       # 30 min idle timeout

    # Token rotation
    ROTATE_REFRESH_TOKEN = True           # Issue new refresh token on use
    REFRESH_TOKEN_REUSE_INTERVAL = 2      # Grace period for parallel requests

    # Security flags
    SECURE_COOKIE = True                  # HTTPS only
    HTTPONLY_COOKIE = True                # No JavaScript access
    SAMESITE_COOKIE = "Strict"            # CSRF protection

    # Concurrent sessions
    MAX_SESSIONS_PER_USER = 5             # Limit concurrent sessions


class Session(BaseModel):
    """User session data."""

    session_id: str
    user_id: str
    account_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    mfa_verified: bool = False
    mfa_verified_at: Optional[datetime] = None


class SessionManager:
    """Secure session management with Redis backing."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[Redis] = None

    async def get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url)
        return self._redis

    async def create_session(
        self,
        user_id: str,
        account_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        mfa_verified: bool = False,
    ) -> Session:
        """Create new session with security metadata."""
        redis = await self.get_redis()

        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            account_id=account_id,
            created_at=now,
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent,
            mfa_verified=mfa_verified,
            mfa_verified_at=now if mfa_verified else None,
        )

        # Store in Redis with TTL
        key = f"session:{session_id}"
        await redis.setex(
            key,
            SessionConfig.SESSION_TTL_SECONDS,
            session.model_dump_json()
        )

        # Track user's sessions for concurrent limit
        user_sessions_key = f"user_sessions:{user_id}"
        await redis.zadd(user_sessions_key, {session_id: now.timestamp()})
        await redis.expire(user_sessions_key, SessionConfig.SESSION_TTL_SECONDS)

        # Enforce max sessions
        await self._enforce_max_sessions(user_id)

        logger.info("session.created", user_id=user_id, session_id=session_id[:8])
        return session

    async def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate session and update activity timestamp."""
        redis = await self.get_redis()

        key = f"session:{session_id}"
        data = await redis.get(key)

        if not data:
            return None

        session = Session.model_validate_json(data)

        # Check idle timeout
        now = datetime.now(timezone.utc)
        idle_seconds = (now - session.last_activity).total_seconds()

        if idle_seconds > SessionConfig.IDLE_TIMEOUT_SECONDS:
            await self.revoke_session(session_id)
            logger.info("session.idle_timeout", session_id=session_id[:8])
            return None

        # Update last activity
        session.last_activity = now
        await redis.setex(
            key,
            SessionConfig.SESSION_TTL_SECONDS,
            session.model_dump_json()
        )

        return session

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session."""
        redis = await self.get_redis()

        key = f"session:{session_id}"
        data = await redis.get(key)

        if data:
            session = Session.model_validate_json(data)
            user_sessions_key = f"user_sessions:{session.user_id}"
            await redis.zrem(user_sessions_key, session_id)

        deleted = await redis.delete(key)
        logger.info("session.revoked", session_id=session_id[:8])
        return deleted > 0

    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user (logout everywhere)."""
        redis = await self.get_redis()

        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await redis.zrange(user_sessions_key, 0, -1)

        count = 0
        for session_id in session_ids:
            await redis.delete(f"session:{session_id.decode()}")
            count += 1

        await redis.delete(user_sessions_key)
        logger.info("session.revoked_all", user_id=user_id, count=count)
        return count

    async def _enforce_max_sessions(self, user_id: str) -> None:
        """Remove oldest sessions if over limit."""
        redis = await self.get_redis()

        user_sessions_key = f"user_sessions:{user_id}"
        session_count = await redis.zcard(user_sessions_key)

        if session_count > SessionConfig.MAX_SESSIONS_PER_USER:
            # Remove oldest sessions
            excess = session_count - SessionConfig.MAX_SESSIONS_PER_USER
            oldest = await redis.zrange(user_sessions_key, 0, excess - 1)

            for session_id in oldest:
                await redis.delete(f"session:{session_id.decode()}")
                await redis.zrem(user_sessions_key, session_id)

            logger.info("session.limit_enforced", user_id=user_id, removed=excess)
```

### 1.5 Token Refresh Strategy

```python
# /services/api/src/apex/api/token_refresh.py

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import HTTPException, status
from jose import jwt, JWTError
from pydantic import BaseModel
from redis.asyncio import Redis

from .deps import settings
from .auth import JWT_SECRET_KEY, JWT_ALGORITHM

logger = structlog.get_logger(__name__)


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    access_expires_in: int  # seconds
    refresh_expires_in: int  # seconds


class RefreshTokenManager:
    """Secure refresh token management with rotation."""

    ACCESS_TOKEN_EXPIRE_MINUTES = 15     # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS = 7        # Longer refresh tokens
    REFRESH_TOKEN_REUSE_SECONDS = 2      # Grace period for concurrent requests

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[Redis] = None

    async def get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url)
        return self._redis

    async def create_token_pair(
        self,
        user_id: str,
        account_id: str,
        email: str,
        roles: list[str],
        mfa_verified: bool = False,
    ) -> TokenPair:
        """Create new access/refresh token pair."""
        now = datetime.now(timezone.utc)

        # Create access token (short-lived)
        access_exp = now + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_payload = {
            "sub": user_id,
            "account_id": account_id,
            "email": email,
            "roles": roles,
            "mfa_verified": mfa_verified,
            "type": "access",
            "iat": now.timestamp(),
            "exp": access_exp.timestamp(),
        }
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # Create refresh token (longer-lived, opaque)
        refresh_token = secrets.token_urlsafe(64)
        refresh_exp = now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

        # Store refresh token metadata in Redis
        redis = await self.get_redis()
        refresh_key = f"refresh_token:{refresh_token}"
        refresh_data = {
            "user_id": user_id,
            "account_id": account_id,
            "email": email,
            "roles": ",".join(roles),
            "mfa_verified": "1" if mfa_verified else "0",
            "created_at": str(now.timestamp()),
            "used": "0",
        }
        await redis.hset(refresh_key, mapping=refresh_data)
        await redis.expireat(refresh_key, refresh_exp)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=self.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Refresh tokens with rotation (invalidates old refresh token)."""
        redis = await self.get_redis()
        refresh_key = f"refresh_token:{refresh_token}"

        # Get refresh token data
        data = await redis.hgetall(refresh_key)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Decode Redis byte strings
        data = {k.decode(): v.decode() for k, v in data.items()}

        # Check if already used (token rotation)
        if data.get("used") == "1":
            created_at = float(data.get("created_at", 0))
            if time.time() - created_at > self.REFRESH_TOKEN_REUSE_SECONDS:
                # Possible token theft - revoke all user sessions
                logger.warning(
                    "refresh_token.reuse_detected",
                    user_id=data.get("user_id"),
                    token_prefix=refresh_token[:8]
                )
                await self._revoke_user_tokens(data.get("user_id", ""))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Security violation: token reuse detected. Please login again."
                )

        # Mark as used
        await redis.hset(refresh_key, "used", "1")

        # Create new token pair
        new_tokens = await self.create_token_pair(
            user_id=data.get("user_id", ""),
            account_id=data.get("account_id", ""),
            email=data.get("email", ""),
            roles=data.get("roles", "").split(","),
            mfa_verified=data.get("mfa_verified") == "1",
        )

        # Schedule old token deletion (grace period for parallel requests)
        await redis.expire(refresh_key, self.REFRESH_TOKEN_REUSE_SECONDS)

        logger.debug("refresh_token.rotated", user_id=data.get("user_id"))
        return new_tokens

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a specific refresh token."""
        redis = await self.get_redis()
        refresh_key = f"refresh_token:{refresh_token}"
        deleted = await redis.delete(refresh_key)
        return deleted > 0

    async def _revoke_user_tokens(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        # This would need a user -> tokens index in production
        logger.warning("refresh_token.revoke_all", user_id=user_id)
```

### 1.6 Password Policies

The current implementation in `/home/user/SignX/services/api/src/apex/api/auth_password.py` includes:
- Minimum 8 characters
- 3 of 4 complexity requirements (upper, lower, digit, special)
- Common password blocklist
- bcrypt hashing with 12 rounds

**Enhanced Password Policy**:

```python
# /services/api/src/apex/api/password_policy.py

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel

class PasswordPolicy(BaseModel):
    """Enhanced password policy for SignX."""

    # Length requirements
    min_length: int = 12        # NIST 800-63B recommends 8+, we use 12
    max_length: int = 128       # Prevent bcrypt truncation issues

    # Complexity (NIST recommends against complex rules, but engineering systems need them)
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    min_complexity_types: int = 3  # At least 3 of 4 types

    # History
    prevent_reuse_count: int = 12  # Cannot reuse last 12 passwords

    # Expiration (NIST no longer recommends forced rotation)
    max_age_days: Optional[int] = None  # No forced rotation

    # Breach checking
    check_breached_passwords: bool = True  # Check against HaveIBeenPwned

    # Context-specific
    prevent_username_in_password: bool = True
    prevent_email_in_password: bool = True

    def validate(self, password: str, username: Optional[str] = None, email: Optional[str] = None) -> tuple[bool, list[str]]:
        """Validate password against policy."""
        errors: list[str] = []

        # Length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        if len(password) > self.max_length:
            errors.append(f"Password must be at most {self.max_length} characters")

        # Complexity
        complexity_count = 0
        if self.require_uppercase and re.search(r'[A-Z]', password):
            complexity_count += 1
        if self.require_lowercase and re.search(r'[a-z]', password):
            complexity_count += 1
        if self.require_digit and re.search(r'\d', password):
            complexity_count += 1
        if self.require_special and re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            complexity_count += 1

        if complexity_count < self.min_complexity_types:
            errors.append(f"Password must contain at least {self.min_complexity_types} of: uppercase, lowercase, digit, special character")

        # Context checks
        if self.prevent_username_in_password and username:
            if username.lower() in password.lower():
                errors.append("Password cannot contain your username")

        if self.prevent_email_in_password and email:
            email_local = email.split('@')[0].lower()
            if email_local in password.lower():
                errors.append("Password cannot contain your email address")

        return len(errors) == 0, errors


# Breach checking (HaveIBeenPwned k-anonymity API)
import hashlib
import httpx

async def check_password_breached(password: str) -> bool:
    """Check if password appears in breach databases using k-anonymity."""
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=5.0
            )
            response.raise_for_status()

            # Check if our suffix appears in the response
            for line in response.text.splitlines():
                hash_suffix, count = line.split(':')
                if hash_suffix == suffix:
                    return True  # Password is breached

            return False  # Password not found in breaches
    except Exception:
        # Fail open - don't block registration if API is down
        return False
```

---

## 2. Authorization (RBAC) Architecture

### 2.1 Current Implementation (Existing)

The system has RBAC infrastructure in:
- `/home/user/SignX/services/api/src/apex/api/rbac.py` - RBAC decorators
- `/home/user/SignX/services/api/alembic/versions/009_add_audit_rbac_compliance_tables.py` - Database schema

### 2.2 Role Definitions

```yaml
# /services/api/config/rbac_roles.yaml

roles:
  admin:
    description: "Full system administrator"
    permissions:
      - "*"  # All permissions
    mfa_required: enforced

  pe_engineer:
    description: "Licensed Professional Engineer - can stamp calculations"
    permissions:
      - calculation.create
      - calculation.read
      - calculation.update
      - calculation.approve
      - calculation.stamp       # PE stamp authority
      - project.create
      - project.read
      - project.update
      - project.submit
      - file.upload
      - file.read
      - audit.read
    mfa_required: enforced
    additional_requirements:
      - pe_license_verified: true
      - pe_license_state: required

  engineer:
    description: "Design engineer - creates calculations"
    permissions:
      - calculation.create
      - calculation.read
      - calculation.update
      - project.create
      - project.read
      - project.update
      - project.submit
      - file.upload
      - file.read
    mfa_required: required

  designer:
    description: "Design drafter - creates projects, limited calculations"
    permissions:
      - calculation.read
      - project.create
      - project.read
      - project.update
      - file.upload
      - file.read
    mfa_required: optional

  viewer:
    description: "Read-only access to projects"
    permissions:
      - calculation.read
      - project.read
      - file.read
    mfa_required: optional

  approver:
    description: "QA/review role - can approve but not stamp"
    permissions:
      - calculation.read
      - calculation.approve
      - project.read
      - project.approve
      - file.read
      - audit.read
    mfa_required: required
```

### 2.3 Permission Matrix

| Permission | Admin | PE Engineer | Engineer | Designer | Viewer | Approver |
|------------|-------|-------------|----------|----------|--------|----------|
| calculation.create | Yes | Yes | Yes | No | No | No |
| calculation.read | Yes | Yes | Yes | Yes | Yes | Yes |
| calculation.update | Yes | Yes | Yes | No | No | No |
| calculation.approve | Yes | Yes | No | No | No | Yes |
| calculation.stamp | Yes | Yes | No | No | No | No |
| calculation.delete | Yes | No | No | No | No | No |
| project.create | Yes | Yes | Yes | Yes | No | No |
| project.read | Yes | Yes | Yes | Yes | Yes | Yes |
| project.read_all | Yes | No | No | No | No | Yes |
| project.update | Yes | Yes | Yes | Yes | No | No |
| project.delete | Yes | No | No | No | No | No |
| project.submit | Yes | Yes | Yes | No | No | No |
| project.approve | Yes | Yes | No | No | No | Yes |
| file.upload | Yes | Yes | Yes | Yes | No | No |
| file.read | Yes | Yes | Yes | Yes | Yes | Yes |
| file.delete | Yes | Yes | No | No | No | No |
| audit.read | Yes | Yes | No | No | No | Yes |
| admin.manage_users | Yes | No | No | No | No | No |
| admin.manage_permissions | Yes | No | No | No | No | No |

### 2.4 Resource-Level Access Control

```python
# /services/api/src/apex/api/resource_access.py

from __future__ import annotations

from enum import Enum
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import TokenData
from .rbac import check_permission

logger = structlog.get_logger(__name__)


class ResourceOwnership(str, Enum):
    """Resource ownership levels."""
    OWNER = "owner"           # Created the resource
    ACCOUNT_MEMBER = "account" # In same account
    SHARED = "shared"         # Explicitly shared
    PUBLIC = "public"         # Publicly accessible


async def check_resource_access(
    db: AsyncSession,
    user: TokenData,
    resource_type: str,
    resource_id: str,
    required_permission: str,
) -> bool:
    """Check if user can access a specific resource.

    Implements organization isolation and resource-level ACLs.
    """
    # Admins can access everything
    if "admin" in user.roles:
        return True

    # Check base permission first
    has_permission = await check_permission(db, user, required_permission)
    if not has_permission:
        return False

    # Get resource ownership
    ownership = await _get_resource_ownership(db, resource_type, resource_id, user)

    # Resource-level access rules
    if ownership == ResourceOwnership.OWNER:
        return True

    if ownership == ResourceOwnership.ACCOUNT_MEMBER:
        # Account members need read_all permission for resources they don't own
        if required_permission.endswith(".read"):
            read_all_perm = required_permission.replace(".read", ".read_all")
            return await check_permission(db, user, read_all_perm)
        return True  # Same account, has base permission

    if ownership == ResourceOwnership.SHARED:
        # Check sharing permissions
        return await _check_sharing_permission(db, user, resource_type, resource_id, required_permission)

    if ownership == ResourceOwnership.PUBLIC:
        # Public resources only allow read
        return required_permission.endswith(".read")

    return False


async def _get_resource_ownership(
    db: AsyncSession,
    resource_type: str,
    resource_id: str,
    user: TokenData,
) -> ResourceOwnership:
    """Determine user's relationship to a resource."""
    # This would query the database for resource ownership
    # Simplified example:

    from sqlalchemy import select, text

    # Query resource owner and account
    query = text(f"""
        SELECT created_by, account_id, is_public
        FROM {resource_type}s
        WHERE id = :resource_id
    """)

    result = await db.execute(query, {"resource_id": resource_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    created_by, account_id, is_public = row

    if created_by == user.user_id:
        return ResourceOwnership.OWNER

    if account_id == user.account_id:
        return ResourceOwnership.ACCOUNT_MEMBER

    if is_public:
        return ResourceOwnership.PUBLIC

    # Check explicit sharing
    sharing_query = text("""
        SELECT 1 FROM resource_shares
        WHERE resource_type = :resource_type
        AND resource_id = :resource_id
        AND (shared_with_user = :user_id OR shared_with_account = :account_id)
    """)
    sharing_result = await db.execute(sharing_query, {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user.user_id,
        "account_id": user.account_id,
    })

    if sharing_result.fetchone():
        return ResourceOwnership.SHARED

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to this resource"
    )


async def _check_sharing_permission(
    db: AsyncSession,
    user: TokenData,
    resource_type: str,
    resource_id: str,
    required_permission: str,
) -> bool:
    """Check if shared resource allows the required permission."""
    from sqlalchemy import text

    query = text("""
        SELECT permissions FROM resource_shares
        WHERE resource_type = :resource_type
        AND resource_id = :resource_id
        AND (shared_with_user = :user_id OR shared_with_account = :account_id)
    """)

    result = await db.execute(query, {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user.user_id,
        "account_id": user.account_id,
    })

    row = result.fetchone()
    if row:
        shared_permissions = row[0] or []
        return required_permission in shared_permissions

    return False
```

### 2.5 Organization Isolation

```python
# /services/api/src/apex/api/org_isolation.py

from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .auth import get_current_user, TokenData
from .db import get_db


class OrganizationFilter:
    """Middleware for automatic organization isolation."""

    @staticmethod
    def apply_account_filter(query, user: TokenData, model, allow_cross_account: bool = False):
        """Apply account_id filter to queries.

        Args:
            query: SQLAlchemy query
            user: Current user
            model: SQLAlchemy model with account_id column
            allow_cross_account: If True, admins can query across accounts

        Returns:
            Filtered query
        """
        # Admins with explicit cross-account permission
        if allow_cross_account and "admin" in user.roles:
            return query

        # Standard isolation - filter by account_id
        return query.where(model.account_id == user.account_id)


# Dependency for auto-filtered queries
async def get_org_scoped_db(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[AsyncSession, str]:
    """Get database session with organization context."""
    return db, current_user.account_id
```

---

## 3. API Security

### 3.1 Current Implementation (Existing)

The system has:
- Rate limiting via SlowAPI (100 req/min default)
- CORS configuration via environment variables
- Body size limits (256KB default)
- Request tracing via X-Request-ID

### 3.2 Enhanced Rate Limiting Strategy

```python
# /services/api/src/apex/api/rate_limiting.py

from __future__ import annotations

from typing import Callable, Optional
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


class RateLimitConfig:
    """Rate limiting configuration."""

    # Default limits (can be overridden via environment)
    DEFAULT_LIMITS = {
        "anonymous": "30/minute",      # Unauthenticated requests
        "authenticated": "100/minute",  # Authenticated users
        "admin": "500/minute",          # Admin users
    }

    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        # Auth endpoints (brute force protection)
        "/auth/token": "5/minute",
        "/auth/register": "3/minute",
        "/auth/password-reset": "3/minute",
        "/auth/verify-2fa": "10/minute",

        # Computation-heavy endpoints
        "/api/v1/signcalc/run": "30/minute",
        "/api/v1/calculations/complex": "10/minute",

        # File uploads
        "/api/v1/files/upload": "20/minute",

        # Bulk operations
        "/api/v1/projects/bulk": "5/minute",
    }

    # Burst allowance
    BURST_MULTIPLIER = 2.0  # Allow 2x burst for short periods


def create_rate_key_func() -> Callable:
    """Create rate limit key function with user-aware limits."""

    def rate_key_func(request: Request) -> str:
        """Extract rate limit key from request."""
        # Try to get user ID from JWT
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                from .auth import JWT_SECRET_KEY, JWT_ALGORITHM

                token = auth_header[7:]
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except Exception:
                pass

        # Fall back to API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"

        # Fall back to IP
        return f"ip:{get_remote_address(request)}"

    return rate_key_func


def get_endpoint_limit(path: str) -> Optional[str]:
    """Get rate limit for specific endpoint."""
    # Exact match
    if path in RateLimitConfig.ENDPOINT_LIMITS:
        return RateLimitConfig.ENDPOINT_LIMITS[path]

    # Prefix match
    for endpoint, limit in RateLimitConfig.ENDPOINT_LIMITS.items():
        if path.startswith(endpoint):
            return limit

    return None
```

### 3.3 Input Validation

```python
# /services/api/src/apex/api/validators.py

from __future__ import annotations

import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# Input sanitization patterns
DANGEROUS_PATTERNS = [
    r'<script[^>]*>',           # XSS script tags
    r'javascript:',              # JavaScript URLs
    r'on\w+\s*=',               # Event handlers
    r'data:text/html',           # Data URLs with HTML
    r'\{\{.*\}\}',              # Template injection
    r'\$\{.*\}',                # String interpolation
]

SQL_INJECTION_PATTERNS = [
    r"'\s*or\s+'",              # OR injection
    r";\s*drop\s+",             # DROP injection
    r"union\s+select",          # UNION injection
    r"--\s*$",                  # Comment injection
]


class SecureString(str):
    """String type with automatic sanitization."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("String required")

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Invalid characters detected")

        # HTML entity encoding for XSS prevention
        v = v.replace('&', '&amp;')
        v = v.replace('<', '&lt;')
        v = v.replace('>', '&gt;')
        v = v.replace('"', '&quot;')
        v = v.replace("'", '&#x27;')

        return v


class ProjectInput(BaseModel):
    """Example validated input model."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=500)

    @field_validator('name', 'description', 'location', mode='before')
    @classmethod
    def sanitize_strings(cls, v: Any) -> Any:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("String required")

        # Trim whitespace
        v = v.strip()

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid characters in input")

        return v

    @model_validator(mode='after')
    def validate_business_rules(self):
        """Business-level validation."""
        if self.name and self.name.lower() in ('admin', 'system', 'root'):
            raise ValueError("Reserved project name")
        return self


# Path traversal prevention
def validate_file_path(path: str, allowed_prefix: str) -> str:
    """Validate file path to prevent traversal attacks."""
    import os

    # Normalize path
    normalized = os.path.normpath(path)

    # Check for traversal
    if '..' in normalized:
        raise ValueError("Path traversal not allowed")

    # Ensure path starts with allowed prefix
    if not normalized.startswith(allowed_prefix):
        raise ValueError(f"Path must be within {allowed_prefix}")

    return normalized
```

### 3.4 CORS Policy

```python
# /services/api/src/apex/api/cors_config.py

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class CORSPolicy(BaseModel):
    """Production CORS configuration."""

    # Allowed origins (explicit list, no wildcards in production)
    allow_origins: list[str] = [
        "https://app.signxstudio.com",
        "https://staging.signxstudio.com",
    ]

    # Development origins (only in dev/staging)
    dev_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Credentials handling
    allow_credentials: bool = True  # Required for cookies/auth

    # Allowed methods
    allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

    # Allowed headers
    allow_headers: list[str] = [
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Idempotency-Key",
        "X-API-Key",
    ]

    # Exposed headers (readable by client)
    expose_headers: list[str] = [
        "X-Trace-ID",
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ]

    # Preflight cache duration
    max_age: int = 3600  # 1 hour

    def get_origins(self, env: str) -> list[str]:
        """Get allowed origins based on environment."""
        if env in ("dev", "development", "staging"):
            return self.allow_origins + self.dev_origins
        return self.allow_origins
```

### 3.5 Request Signing for Critical Operations

```python
# /services/api/src/apex/api/request_signing.py

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

from fastapi import HTTPException, Request, status
from pydantic import BaseModel


class SignedRequestConfig(BaseModel):
    """Configuration for request signing."""

    # Signature algorithm
    algorithm: str = "sha256"

    # Timestamp tolerance (prevent replay attacks)
    timestamp_tolerance_seconds: int = 300  # 5 minutes

    # Required for these endpoints
    required_endpoints: list[str] = [
        "/api/v1/calculations/stamp",
        "/api/v1/calculations/approve",
        "/api/v1/projects/delete",
        "/api/v1/admin/users",
    ]


async def verify_request_signature(
    request: Request,
    secret_key: str,
) -> bool:
    """Verify HMAC signature on critical requests.

    Expected headers:
    - X-Signature-Timestamp: Unix timestamp
    - X-Signature: HMAC-SHA256 signature

    Signature is computed over:
    - HTTP method
    - Request path
    - Request body (if present)
    - Timestamp
    """
    config = SignedRequestConfig()

    # Check if signing is required for this endpoint
    if not any(request.url.path.startswith(ep) for ep in config.required_endpoints):
        return True  # Not required

    # Get signature headers
    timestamp_str = request.headers.get("X-Signature-Timestamp")
    signature = request.headers.get("X-Signature")

    if not timestamp_str or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request signature required"
        )

    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format"
        )

    current_time = int(time.time())
    if abs(current_time - timestamp) > config.timestamp_tolerance_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request timestamp expired"
        )

    # Get request body
    body = await request.body()

    # Compute expected signature
    message = f"{request.method}:{request.url.path}:{body.decode() if body else ''}:{timestamp}"
    expected_signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature"
        )

    return True
```

---

## 4. Data Security

### 4.1 Encryption at Rest

```yaml
# Database encryption configuration (PostgreSQL)
# Add to docker-compose.prod.yml or infra/compose.yaml

services:
  db:
    environment:
      # Enable TDE (Transparent Data Encryption) for PostgreSQL Enterprise
      # For community edition, use application-level encryption

      # SSL/TLS for connections
      - POSTGRES_SSL=on
      - POSTGRES_SSL_CERT_FILE=/etc/ssl/certs/server.crt
      - POSTGRES_SSL_KEY_FILE=/etc/ssl/private/server.key

    command:
      - postgres
      - -c
      - ssl=on
      - -c
      - ssl_cert_file=/etc/ssl/certs/server.crt
      - -c
      - ssl_key_file=/etc/ssl/private/server.key
```

```python
# /services/api/src/apex/api/encryption.py

from __future__ import annotations

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .deps import settings


class FieldEncryption:
    """Application-level field encryption for sensitive data."""

    def __init__(self, master_key: Optional[str] = None):
        """Initialize with master key from environment."""
        master_key = master_key or settings.ENCRYPTION_KEY
        if not master_key:
            raise ValueError("ENCRYPTION_KEY environment variable required")

        # Derive encryption key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"signx-field-encryption-salt",  # Static salt for determinism
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string field."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string field."""
        return self._fernet.decrypt(ciphertext.encode()).decode()


# Encrypted column type for SQLAlchemy
from sqlalchemy import TypeDecorator, String

class EncryptedString(TypeDecorator):
    """SQLAlchemy column type for encrypted strings."""

    impl = String
    cache_ok = True

    def __init__(self, length: int = 500):
        super().__init__(length=length)
        self._encryptor = None

    @property
    def encryptor(self) -> FieldEncryption:
        if self._encryptor is None:
            self._encryptor = FieldEncryption()
        return self._encryptor

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encryptor.encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encryptor.decrypt(value)
        return value


# Usage in models:
# class User(Base):
#     ssn = Column(EncryptedString(100))  # Encrypted at rest
```

### 4.2 Encryption in Transit

```python
# /services/api/src/apex/api/tls_config.py

from __future__ import annotations

from pydantic import BaseModel


class TLSConfig(BaseModel):
    """TLS 1.3 configuration for production."""

    # Minimum TLS version
    min_version: str = "TLSv1.3"

    # Cipher suites (TLS 1.3)
    ciphers: list[str] = [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
    ]

    # HSTS configuration
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True

    # Certificate requirements
    require_client_cert: bool = False  # mTLS (optional)
    verify_client_cert: bool = False


# Nginx/Caddy configuration example
NGINX_TLS_CONFIG = """
ssl_protocols TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256';

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Session resumption
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;
"""
```

### 4.3 PII Handling

```python
# /services/api/src/apex/api/pii_handler.py

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class PIICategory(str, Enum):
    """PII data categories."""
    DIRECT_IDENTIFIER = "direct_identifier"    # Name, email, SSN
    INDIRECT_IDENTIFIER = "indirect_identifier" # IP address, device ID
    SENSITIVE = "sensitive"                     # Financial, health data
    DERIVED = "derived"                         # Inferred data


class PIIField(Enum):
    """Known PII fields and their handling rules."""

    # Format: (field_pattern, category, retention_days, should_encrypt)
    EMAIL = (r"email", PIICategory.DIRECT_IDENTIFIER, 2555, True)  # 7 years
    NAME = (r"(first_|last_)?name", PIICategory.DIRECT_IDENTIFIER, 2555, True)
    PHONE = (r"phone|mobile", PIICategory.DIRECT_IDENTIFIER, 2555, True)
    SSN = (r"ssn|social_security", PIICategory.DIRECT_IDENTIFIER, 365, True)
    IP_ADDRESS = (r"ip_address|client_ip", PIICategory.INDIRECT_IDENTIFIER, 90, False)
    PE_LICENSE = (r"pe_license", PIICategory.DIRECT_IDENTIFIER, 2555, True)


class PIIHandler:
    """Handle PII with appropriate protections."""

    @staticmethod
    def hash_pii(value: str, salt: Optional[str] = None) -> str:
        """One-way hash PII for pseudonymization."""
        salt = salt or "signx-pii-salt"
        return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email for display/logs."""
        if '@' not in email:
            return '***'
        local, domain = email.split('@')
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number for display/logs."""
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 4:
            return '***'
        return '*' * (len(digits) - 4) + digits[-4:]

    @staticmethod
    def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
        """Remove or mask PII from log data."""
        pii_patterns = {
            'email': PIIHandler.mask_email,
            'phone': PIIHandler.mask_phone,
            'password': lambda x: '***',
            'token': lambda x: x[:8] + '...' if len(x) > 8 else '***',
            'secret': lambda x: '***',
            'ssn': lambda x: '***-**-' + x[-4:] if len(x) >= 4 else '***',
        }

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if key matches PII pattern
            for pattern, mask_func in pii_patterns.items():
                if pattern in key_lower:
                    if isinstance(value, str):
                        sanitized[key] = mask_func(value)
                    else:
                        sanitized[key] = '***'
                    break
            else:
                # Recursively sanitize nested dicts
                if isinstance(value, dict):
                    sanitized[key] = PIIHandler.sanitize_log_data(value)
                else:
                    sanitized[key] = value

        return sanitized
```

### 4.4 Data Retention Policies

```python
# /services/api/src/apex/api/data_retention.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class RetentionCategory(str, Enum):
    """Data retention categories."""
    ENGINEERING_CALCULATIONS = "engineering"  # 7+ years (liability)
    PE_STAMPS = "pe_stamps"                    # 10+ years (legal)
    AUDIT_LOGS = "audit"                       # 7 years (compliance)
    USER_DATA = "user"                         # Account lifetime + 90 days
    SESSION_DATA = "session"                   # 30 days
    TEMPORARY = "temporary"                    # 24 hours


class RetentionPolicy(BaseModel):
    """Data retention configuration."""

    # Retention periods in days
    retention_periods: dict[str, int] = {
        RetentionCategory.ENGINEERING_CALCULATIONS: 2555,  # 7 years
        RetentionCategory.PE_STAMPS: 3650,                 # 10 years
        RetentionCategory.AUDIT_LOGS: 2555,                # 7 years
        RetentionCategory.USER_DATA: 90,                   # 90 days after deletion
        RetentionCategory.SESSION_DATA: 30,                # 30 days
        RetentionCategory.TEMPORARY: 1,                    # 1 day
    }

    # Legal hold (prevent deletion)
    legal_hold_enabled: bool = False

    def get_retention_date(self, category: RetentionCategory) -> datetime:
        """Get the date until which data should be retained."""
        days = self.retention_periods.get(category, 365)
        return datetime.now(timezone.utc) + timedelta(days=days)

    def should_delete(self, category: RetentionCategory, created_at: datetime) -> bool:
        """Check if data should be deleted based on retention policy."""
        if self.legal_hold_enabled:
            return False

        days = self.retention_periods.get(category, 365)
        retention_date = created_at + timedelta(days=days)
        return datetime.now(timezone.utc) > retention_date


# Automated retention job
async def run_retention_cleanup(db, storage):
    """Periodic job to clean up expired data."""
    policy = RetentionPolicy()

    # Clean session data
    await db.execute("""
        DELETE FROM sessions
        WHERE created_at < NOW() - INTERVAL '%s days'
    """ % policy.retention_periods[RetentionCategory.SESSION_DATA])

    # Clean temporary files
    await db.execute("""
        DELETE FROM file_uploads
        WHERE category = 'temporary'
        AND created_at < NOW() - INTERVAL '%s days'
    """ % policy.retention_periods[RetentionCategory.TEMPORARY])

    # Note: Engineering calculations and PE stamps are NOT auto-deleted
    # They require explicit legal/compliance approval for deletion
```

### 4.5 Right to Deletion (GDPR)

```python
# /services/api/src/apex/api/gdpr.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import log_audit

logger = structlog.get_logger(__name__)


class DeletionRequest(BaseModel):
    """GDPR Article 17 deletion request."""

    user_id: str
    requested_at: datetime
    reason: str
    status: str = "pending"  # pending, processing, completed, rejected
    processed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class GDPRHandler:
    """Handle GDPR data subject requests."""

    @staticmethod
    async def request_deletion(
        db: AsyncSession,
        user_id: str,
        reason: str,
    ) -> DeletionRequest:
        """Create deletion request (Right to Erasure)."""
        request = DeletionRequest(
            user_id=user_id,
            requested_at=datetime.now(timezone.utc),
            reason=reason,
        )

        # Log the request
        await log_audit(
            db=db,
            action="gdpr.deletion_requested",
            resource_type="user",
            resource_id=user_id,
            user_id=user_id,
            account_id="system",
        )

        logger.info("gdpr.deletion_requested", user_id=user_id)
        return request

    @staticmethod
    async def process_deletion(
        db: AsyncSession,
        request: DeletionRequest,
    ) -> DeletionRequest:
        """Process deletion request with legal hold checks."""

        # Check for legal holds
        legal_holds = await db.execute("""
            SELECT 1 FROM legal_holds
            WHERE user_id = :user_id AND active = true
        """, {"user_id": request.user_id})

        if legal_holds.fetchone():
            request.status = "rejected"
            request.rejection_reason = "Legal hold active - deletion blocked"
            return request

        # Check for active PE stamps (cannot delete while stamps are valid)
        pe_stamps = await db.execute("""
            SELECT 1 FROM pe_stamps
            WHERE pe_user_id = :user_id AND is_revoked = false
        """, {"user_id": request.user_id})

        if pe_stamps.fetchone():
            request.status = "rejected"
            request.rejection_reason = "Active PE stamps exist - revoke stamps first"
            return request

        # Proceed with deletion
        request.status = "processing"

        # 1. Anonymize user data (don't delete, anonymize for audit trail)
        await db.execute("""
            UPDATE users SET
                email = CONCAT('deleted_', id, '@anonymized.local'),
                first_name = 'Deleted',
                last_name = 'User',
                phone = NULL,
                deleted_at = NOW()
            WHERE id = :user_id
        """, {"user_id": request.user_id})

        # 2. Delete personal files
        await db.execute("""
            DELETE FROM file_uploads
            WHERE uploaded_by = :user_id
            AND project_id IS NULL
        """, {"user_id": request.user_id})

        # 3. Anonymize audit logs (keep logs but remove PII)
        await db.execute("""
            UPDATE audit_logs SET
                ip_address = '0.0.0.0',
                user_agent = 'anonymized'
            WHERE user_id = :user_id
        """, {"user_id": request.user_id})

        # 4. Revoke all sessions
        await db.execute("""
            DELETE FROM sessions WHERE user_id = :user_id
        """, {"user_id": request.user_id})

        request.status = "completed"
        request.processed_at = datetime.now(timezone.utc)

        await log_audit(
            db=db,
            action="gdpr.deletion_completed",
            resource_type="user",
            resource_id=request.user_id,
            user_id="system",
            account_id="system",
        )

        logger.info("gdpr.deletion_completed", user_id=request.user_id)
        return request

    @staticmethod
    async def export_user_data(
        db: AsyncSession,
        user_id: str,
    ) -> dict:
        """Export all user data (Right to Access/Portability)."""
        # Collect all user data
        user = await db.execute("""
            SELECT * FROM users WHERE id = :user_id
        """, {"user_id": user_id})

        projects = await db.execute("""
            SELECT * FROM projects WHERE created_by = :user_id
        """, {"user_id": user_id})

        calculations = await db.execute("""
            SELECT * FROM calculations WHERE created_by = :user_id
        """, {"user_id": user_id})

        audit_logs = await db.execute("""
            SELECT * FROM audit_logs WHERE user_id = :user_id
        """, {"user_id": user_id})

        return {
            "user": dict(user.fetchone() or {}),
            "projects": [dict(r) for r in projects.fetchall()],
            "calculations": [dict(r) for r in calculations.fetchall()],
            "audit_logs": [dict(r) for r in audit_logs.fetchall()],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
```

---

## 5. Audit and Compliance

### 5.1 Current Implementation (Existing)

The system has audit infrastructure in:
- `/home/user/SignX/services/api/alembic/versions/009_add_audit_rbac_compliance_tables.py`
- `/home/user/SignX/services/api/src/apex/api/routes/audit.py`

### 5.2 Comprehensive Audit Log Requirements

```python
# /services/api/src/apex/api/audit_events.py

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel


class AuditEventCategory(str, Enum):
    """Audit event categories."""
    AUTHENTICATION = "auth"
    AUTHORIZATION = "authz"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    ADMINISTRATION = "admin"
    PE_STAMP = "pe_stamp"
    COMPLIANCE = "compliance"
    SECURITY = "security"


class AuditEvent(BaseModel):
    """Comprehensive audit event model."""

    # Event identification
    event_id: str
    timestamp: datetime
    category: AuditEventCategory
    action: str

    # Actor information
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    # Resource information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    # Change tracking
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None

    # Context
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    confidence: Optional[float] = None

    # Outcome
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# Events that MUST be logged (compliance requirement)
MANDATORY_AUDIT_EVENTS = {
    # Authentication
    "auth.login.success",
    "auth.login.failure",
    "auth.logout",
    "auth.mfa.enabled",
    "auth.mfa.disabled",
    "auth.mfa.verified",
    "auth.mfa.failed",
    "auth.password.changed",
    "auth.password.reset_requested",
    "auth.password.reset_completed",
    "auth.session.created",
    "auth.session.revoked",

    # Authorization
    "authz.permission.denied",
    "authz.role.assigned",
    "authz.role.revoked",

    # PE Stamps (critical for engineering liability)
    "pe_stamp.created",
    "pe_stamp.revoked",
    "pe_stamp.viewed",
    "pe_stamp.downloaded",

    # Calculations
    "calculation.created",
    "calculation.approved",
    "calculation.rejected",
    "calculation.deleted",

    # Projects
    "project.created",
    "project.submitted",
    "project.approved",
    "project.deleted",

    # Files
    "file.uploaded",
    "file.downloaded",
    "file.deleted",

    # Administration
    "admin.user.created",
    "admin.user.deleted",
    "admin.user.role_changed",
    "admin.settings.changed",

    # Security
    "security.suspicious_activity",
    "security.account_locked",
    "security.token_reuse_detected",
}
```

### 5.3 PE Stamp Tracking

```python
# /services/api/src/apex/api/pe_stamp_audit.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import log_audit

logger = structlog.get_logger(__name__)


class PEStampRecord(BaseModel):
    """PE stamp audit record with full traceability."""

    stamp_id: str
    project_id: str
    calculation_id: str

    # PE Engineer information
    pe_user_id: str
    pe_name: str
    pe_license_number: str
    pe_license_state: str
    pe_license_expiry: datetime

    # Stamp details
    stamp_type: str  # "preliminary", "final", "revision"
    methodology: str
    code_references: list[str]

    # Calculation snapshot at time of stamp
    calculation_sha256: str
    calculation_inputs: dict
    calculation_outputs: dict

    # Timestamps
    stamped_at: datetime
    created_at: datetime

    # Revocation (if applicable)
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None


async def create_pe_stamp(
    db: AsyncSession,
    project_id: str,
    calculation_id: str,
    pe_user_id: str,
    methodology: str,
    code_references: list[str],
) -> PEStampRecord:
    """Create PE stamp with full audit trail."""
    import uuid
    import hashlib
    import json

    # Get PE user details
    pe_user = await db.execute("""
        SELECT u.*, pe.license_number, pe.license_state, pe.license_expiry
        FROM users u
        JOIN pe_licenses pe ON u.id = pe.user_id
        WHERE u.id = :user_id AND pe.is_active = true
    """, {"user_id": pe_user_id})
    pe_data = pe_user.fetchone()

    if not pe_data:
        raise ValueError("User is not a licensed PE or license is inactive")

    # Get calculation data
    calc = await db.execute("""
        SELECT * FROM calculations WHERE id = :calc_id
    """, {"calc_id": calculation_id})
    calc_data = dict(calc.fetchone())

    # Create calculation hash for immutability
    calc_hash = hashlib.sha256(
        json.dumps(calc_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    stamp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    stamp = PEStampRecord(
        stamp_id=stamp_id,
        project_id=project_id,
        calculation_id=calculation_id,
        pe_user_id=pe_user_id,
        pe_name=f"{pe_data['first_name']} {pe_data['last_name']}",
        pe_license_number=pe_data['license_number'],
        pe_license_state=pe_data['license_state'],
        pe_license_expiry=pe_data['license_expiry'],
        stamp_type="final",
        methodology=methodology,
        code_references=code_references,
        calculation_sha256=calc_hash,
        calculation_inputs=calc_data.get('inputs', {}),
        calculation_outputs=calc_data.get('outputs', {}),
        stamped_at=now,
        created_at=now,
    )

    # Insert stamp record
    await db.execute("""
        INSERT INTO pe_stamps (
            stamp_id, project_id, calculation_id, pe_user_id,
            pe_license_number, pe_state, stamp_type, methodology,
            code_references, stamped_at
        ) VALUES (
            :stamp_id, :project_id, :calculation_id, :pe_user_id,
            :pe_license_number, :pe_state, :stamp_type, :methodology,
            :code_references, :stamped_at
        )
    """, stamp.model_dump())

    # Create immutable audit record
    await log_audit(
        db=db,
        action="pe_stamp.created",
        resource_type="pe_stamp",
        resource_id=stamp_id,
        user_id=pe_user_id,
        account_id=pe_data['account_id'],
        after_state={
            "stamp_id": stamp_id,
            "calculation_sha256": calc_hash,
            "pe_license_number": stamp.pe_license_number,
            "pe_license_state": stamp.pe_license_state,
        }
    )

    logger.info(
        "pe_stamp.created",
        stamp_id=stamp_id,
        pe_user_id=pe_user_id,
        calculation_sha256=calc_hash,
    )

    return stamp


async def revoke_pe_stamp(
    db: AsyncSession,
    stamp_id: str,
    revoked_by: str,
    reason: str,
) -> PEStampRecord:
    """Revoke PE stamp with audit trail."""
    now = datetime.now(timezone.utc)

    # Get current stamp
    stamp = await db.execute("""
        SELECT * FROM pe_stamps WHERE stamp_id = :stamp_id
    """, {"stamp_id": stamp_id})
    stamp_data = stamp.fetchone()

    if not stamp_data:
        raise ValueError("PE stamp not found")

    if stamp_data['is_revoked']:
        raise ValueError("PE stamp already revoked")

    # Update stamp
    await db.execute("""
        UPDATE pe_stamps SET
            is_revoked = true,
            revoked_at = :revoked_at,
            revoked_reason = :reason
        WHERE stamp_id = :stamp_id
    """, {"stamp_id": stamp_id, "revoked_at": now, "reason": reason})

    # Create audit record
    await log_audit(
        db=db,
        action="pe_stamp.revoked",
        resource_type="pe_stamp",
        resource_id=stamp_id,
        user_id=revoked_by,
        account_id=stamp_data['account_id'],
        before_state={"is_revoked": False},
        after_state={
            "is_revoked": True,
            "revoked_at": now.isoformat(),
            "revocation_reason": reason,
        }
    )

    logger.warning(
        "pe_stamp.revoked",
        stamp_id=stamp_id,
        revoked_by=revoked_by,
        reason=reason,
    )

    return PEStampRecord(**{**dict(stamp_data), "is_revoked": True, "revoked_at": now, "revocation_reason": reason})
```

### 5.4 Tamper-Proof Log Storage

```python
# /services/api/src/apex/api/tamper_proof_logs.py

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ChainedAuditLog(BaseModel):
    """Audit log with blockchain-style chaining for tamper detection."""

    log_id: int
    timestamp: datetime
    action: str
    data: dict

    # Chaining fields
    previous_hash: str
    current_hash: str

    @staticmethod
    def compute_hash(
        log_id: int,
        timestamp: datetime,
        action: str,
        data: dict,
        previous_hash: str,
    ) -> str:
        """Compute SHA256 hash of log entry."""
        content = json.dumps({
            "log_id": log_id,
            "timestamp": timestamp.isoformat(),
            "action": action,
            "data": data,
            "previous_hash": previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


async def create_chained_audit_log(
    db,
    action: str,
    data: dict,
    user_id: str,
    account_id: str,
) -> ChainedAuditLog:
    """Create audit log with hash chain for tamper detection."""

    # Get previous log hash
    result = await db.execute("""
        SELECT log_id, current_hash FROM audit_logs
        ORDER BY log_id DESC LIMIT 1
    """)
    prev = result.fetchone()

    previous_hash = prev['current_hash'] if prev else "genesis"
    new_log_id = (prev['log_id'] + 1) if prev else 1
    now = datetime.now(timezone.utc)

    # Compute hash
    current_hash = ChainedAuditLog.compute_hash(
        log_id=new_log_id,
        timestamp=now,
        action=action,
        data=data,
        previous_hash=previous_hash,
    )

    # Insert with hash
    await db.execute("""
        INSERT INTO audit_logs (
            log_id, user_id, account_id, action,
            timestamp, before_state, after_state,
            previous_hash, current_hash
        ) VALUES (
            :log_id, :user_id, :account_id, :action,
            :timestamp, :before_state, :after_state,
            :previous_hash, :current_hash
        )
    """, {
        "log_id": new_log_id,
        "user_id": user_id,
        "account_id": account_id,
        "action": action,
        "timestamp": now,
        "before_state": json.dumps(data.get("before", {})),
        "after_state": json.dumps(data.get("after", {})),
        "previous_hash": previous_hash,
        "current_hash": current_hash,
    })

    return ChainedAuditLog(
        log_id=new_log_id,
        timestamp=now,
        action=action,
        data=data,
        previous_hash=previous_hash,
        current_hash=current_hash,
    )


async def verify_audit_chain(db, start_id: int = 1, end_id: Optional[int] = None) -> tuple[bool, list[int]]:
    """Verify audit log chain integrity."""

    query = "SELECT * FROM audit_logs WHERE log_id >= :start_id"
    params = {"start_id": start_id}

    if end_id:
        query += " AND log_id <= :end_id"
        params["end_id"] = end_id

    query += " ORDER BY log_id ASC"

    result = await db.execute(query, params)
    logs = result.fetchall()

    tampered_ids = []
    previous_hash = "genesis"

    for log in logs:
        # Recompute hash
        expected_hash = ChainedAuditLog.compute_hash(
            log_id=log['log_id'],
            timestamp=log['timestamp'],
            action=log['action'],
            data={
                "before": json.loads(log['before_state'] or "{}"),
                "after": json.loads(log['after_state'] or "{}"),
            },
            previous_hash=previous_hash,
        )

        # Check chain link
        if log['previous_hash'] != previous_hash:
            tampered_ids.append(log['log_id'])
            logger.error("audit_chain.broken_link", log_id=log['log_id'])

        # Check hash integrity
        if log['current_hash'] != expected_hash:
            tampered_ids.append(log['log_id'])
            logger.error("audit_chain.hash_mismatch", log_id=log['log_id'])

        previous_hash = log['current_hash']

    is_valid = len(tampered_ids) == 0
    return is_valid, tampered_ids
```

---

## 6. Vulnerability Management

### 6.1 Current Implementation (Existing)

The system has CI security scanning in:
- `/home/user/SignX/.github/workflows/security-scan.yml`
- Semgrep SAST
- Gitleaks secret scanning
- Python Safety dependency check

### 6.2 Enhanced Security Scanning Workflow

```yaml
# /.github/workflows/security-scan-enhanced.yml

name: Security Scanning (Enhanced)

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC

jobs:
  # Static Application Security Testing
  semgrep:
    name: Semgrep SAST
    runs-on: ubuntu-latest
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v4

      - name: Run Semgrep
        run: |
          semgrep ci \
            --config=auto \
            --config=p/security-audit \
            --config=p/owasp-top-ten \
            --config=p/python \
            --config=p/javascript \
            --sarif --output=semgrep.sarif
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: semgrep.sarif
        if: always()

  # Secret Detection
  secrets:
    name: Gitleaks Secret Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_CONFIG: .gitleaks.toml

  # Dependency Vulnerability Scanning
  dependencies:
    name: Dependency Scanning
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install and run pip-audit
        run: |
          pip install pip-audit
          pip-audit --format=json --output=pip-audit.json || true

      - name: Install and run Safety
        run: |
          pip install safety
          safety check --json --output=safety.json || true

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: dependency-scan-results
          path: |
            pip-audit.json
            safety.json

  # Container Scanning
  container-scan:
    name: Container Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build API image
        run: docker build -t signx-api:scan ./services/api

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'signx-api:scan'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  # Infrastructure as Code Scanning
  iac-scan:
    name: IaC Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Checkov
        uses: bridgecrewio/checkov-action@master
        with:
          directory: .
          framework: dockerfile,kubernetes,helm
          output_format: sarif
          output_file_path: checkov.sarif

      - name: Upload Checkov results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: checkov.sarif
        if: always()

  # Dynamic Application Security Testing (staging only)
  dast:
    name: DAST Scan
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: ZAP Scan
        uses: zaproxy/action-baseline@v0.11.0
        with:
          target: 'https://staging.signxstudio.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'
```

### 6.3 Container Security Hardening

```dockerfile
# /services/api/Dockerfile.hardened

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim AS builder

# Prevent Python from writing bytecode and buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /build/
RUN pip install --upgrade pip && \
    pip install uv && \
    uv pip compile --generate-hashes pyproject.toml -o requirements.txt && \
    uv pip install --target=/install -r requirements.txt

# ============================================================================
# Stage 2: Production (Hardened)
# ============================================================================
FROM python:3.11-slim

LABEL maintainer="SignX Studio <security@signxstudio.com>"
LABEL org.opencontainers.image.source="https://github.com/signxstudio/apex"
LABEL org.opencontainers.image.description="SignX API - Hardened Production Image"

# Security environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app/src \
    # Disable pip to prevent runtime package installation
    PIP_NO_INPUT=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app /tmp/apex && \
    chown -R appuser:appuser /app /tmp/apex

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl ca-certificates libpq5 && \
    # Remove unnecessary packages
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    # Remove shell access
    rm -f /bin/sh /bin/bash 2>/dev/null || true

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# Copy application code
COPY --chown=appuser:appuser src /app/src
COPY --chown=appuser:appuser alembic /app/alembic
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser config /app/config

# Remove write permissions where not needed
RUN chmod -R 555 /app/src && \
    chmod 555 /app/alembic.ini

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Run as non-root
USER appuser

# Expose only necessary port
EXPOSE 8000

# Use exec form to prevent shell injection
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["apex.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

### 6.4 Penetration Testing Schedule

```yaml
# /docs/security/pentest-schedule.yaml

penetration_testing:
  schedule:
    # External pentest (annual)
    external:
      frequency: annual
      scope:
        - Public API endpoints
        - Web application
        - Authentication flows
        - OAuth integrations
      provider: "[Select from approved vendors]"
      last_completed: null
      next_scheduled: null

    # Internal pentest (semi-annual)
    internal:
      frequency: semi-annual
      scope:
        - Internal APIs
        - Database security
        - Container security
        - Network segmentation
      team: Security team or approved vendor
      last_completed: null
      next_scheduled: null

    # Continuous automated testing
    automated:
      frequency: weekly
      tools:
        - OWASP ZAP (DAST)
        - Semgrep (SAST)
        - Trivy (container scanning)
        - Dependency scanning
      integration: GitHub Actions CI/CD

  findings_process:
    critical:
      sla_hours: 24
      escalation: CTO, Security Lead
      requires_patch: true

    high:
      sla_days: 7
      escalation: Security Lead, Tech Lead
      requires_patch: true

    medium:
      sla_days: 30
      escalation: Tech Lead
      requires_patch: recommended

    low:
      sla_days: 90
      escalation: Development Team
      requires_patch: optional

  bug_bounty:
    enabled: false  # Consider enabling after maturity
    platform: null  # HackerOne, Bugcrowd, etc.
    scope: null
    rewards:
      critical: "$5,000 - $10,000"
      high: "$1,000 - $5,000"
      medium: "$500 - $1,000"
      low: "$100 - $500"
```

---

## 7. Incident Response

### 7.1 Detection Mechanisms

```python
# /services/api/src/apex/api/security_monitoring.py

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from pydantic import BaseModel
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class SecurityAlert(BaseModel):
    """Security alert model."""

    alert_id: str
    alert_type: str
    severity: str  # critical, high, medium, low
    description: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    metadata: dict = {}


class SecurityMonitor:
    """Real-time security monitoring and alerting."""

    # Alert thresholds
    FAILED_LOGIN_THRESHOLD = 5
    FAILED_LOGIN_WINDOW_MINUTES = 15

    API_ABUSE_THRESHOLD = 1000  # requests
    API_ABUSE_WINDOW_MINUTES = 5

    SUSPICIOUS_IP_THRESHOLD = 10  # failed logins from same IP

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[Redis] = None

    async def get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url)
        return self._redis

    async def track_failed_login(self, user_email: str, ip_address: str) -> Optional[SecurityAlert]:
        """Track failed login attempts and alert on threshold."""
        redis = await self.get_redis()
        now = datetime.now(timezone.utc)

        # Track by user
        user_key = f"security:failed_login:user:{user_email}"
        await redis.zadd(user_key, {str(now.timestamp()): now.timestamp()})
        await redis.expire(user_key, self.FAILED_LOGIN_WINDOW_MINUTES * 60)

        # Track by IP
        ip_key = f"security:failed_login:ip:{ip_address}"
        await redis.zadd(ip_key, {str(now.timestamp()): now.timestamp()})
        await redis.expire(ip_key, self.FAILED_LOGIN_WINDOW_MINUTES * 60)

        # Check user threshold
        window_start = now - timedelta(minutes=self.FAILED_LOGIN_WINDOW_MINUTES)
        user_count = await redis.zcount(user_key, window_start.timestamp(), now.timestamp())

        if user_count >= self.FAILED_LOGIN_THRESHOLD:
            return await self._create_alert(
                alert_type="brute_force_attempt",
                severity="high",
                description=f"Multiple failed login attempts for {user_email}",
                user_id=user_email,
                ip_address=ip_address,
                metadata={"attempt_count": user_count}
            )

        # Check IP threshold
        ip_count = await redis.zcount(ip_key, window_start.timestamp(), now.timestamp())

        if ip_count >= self.SUSPICIOUS_IP_THRESHOLD:
            return await self._create_alert(
                alert_type="suspicious_ip",
                severity="high",
                description=f"Multiple failed logins from IP {ip_address}",
                ip_address=ip_address,
                metadata={"attempt_count": ip_count}
            )

        return None

    async def track_api_usage(self, user_id: str, endpoint: str) -> Optional[SecurityAlert]:
        """Track API usage and alert on abuse."""
        redis = await self.get_redis()
        now = datetime.now(timezone.utc)

        key = f"security:api_usage:{user_id}"
        await redis.incr(key)
        await redis.expire(key, self.API_ABUSE_WINDOW_MINUTES * 60)

        count = int(await redis.get(key) or 0)

        if count >= self.API_ABUSE_THRESHOLD:
            return await self._create_alert(
                alert_type="api_abuse",
                severity="medium",
                description=f"High API usage from user {user_id}",
                user_id=user_id,
                metadata={"request_count": count, "endpoint": endpoint}
            )

        return None

    async def detect_token_reuse(self, token_hash: str, user_id: str) -> Optional[SecurityAlert]:
        """Detect refresh token reuse (potential theft)."""
        return await self._create_alert(
            alert_type="token_reuse",
            severity="critical",
            description=f"Refresh token reuse detected for user {user_id}",
            user_id=user_id,
            metadata={"token_hash": token_hash[:16]}
        )

    async def detect_privilege_escalation(
        self,
        user_id: str,
        attempted_action: str,
        user_roles: list[str]
    ) -> Optional[SecurityAlert]:
        """Detect privilege escalation attempts."""
        return await self._create_alert(
            alert_type="privilege_escalation",
            severity="high",
            description=f"User {user_id} attempted unauthorized action: {attempted_action}",
            user_id=user_id,
            metadata={"attempted_action": attempted_action, "user_roles": user_roles}
        )

    async def _create_alert(
        self,
        alert_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: dict = {}
    ) -> SecurityAlert:
        """Create and dispatch security alert."""
        import uuid

        alert = SecurityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=alert_type,
            severity=severity,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

        # Log alert
        logger.warning(
            "security.alert",
            alert_type=alert_type,
            severity=severity,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
        )

        # Send to alerting system (Slack, PagerDuty, etc.)
        await self._dispatch_alert(alert)

        return alert

    async def _dispatch_alert(self, alert: SecurityAlert) -> None:
        """Dispatch alert to notification channels."""
        # Integration with Slack, PagerDuty, email, etc.
        # This would be implemented based on your alerting infrastructure
        pass
```

### 7.2 Incident Response Procedures

```yaml
# /docs/security/incident-response.yaml

incident_response_plan:
  version: "1.0"
  last_updated: "2025-01-01"

  severity_levels:
    critical:
      description: "Active data breach, system compromise, or PE stamp forgery"
      response_time: "15 minutes"
      escalation:
        - Security Lead (immediate)
        - CTO (within 30 minutes)
        - Legal (within 1 hour)
        - CEO (within 2 hours)

    high:
      description: "Potential breach, unauthorized access, or service outage"
      response_time: "1 hour"
      escalation:
        - Security Lead (immediate)
        - CTO (within 2 hours)

    medium:
      description: "Suspicious activity, failed attacks, or policy violations"
      response_time: "4 hours"
      escalation:
        - Security Lead (within 4 hours)

    low:
      description: "Anomalies, scanning attempts, or minor policy deviations"
      response_time: "24 hours"
      escalation:
        - Security Team (next business day)

  response_phases:
    1_detection:
      actions:
        - Verify alert authenticity
        - Gather initial evidence
        - Classify severity
        - Activate incident response team
      artifacts:
        - Incident ticket created
        - Initial timeline documented
        - Evidence preserved

    2_containment:
      actions:
        - Isolate affected systems
        - Revoke compromised credentials
        - Block malicious IPs
        - Preserve forensic evidence
      considerations:
        - "DO NOT destroy evidence"
        - "Document all containment actions"
        - "Consider business impact of isolation"

    3_eradication:
      actions:
        - Identify root cause
        - Remove malicious artifacts
        - Patch vulnerabilities
        - Verify clean state

    4_recovery:
      actions:
        - Restore from clean backups
        - Reset affected credentials
        - Monitor for re-infection
        - Gradual service restoration

    5_post_incident:
      actions:
        - Conduct post-mortem
        - Update documentation
        - Implement preventive measures
        - Notify stakeholders
      timeline: "Within 7 days of incident closure"

  communication_plan:
    internal:
      channels:
        - Dedicated Slack channel (#incident-response)
        - Email to security@signxstudio.com
        - Phone tree for critical incidents

    external:
      data_breach_notification:
        gdpr_timeline: "72 hours to supervisory authority"
        ccpa_timeline: "Expeditiously"
        customer_notification: "Without unreasonable delay"

      templates:
        - Initial breach notification
        - Status update
        - Resolution notification

  contacts:
    security_lead:
      name: "[TBD]"
      phone: "[TBD]"
      email: "security@signxstudio.com"

    legal_counsel:
      name: "[TBD]"
      phone: "[TBD]"

    law_enforcement:
      fbi_cyber: "1-800-CALL-FBI"
      local_police: "[TBD]"
```

---

## 8. OWASP Top 10 Mitigations

### 8.1 A01:2021 - Broken Access Control

**Controls Implemented**:
- RBAC system with permission-based access (`/services/api/src/apex/api/rbac.py`)
- Organization isolation (`account_id` filtering)
- Resource-level access control
- JWT token validation

**Additional Controls Needed**:

```python
# Enforce deny-by-default
async def check_access(user: TokenData, resource: str, action: str) -> bool:
    """Deny by default, require explicit permission."""
    if not user:
        return False

    # Admin bypass
    if "admin" in user.roles:
        return True

    # Check explicit permission
    permission = f"{resource}.{action}"
    return await check_permission(db, user, permission)


# Prevent IDOR (Insecure Direct Object Reference)
async def get_resource_with_access_check(
    db: AsyncSession,
    user: TokenData,
    resource_type: str,
    resource_id: str,
) -> Any:
    """Always verify ownership/access before returning resources."""
    resource = await db.get(resource_type, resource_id)

    if not resource:
        raise HTTPException(status_code=404, detail="Not found")

    # Verify access
    if resource.account_id != user.account_id:
        if "admin" not in user.roles:
            logger.warning("idor_attempt", user_id=user.user_id, resource_id=resource_id)
            raise HTTPException(status_code=404, detail="Not found")  # Don't reveal existence

    return resource
```

### 8.2 A02:2021 - Cryptographic Failures

**Controls Implemented**:
- bcrypt password hashing (12 rounds)
- JWT with HS256 signing
- TLS for transit encryption

**Additional Controls Needed**:

```python
# Ensure strong cryptographic algorithms
ALLOWED_JWT_ALGORITHMS = ["HS256", "RS256", "ES256"]  # No "none"
MINIMUM_BCRYPT_ROUNDS = 12

# Verify cryptographic settings at startup
def verify_crypto_settings():
    """Startup check for cryptographic configuration."""
    import bcrypt

    # Verify bcrypt rounds
    assert BCRYPT_ROUNDS >= MINIMUM_BCRYPT_ROUNDS, f"bcrypt rounds must be >= {MINIMUM_BCRYPT_ROUNDS}"

    # Verify JWT algorithm
    assert JWT_ALGORITHM in ALLOWED_JWT_ALGORITHMS, f"JWT algorithm must be one of {ALLOWED_JWT_ALGORITHMS}"

    # Verify key length
    if JWT_SECRET_KEY:
        assert len(JWT_SECRET_KEY) >= 32, "JWT secret key must be at least 32 characters"
```

### 8.3 A03:2021 - Injection

**Controls Implemented**:
- SQLAlchemy ORM with parameterized queries
- Pydantic input validation

**Additional Controls Needed**:

```python
# SQL Injection Prevention
# NEVER use string formatting for queries
# BAD: f"SELECT * FROM users WHERE id = '{user_id}'"
# GOOD:
await db.execute(select(User).where(User.id == user_id))

# Command Injection Prevention (if shell commands needed)
import shlex
import subprocess

def safe_command(cmd: list[str]) -> subprocess.CompletedProcess:
    """Execute command safely without shell."""
    # Validate command is in allowlist
    ALLOWED_COMMANDS = ["gs", "pdftk", "convert"]  # Ghostscript, PDFtk, ImageMagick

    if cmd[0] not in ALLOWED_COMMANDS:
        raise ValueError(f"Command not allowed: {cmd[0]}")

    # Execute without shell
    return subprocess.run(cmd, capture_output=True, shell=False, timeout=30)

# NoSQL Injection Prevention (if using MongoDB/etc.)
# Always validate and sanitize operators
def sanitize_mongo_query(query: dict) -> dict:
    """Remove MongoDB operators from user input."""
    dangerous_operators = ["$where", "$regex", "$expr", "$function"]

    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items() if k not in dangerous_operators}
        elif isinstance(obj, list):
            return [clean(item) for item in obj]
        return obj

    return clean(query)
```

### 8.4 A04:2021 - Insecure Design

**Controls Implemented**:
- Defense in depth architecture
- Threat modeling in design phase

**Additional Controls Needed**:

```python
# Business logic security checks
class CalculationSecurityChecks:
    """Security checks for engineering calculations."""

    @staticmethod
    async def validate_pe_stamp_eligibility(
        db: AsyncSession,
        user: TokenData,
        calculation_id: str,
    ) -> tuple[bool, list[str]]:
        """Verify all requirements before allowing PE stamp."""
        errors = []

        # 1. User must be PE
        if "pe" not in user.roles and "pe_engineer" not in user.roles:
            errors.append("User is not a licensed PE")

        # 2. PE license must be valid
        license = await db.execute("""
            SELECT * FROM pe_licenses
            WHERE user_id = :user_id AND is_active = true
        """, {"user_id": user.user_id})

        if not license.fetchone():
            errors.append("PE license not found or inactive")

        # 3. Calculation must be complete
        calc = await db.execute("""
            SELECT status FROM calculations WHERE id = :calc_id
        """, {"calc_id": calculation_id})
        calc_data = calc.fetchone()

        if not calc_data or calc_data['status'] != 'complete':
            errors.append("Calculation is not complete")

        # 4. MFA must be verified
        if not user.mfa_verified:
            errors.append("MFA verification required for PE stamp")

        # 5. Check for conflicting stamps
        existing = await db.execute("""
            SELECT 1 FROM pe_stamps
            WHERE calculation_id = :calc_id AND is_revoked = false
        """, {"calc_id": calculation_id})

        if existing.fetchone():
            errors.append("Calculation already has active PE stamp")

        return len(errors) == 0, errors
```

### 8.5 A05:2021 - Security Misconfiguration

**Controls Implemented**:
- Docker security options (`no-new-privileges`, `read_only`)
- Non-root container user
- Environment-based configuration

**Additional Controls Needed**:

```python
# Startup security checks
def validate_prod_requirements():
    """Validate security requirements for production."""
    from .deps import settings

    if settings.ENV == "production":
        # JWT secret must not be default
        if settings.JWT_SECRET_KEY in (None, "dev-secret-key-change-in-production"):
            raise ValueError("JWT_SECRET_KEY must be set in production")

        # Database must use SSL
        if "sslmode=require" not in settings.DATABASE_URL:
            logger.warning("Database connection should use SSL in production")

        # CORS must be restricted
        if "*" in settings.CORS_ALLOW_ORIGINS:
            raise ValueError("CORS cannot allow all origins in production")

        # Debug mode must be off
        if os.getenv("DEBUG", "").lower() == "true":
            raise ValueError("DEBUG mode must be disabled in production")

# Security headers middleware
from fastapi import Response

async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # HSTS (only in production with HTTPS)
    if settings.ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response
```

### 8.6 A06:2021 - Vulnerable and Outdated Components

**Controls Implemented**:
- `pip-audit` and `safety` in CI
- Dependabot (if enabled)

**Additional Controls Needed**:

```yaml
# /.github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/services/api"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    groups:
      security:
        applies-to: security-updates
    reviewers:
      - "security-team"

  - package-ecosystem: "npm"
    directory: "/apex/apps/ui-web"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "docker"
    directory: "/services/api"
    schedule:
      interval: "weekly"
```

### 8.7 A07:2021 - Identification and Authentication Failures

**Controls Implemented**:
- Account lockout after failed attempts
- Password strength validation
- Duo 2FA integration

**Additional Controls Needed**:

```python
# Enhanced session security
class SessionSecurityConfig:
    # Bind session to user agent and IP (optional, can break mobile)
    BIND_TO_USER_AGENT = True
    BIND_TO_IP = False  # Can cause issues with mobile/VPN

    # Session fixation prevention
    REGENERATE_SESSION_ON_LOGIN = True
    REGENERATE_SESSION_ON_PRIVILEGE_CHANGE = True

# Credential stuffing protection
async def check_credential_stuffing(ip_address: str, attempts: int) -> bool:
    """Detect credential stuffing attacks."""
    # Track login attempts across different accounts from same IP
    redis = await get_redis()

    key = f"login_attempts:ip:{ip_address}"
    current = int(await redis.get(key) or 0)

    if current > 50:  # 50 different accounts from same IP
        return True  # Likely credential stuffing

    await redis.incr(key)
    await redis.expire(key, 3600)  # 1 hour window

    return False
```

### 8.8 A08:2021 - Software and Data Integrity Failures

**Controls Implemented**:
- Calculation SHA256 hashing in envelopes
- Chained audit logs

**Additional Controls Needed**:

```python
# Verify CI/CD pipeline integrity
def verify_deployment_signature(deployment_manifest: dict, signature: str) -> bool:
    """Verify deployment was signed by authorized key."""
    import hmac

    DEPLOYMENT_SIGNING_KEY = os.getenv("DEPLOYMENT_SIGNING_KEY")
    if not DEPLOYMENT_SIGNING_KEY:
        raise ValueError("Deployment signing key not configured")

    expected_sig = hmac.new(
        DEPLOYMENT_SIGNING_KEY.encode(),
        json.dumps(deployment_manifest, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_sig)

# Subresource Integrity for frontend
# In HTML templates:
# <script src="https://cdn.example.com/lib.js"
#         integrity="sha384-..."
#         crossorigin="anonymous"></script>
```

### 8.9 A09:2021 - Security Logging and Monitoring Failures

**Controls Implemented**:
- Structured logging with structlog
- Audit log infrastructure

**Additional Controls Needed**:

```python
# Ensure sensitive events are logged
SECURITY_EVENTS_TO_LOG = [
    "login_success",
    "login_failure",
    "logout",
    "password_change",
    "mfa_enable",
    "mfa_disable",
    "permission_denied",
    "session_created",
    "session_revoked",
    "pe_stamp_created",
    "pe_stamp_revoked",
    "data_export",
    "data_deletion",
]

# Log retention
LOG_RETENTION_DAYS = {
    "application": 90,
    "security": 365 * 7,  # 7 years
    "audit": 365 * 7,     # 7 years (compliance)
    "access": 90,
}

# Alerting thresholds
ALERT_THRESHOLDS = {
    "failed_logins_per_hour": 10,
    "permission_denials_per_hour": 20,
    "api_errors_per_minute": 50,
}
```

### 8.10 A10:2021 - Server-Side Request Forgery (SSRF)

**Controls Implemented**:
- Limited external API calls

**Additional Controls Needed**:

```python
# SSRF Prevention
import ipaddress
import urllib.parse

ALLOWED_EXTERNAL_HOSTS = [
    "api.duo.com",
    "*.duosecurity.com",
    "api.pwnedpasswords.com",
]

BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),      # Private
    ipaddress.ip_network("172.16.0.0/12"),   # Private
    ipaddress.ip_network("192.168.0.0/16"),  # Private
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),       # Current network
]

def validate_url_for_ssrf(url: str) -> bool:
    """Validate URL to prevent SSRF attacks."""
    parsed = urllib.parse.urlparse(url)

    # Only allow HTTPS
    if parsed.scheme != "https":
        return False

    # Check against allowlist
    hostname = parsed.hostname
    if not any(
        hostname == allowed or
        (allowed.startswith("*.") and hostname.endswith(allowed[1:]))
        for allowed in ALLOWED_EXTERNAL_HOSTS
    ):
        return False

    # Resolve and check IP
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)

        for blocked_range in BLOCKED_IP_RANGES:
            if ip_obj in blocked_range:
                return False
    except socket.gaierror:
        return False

    return True
```

---

## 9. Implementation Checklist

### Phase 1: Critical (Week 1-2)
- [ ] Enforce MFA for PE stamp operations
- [ ] Implement request signing for critical endpoints
- [ ] Add SSRF protection to external API calls
- [ ] Enable container scanning in CI
- [ ] Configure security headers middleware
- [ ] Validate production configuration at startup

### Phase 2: High Priority (Week 3-4)
- [ ] Implement token refresh rotation
- [ ] Add session management with Redis
- [ ] Set up security monitoring and alerting
- [ ] Create incident response runbooks
- [ ] Enable field-level encryption for PII
- [ ] Configure HSTS and other security headers

### Phase 3: Medium Priority (Month 2)
- [ ] Implement GDPR data export/deletion
- [ ] Set up penetration testing schedule
- [ ] Enable bug bounty program evaluation
- [ ] Add data retention automation
- [ ] Implement tamper-proof audit logs
- [ ] Create security training materials

### Phase 4: Continuous
- [ ] Weekly dependency scanning
- [ ] Monthly security review meetings
- [ ] Quarterly penetration testing
- [ ] Annual external security audit
- [ ] Continuous monitoring and alerting tuning

---

## 10. Security Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Security Lead | TBD | security@signxstudio.com | TBD |
| CTO | TBD | TBD | TBD |
| Legal Counsel | TBD | TBD | TBD |
| On-Call Engineer | TBD | oncall@signxstudio.com | TBD |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-22 | Claude Security Auditor | Initial comprehensive security architecture |

---

*This document should be reviewed and updated quarterly or after any significant security incident or architecture change.*
