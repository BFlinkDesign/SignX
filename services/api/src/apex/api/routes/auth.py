"""Authentication endpoints for APEX API using Supabase Auth with OAuth, 2FA, and multi-account support."""

from __future__ import annotations

import structlog
from datetime import timedelta
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from gotrue.errors import AuthApiError
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..auth import TokenData, create_access_token, create_session_token, get_current_user
from ..auth_helpers import get_account_from_email, normalize_provider
from ..auth_health import get_health_monitor, ProviderStatus
from ..auth_password import (
    get_lockout_manager,
    hash_password,
    PasswordStrength,
    generate_reset_token,
    validate_reset_token,
)
from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config, settings
from ..duo_client import get_duo_service
from ..schemas import ResponseEnvelope, add_assumption
from ..supabase_client import get_supabase_client, get_supabase_admin

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# JWT settings
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


class TokenResponse(BaseModel):
    """OAuth2 token response with session or access token."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: dict
    session_token: Optional[str] = None  # For 2FA flow
    requires_2fa: bool = False


class SessionTokenResponse(BaseModel):
    """Session token response for 2FA flow."""

    session_token: str
    expires_in: int
    user: dict


class Verify2FARequest(BaseModel):
    """Request to verify 2FA with Duo."""

    session_token: str
    factor: str = "push"  # push, sms, phone, passcode
    passcode: Optional[str] = None  # Required if factor="passcode"


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request to confirm password reset."""

    token: str
    email: EmailStr
    new_password: str


@router.post("/register", response_model=ResponseEnvelope)
async def register(
    email: EmailStr = Query(..., description="User email address"),
    password: str = Query(..., min_length=8, description="User password"),
    account_id: Optional[str] = Query(None, description="Account/organization ID (auto-assigned if not provided)"),
) -> ResponseEnvelope:
    """Register new user via Supabase Auth with automatic account assignment.
    
    Creates a new user account with email/password authentication.
    Account and role are automatically assigned based on email domain.
    Email confirmation may be required based on Supabase configuration.
    """
    logger.info("auth.register", email=email)
    
    # Validate password strength
    is_valid, errors = PasswordStrength.validate(password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password validation failed: " + "; ".join(errors)
        )
    
    # Check provider health (use password provider for registration)
    health_monitor = get_health_monitor()
    provider_status = await health_monitor.check_provider_health("password")
    
    if provider_status == ProviderStatus.DOWN:
        # Fallback: try other providers
        fallback_provider = await health_monitor.select_healthy_provider()
        if not fallback_provider or fallback_provider == "password":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable"
            )
    
    try:
        supabase = get_supabase_client()
        
        # Auto-assign account and role based on email
        auto_account_id, auto_role = get_account_from_email(email, "password")
        final_account_id = account_id or auto_account_id
        
        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "account_id": final_account_id,
                        "role": auto_role,
                        "provider": "password",
                        "accounts": [{"account_id": final_account_id, "role": auto_role}],
                    }
                }
            }
        )
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed - no user returned"
            )
        
        assumptions: list[str] = []
        result = {
            "user_id": response.user.id,
            "email": response.user.email,
            "email_confirmed": response.session is not None,
            "account_id": final_account_id,
            "role": auto_role,
        }
        
        # Email confirmation required if no session returned
        if not response.session:
            add_assumption(assumptions, "Email confirmation required - check your inbox")
        
        return make_envelope(
            result=result,
            assumptions=assumptions,
            confidence=1.0,
            inputs={"email": email, "account_id": final_account_id},
            outputs={"user_id": response.user.id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
    except AuthApiError as e:
        logger.warning("auth.register.failed", email=email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )
    except ValueError as e:
        # Supabase not configured
        logger.error("auth.register.config_missing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )


@router.post("/token", response_model=ResponseEnvelope)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> ResponseEnvelope:
    """OAuth2 password grant login via Supabase Auth.
    
    Supports 2FA flow: if user has 2FA enabled, returns session_token instead of access_token.
    Client must then call /auth/verify-2fa to complete authentication.
    
    Implements account lockout after failed attempts.
    """
    logger.info("auth.login", username=form_data.username)
    
    email = form_data.username.lower()
    lockout_manager = get_lockout_manager()
    
    # Check account lockout
    is_locked, unlock_time = lockout_manager.is_locked(email)
    if is_locked:
        unlock_minutes = int((unlock_time - time.time()) / 60) if unlock_time else 0
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to too many failed attempts. Try again in {unlock_minutes} minutes."
        )
    
    # Check provider health
    health_monitor = get_health_monitor()
    provider_status = await health_monitor.check_provider_health("password")
    
    if provider_status == ProviderStatus.DOWN:
        # Try to find healthy provider
        fallback_provider = await health_monitor.select_healthy_provider()
        if not fallback_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable"
            )
        add_assumption([], f"Using fallback provider: {fallback_provider}")
    
    try:
        supabase = get_supabase_client()
        
        response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password
        })
        
        if not response.session or not response.user:
            # Record failed attempt
            lockout_manager.record_failed_attempt(email)
            remaining = lockout_manager.get_remaining_attempts(email)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials. {remaining} attempts remaining.",
                headers={"WWW-Authenticate": "Bearer", "X-Remaining-Attempts": str(remaining)},
            )
        
        # Successful login - clear lockout
        lockout_manager.record_successful_attempt(email)
        
        user = response.user
        metadata = user.user_metadata or {}
        account_id = metadata.get("account_id", "unknown")
        provider = metadata.get("provider", "password")
        mfa_enabled = metadata.get("mfa_enabled", False)
        
        # Check if 2FA is required
        requires_2fa = mfa_enabled
        if requires_2fa:
            # Return session token for 2FA flow
            session_token = create_session_token(
                user_id=user.id,
                email=user.email or "",
                account_id=account_id,
                provider=provider,
            )
            
            result = SessionTokenResponse(
                session_token=session_token,
                expires_in=600,  # 10 minutes
                user={
                    "id": user.id,
                    "email": user.email,
                    "account_id": account_id,
                }
            )
            
            return make_envelope(
                result=result.model_dump(),
                assumptions=["2FA verification required"],
                confidence=1.0,
                inputs={"username": form_data.username},
                outputs={"user_id": user.id, "requires_2fa": True},
                code_version=get_code_version(),
                model_config=get_model_config(),
            )
        else:
            # Normal login - return access token
            result = TokenResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                token_type="bearer",
                expires_in=response.session.expires_in or 3600,
                user={
                    "id": user.id,
                    "email": user.email,
                    "account_id": account_id,
                },
                requires_2fa=False,
            )
            
            return make_envelope(
                result=result.model_dump(),
                assumptions=[],
                confidence=1.0,
                inputs={"username": form_data.username},
                outputs={"user_id": user.id},
                code_version=get_code_version(),
                model_config=get_model_config(),
            )
            
    except AuthApiError as e:
        # Record failed attempt
        lockout_manager.record_failed_attempt(email)
        remaining = lockout_manager.get_remaining_attempts(email)
        is_locked_now, unlock_time = lockout_manager.is_locked(email)
        
        logger.warning("auth.login.failed", username=form_data.username, error=str(e), remaining=remaining)
        
        detail = f"Invalid credentials. {remaining} attempts remaining."
        if is_locked_now:
            unlock_minutes = int((unlock_time - time.time()) / 60) if unlock_time else 0
            detail = f"Account locked due to too many failed attempts. Try again in {unlock_minutes} minutes."
        
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED if is_locked_now else status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer", "X-Remaining-Attempts": str(remaining)},
        )
    except ValueError as e:
        # Supabase not configured
        logger.error("auth.login.config_missing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )


@router.get("/oauth/{provider}")
async def oauth_login(
    provider: str,
    redirect_to: Optional[str] = Query(None, description="Redirect URL after OAuth"),
) -> RedirectResponse:
    """Initiate OAuth flow for Microsoft 365, Google, or Apple.
    
    Args:
        provider: OAuth provider ("azure", "google", "apple")
        redirect_to: Optional redirect URL (defaults to frontend callback)
    
    Returns:
        Redirect to OAuth provider
    """
    provider_normalized = normalize_provider(provider)
    
    if provider_normalized not in ("azure", "google", "apple"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}. Supported: azure, google, apple"
        )
    
    logger.info("auth.oauth.initiate", provider=provider_normalized)
    
    try:
        supabase = get_supabase_client()
        
        # Default redirect to frontend callback
        callback_url = redirect_to or f"{settings.CORS_ALLOW_ORIGINS[0] if settings.CORS_ALLOW_ORIGINS else 'http://localhost:5173'}/auth/callback"
        
        # Supabase OAuth flow
        oauth_response = supabase.auth.sign_in_with_oauth({
            "provider": provider_normalized,
            "options": {
                "redirect_to": callback_url,
            }
        })
        
        # Redirect to OAuth provider
        if oauth_response.url:
            return RedirectResponse(url=oauth_response.url)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth initialization failed"
            )
            
    except ValueError as e:
        logger.error("auth.oauth.config_missing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    except Exception as e:
        logger.error("auth.oauth.failed", provider=provider_normalized, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth flow failed: {str(e)}"
        )


@router.get("/callback")
async def auth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
) -> RedirectResponse:
    """Handle OAuth callback from provider.
    
    Supabase automatically handles token exchange.
    Redirects to frontend with access token or error.
    """
    if error:
        logger.warning("auth.oauth.callback.error", error=error, description=error_description)
        # Redirect to frontend with error
        frontend_url = settings.CORS_ALLOW_ORIGINS[0] if settings.CORS_ALLOW_ORIGINS else "http://localhost:5173"
        return RedirectResponse(url=f"{frontend_url}/auth/error?error={error}")
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code"
        )
    
    logger.info("auth.oauth.callback", code_present=True)
    
    # Supabase handles code exchange automatically
    # Frontend should call Supabase client to complete exchange
    frontend_url = settings.CORS_ALLOW_ORIGINS[0] if settings.CORS_ALLOW_ORIGINS else "http://localhost:5173"
    return RedirectResponse(url=f"{frontend_url}/auth/callback?code={code}")


@router.post("/verify-2fa", response_model=ResponseEnvelope)
async def verify_2fa(req: Verify2FARequest) -> ResponseEnvelope:
    """Verify 2FA with Duo and issue final access token.
    
    Args:
        req: Session token and 2FA verification details
    
    Returns:
        Final access token with mfa_verified=true
    """
    logger.info("auth.2fa.verify", factor=req.factor)
    
    # Validate session token
    try:
        payload = jwt.decode(req.session_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        account_id = payload.get("account_id")
        provider = payload.get("provider", "password")
        
        if not user_id or not email or not account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session token"
            )
        
        # Verify this is a session token, not a final access token
        if payload.get("type") != "session":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is not a session token"
            )
            
    except JWTError as e:
        logger.warning("auth.2fa.session_token_invalid", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    # Verify with Duo
    duo_service = get_duo_service()
    if not duo_service or not duo_service.is_configured:
        # Duo not configured - skip 2FA and issue token anyway
        logger.warning("auth.2fa.duo_not_configured", user_id=user_id)
        add_assumption([], "Duo 2FA not configured - authentication completed without 2FA")
        
        # Issue token without 2FA
        token_data = {
            "sub": user_id,
            "email": email,
            "account_id": account_id,
            "provider": provider,
            "mfa_verified": False,
        }
        access_token = create_access_token(token_data, mfa_verified=False)
        
        return make_envelope(
            result={
                "access_token": access_token,
                "token_type": "bearer",
                "mfa_verified": False,
            },
            assumptions=["Duo 2FA not configured"],
            confidence=1.0,
            inputs={"factor": req.factor},
            outputs={"user_id": user_id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
    
    # Get user's Duo username (typically email or user_id)
    supabase_admin = get_supabase_admin()
    try:
        user_response = supabase_admin.auth.admin.get_user_by_id(user_id)
        duo_username = user_response.user.user_metadata.get("duo_username") or email
    except Exception:
        duo_username = email
    
    # Perform Duo verification
    success, txid = await duo_service.verify_user(
        username=duo_username,
        factor=req.factor,
        passcode=req.passcode,
    )
    
    if not success:
        logger.warning("auth.2fa.denied", user_id=user_id, factor=req.factor)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA verification failed"
        )
    
    # 2FA successful - issue final access token
    logger.info("auth.2fa.success", user_id=user_id, factor=req.factor)
    
    # Get user's account info from Supabase
    try:
        user_response = supabase_admin.auth.admin.get_user_by_id(user_id)
        metadata = user_response.user.user_metadata or {}
        accounts_data = metadata.get("accounts", [])
    except Exception:
        accounts_data = []
    
    token_data = {
        "sub": user_id,
        "email": email,
        "account_id": account_id,
        "provider": provider,
        "roles": metadata.get("roles", ["user"]),
        "accounts": accounts_data,
        "mfa_verified": True,
    }
    
    access_token = create_access_token(token_data, mfa_verified=True)
    
    return make_envelope(
        result={
            "access_token": access_token,
            "token_type": "bearer",
            "mfa_verified": True,
        },
        assumptions=[],
        confidence=1.0,
        inputs={"factor": req.factor},
        outputs={"user_id": user_id},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/enable-2fa", response_model=ResponseEnvelope)
async def enable_2fa(
    current_user: TokenData = Depends(get_current_user)
) -> ResponseEnvelope:
    """Enable 2FA for current user (opt-in).
    
    Updates user metadata to mark 2FA as enabled.
    User must enroll in Duo separately (via Duo Admin portal or enrollment flow).
    """
    logger.info("auth.2fa.enable", user_id=current_user.user_id)
    
    duo_service = get_duo_service()
    if not duo_service or not duo_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Duo 2FA is not configured"
        )
    
    # Check if user is enrolled in Duo
    enrolled = await duo_service.check_enrollment(current_user.email)
    if not enrolled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not enrolled in Duo. Please enroll via Duo Admin portal first."
        )
    
    # Update user metadata
    try:
        supabase_admin = get_supabase_admin()
        user_response = supabase_admin.auth.admin.get_user_by_id(current_user.user_id)
        metadata = user_response.user.user_metadata or {}
        metadata["mfa_enabled"] = True
        metadata["duo_username"] = current_user.email
        
        supabase_admin.auth.admin.update_user_by_id(
            current_user.user_id,
            {"user_metadata": metadata}
        )
        
        logger.info("auth.2fa.enabled", user_id=current_user.user_id)
        
        return make_envelope(
            result={"enabled": True, "message": "2FA enabled successfully"},
            assumptions=[],
            confidence=1.0,
            inputs={},
            outputs={"user_id": current_user.user_id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
    except Exception as e:
        logger.error("auth.2fa.enable.failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable 2FA: {str(e)}"
        )


@router.post("/disable-2fa", response_model=ResponseEnvelope)
async def disable_2fa(
    current_user: TokenData = Depends(get_current_user)
) -> ResponseEnvelope:
    """Disable 2FA for current user (opt-out)."""
    logger.info("auth.2fa.disable", user_id=current_user.user_id)
    
    try:
        supabase_admin = get_supabase_admin()
        user_response = supabase_admin.auth.admin.get_user_by_id(current_user.user_id)
        metadata = user_response.user.user_metadata or {}
        metadata["mfa_enabled"] = False
        
        supabase_admin.auth.admin.update_user_by_id(
            current_user.user_id,
            {"user_metadata": metadata}
        )
        
        logger.info("auth.2fa.disabled", user_id=current_user.user_id)
        
        return make_envelope(
            result={"enabled": False, "message": "2FA disabled successfully"},
            assumptions=[],
            confidence=1.0,
            inputs={},
            outputs={"user_id": current_user.user_id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
    except Exception as e:
        logger.error("auth.2fa.disable.failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable 2FA: {str(e)}"
        )


@router.get("/2fa-status", response_model=ResponseEnvelope)
async def get_2fa_status(
    current_user: TokenData = Depends(get_current_user)
) -> ResponseEnvelope:
    """Get 2FA status for current user."""
    try:
        supabase_admin = get_supabase_admin()
        user_response = supabase_admin.auth.admin.get_user_by_id(current_user.user_id)
        metadata = user_response.user.user_metadata or {}
        
        mfa_enabled = metadata.get("mfa_enabled", False)
        duo_username = metadata.get("duo_username")
        
        # Check enrollment if Duo is configured
        duo_service = get_duo_service()
        enrolled = False
        if duo_service and duo_service.is_configured and duo_username:
            enrolled = await duo_service.check_enrollment(duo_username)
        
        return make_envelope(
            result={
                "mfa_enabled": mfa_enabled,
                "duo_enrolled": enrolled,
                "duo_configured": duo_service.is_configured if duo_service else False,
            },
            assumptions=[],
            confidence=1.0,
            inputs={},
            outputs={"user_id": current_user.user_id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
    except Exception as e:
        logger.error("auth.2fa.status.failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get 2FA status: {str(e)}"
        )


@router.post("/switch-account", response_model=ResponseEnvelope)
async def switch_account(
    account_id: str = Query(..., description="Account ID to switch to"),
    current_user: TokenData = Depends(get_current_user)
) -> ResponseEnvelope:
    """Switch active account for multi-account users.
    
    Verifies user has access to the requested account, then issues new token.
    """
    logger.info("auth.account.switch", user_id=current_user.user_id, account_id=account_id)
    
    # Check if user has access to this account
    user_account_ids = [acc.account_id for acc in current_user.accounts]
    if account_id not in user_account_ids:
        # Try to fetch from Supabase
        try:
            supabase_admin = get_supabase_admin()
            user_response = supabase_admin.auth.admin.get_user_by_id(current_user.user_id)
            metadata = user_response.user.user_metadata or {}
            accounts_data = metadata.get("accounts", [])
            
            account_ids = [acc.get("account_id") for acc in accounts_data if isinstance(acc, dict)]
            if account_id not in account_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User does not have access to account: {account_id}"
                )
            
            # Find role for this account
            role = "viewer"
            for acc in accounts_data:
                if isinstance(acc, dict) and acc.get("account_id") == account_id:
                    role = acc.get("role", "viewer")
                    break
        except Exception as e:
            logger.error("auth.account.switch.failed", user_id=current_user.user_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify account access: {str(e)}"
            )
    else:
        # Find role from current_user.accounts
        role = "viewer"
        for acc in current_user.accounts:
            if acc.account_id == account_id:
                role = acc.role
                break
    
    # Issue new token with updated account_id
    token_data = {
        "sub": current_user.user_id,
        "email": current_user.email,
        "account_id": account_id,
        "roles": [role],
        "provider": current_user.provider,
        "mfa_verified": current_user.mfa_verified,
        "accounts": current_user.accounts,
    }
    
    access_token = create_access_token(token_data, mfa_verified=current_user.mfa_verified)
    
    logger.info("auth.account.switched", user_id=current_user.user_id, account_id=account_id)
    
    return make_envelope(
        result={
            "access_token": access_token,
            "token_type": "bearer",
            "account_id": account_id,
            "role": role,
        },
        assumptions=[],
        confidence=1.0,
        inputs={"account_id": account_id},
        outputs={"user_id": current_user.user_id},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/accounts", response_model=ResponseEnvelope)
async def list_accounts(
    current_user: TokenData = Depends(get_current_user)
) -> ResponseEnvelope:
    """List all accounts the current user belongs to."""
    return make_envelope(
        result={
            "accounts": [{"account_id": acc.account_id, "role": acc.role} for acc in current_user.accounts],
            "current_account_id": current_user.account_id,
        },
        assumptions=[],
        confidence=1.0,
        inputs={},
        outputs={"user_id": current_user.user_id},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/me", response_model=ResponseEnvelope)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
) -> ResponseEnvelope:
    """Get current user information and account details."""
    return make_envelope(
        result={
            "user_id": current_user.user_id,
            "email": current_user.email,
            "account_id": current_user.account_id,
            "roles": current_user.roles,
            "accounts": [{"account_id": acc.account_id, "role": acc.role} for acc in current_user.accounts],
            "mfa_verified": current_user.mfa_verified,
            "provider": current_user.provider,
        },
        assumptions=[],
        confidence=1.0,
        inputs={},
        outputs={"user_id": current_user.user_id},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/password-reset", response_model=ResponseEnvelope)
async def request_password_reset(req: PasswordResetRequest) -> ResponseEnvelope:
    """Request password reset token.
    
    Sends reset token via email (in production, use email service).
    Token expires in 1 hour.
    """
    logger.info("auth.password_reset.request", email=req.email)
    
    try:
        supabase_admin = get_supabase_admin()
        
        # Find user by email
        try:
            users = supabase_admin.auth.admin.list_users()
            user = None
            for u in users.users:
                if u.email == req.email.lower():
                    user = u
                    break
            
            if not user:
                # Don't reveal if email exists (security best practice)
                logger.info("auth.password_reset.user_not_found", email=req.email)
                return make_envelope(
                    result={"message": "If that email exists, a reset link has been sent."},
                    assumptions=[],
                    confidence=1.0,
                    inputs={"email": req.email},
                    outputs={},
                    code_version=get_code_version(),
                    model_config=get_model_config(),
                )
            
            # Generate reset token
            secret = getattr(settings, "JWT_SECRET_KEY", "dev-secret")
            reset_token = generate_reset_token(req.email, secret)
            
            # Store token in user metadata (in production, use dedicated table)
            metadata = user.user_metadata or {}
            metadata["reset_token"] = reset_token
            metadata["reset_token_expires"] = int(time.time()) + 3600  # 1 hour
            
            supabase_admin.auth.admin.update_user_by_id(
                user.id,
                {"user_metadata": metadata}
            )
            
            # In production, send email with reset link
            logger.info("auth.password_reset.token_generated", email=req.email, user_id=user.id)
            
            return make_envelope(
                result={
                    "message": "If that email exists, a reset link has been sent.",
                    "token": reset_token,  # Remove in production - only for testing
                },
                assumptions=["In production, token sent via email"],
                confidence=1.0,
                inputs={"email": req.email},
                outputs={"user_id": user.id},
                code_version=get_code_version(),
                model_config=get_model_config(),
            )
            
        except Exception as e:
            logger.error("auth.password_reset.error", email=req.email, error=str(e))
            # Don't reveal error details
            return make_envelope(
                result={"message": "If that email exists, a reset link has been sent."},
                assumptions=[],
                confidence=1.0,
                inputs={"email": req.email},
                outputs={},
                code_version=get_code_version(),
                model_config=get_model_config(),
            )
            
    except ValueError as e:
        logger.error("auth.password_reset.config_missing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset service not available"
        )


@router.post("/password-reset/confirm", response_model=ResponseEnvelope)
async def confirm_password_reset(req: PasswordResetConfirm) -> ResponseEnvelope:
    """Confirm password reset with token.
    
    Validates token and updates password.
    """
    logger.info("auth.password_reset.confirm", email=req.email)
    
    # Validate password strength
    is_valid, errors = PasswordStrength.validate(req.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password validation failed: " + "; ".join(errors)
        )
    
    try:
        supabase_admin = get_supabase_admin()
        
        # Find user
        users = supabase_admin.auth.admin.list_users()
        user = None
        for u in users.users:
            if u.email == req.email.lower():
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate token
        metadata = user.user_metadata or {}
        stored_token = metadata.get("reset_token")
        token_expires = metadata.get("reset_token_expires", 0)
        
        if not stored_token or stored_token != req.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        if time.time() > token_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Validate token matches
        secret = getattr(settings, "JWT_SECRET_KEY", "dev-secret")
        if not validate_reset_token(req.token, req.email, secret):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password via Supabase
        supabase_admin.auth.admin.update_user_by_id(
            user.id,
            {"password": req.new_password}
        )
        
        # Clear reset token
        metadata.pop("reset_token", None)
        metadata.pop("reset_token_expires", None)
        supabase_admin.auth.admin.update_user_by_id(
            user.id,
            {"user_metadata": metadata}
        )
        
        logger.info("auth.password_reset.success", email=req.email, user_id=user.id)
        
        return make_envelope(
            result={"message": "Password reset successfully"},
            assumptions=[],
            confidence=1.0,
            inputs={"email": req.email},
            outputs={"user_id": user.id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth.password_reset.confirm.error", email=req.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
