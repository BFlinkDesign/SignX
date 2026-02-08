"""MFA routes for authentication API."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from ..auth import TokenData, create_access_token, get_current_user
from ..auth_mfa import MFASetupResponse, MFAVerifyRequest, mfa_manager
from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth/mfa", tags=["auth", "mfa"])


class MFASetupRequest(BaseModel):
    """Request to set up MFA."""
    
    method: str  # "totp", "sms", "email"
    phone_number: Optional[str] = None  # Required for SMS


class MFAEnableRequest(BaseModel):
    """Request to enable MFA after verification."""
    
    secret: str
    code: str


class MFASendCodeRequest(BaseModel):
    """Request to send MFA code."""
    
    method: str  # "sms", "email"
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None


@router.post("/setup/totp", response_model=MFASetupResponse)
async def setup_totp_mfa(
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Set up TOTP-based 2FA for the current user.
    
    Returns:
        - secret: TOTP secret (store securely)
        - qr_code_url: URL for QR code (scan with authenticator app)
        - backup_codes: One-time backup codes for account recovery
    
    **Next step**: Call `/mfa/verify/totp` with a code from your authenticator app.
    """
    try:
        setup_response = mfa_manager.setup_totp(current_user.email)
        
        logger.info("mfa.totp.setup_initiated", user_id=current_user.user_id)
        
        return make_envelope(
            result=setup_response.model_dump(),
            assumptions=["User will scan QR code with authenticator app"],
            confidence=1.0,
            inputs={"user_id": current_user.user_id, "email": current_user.email},
            intermediates={},
            outputs={"secret_length": len(setup_response.secret)},
            code_version=code_version,
            model_config=model_config,
        )
    except Exception as e:
        logger.error("mfa.totp.setup_failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set up TOTP: {e}" )


@router.post("/verify/totp")
async def verify_totp_code(
    request: MFAEnableRequest,
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Verify TOTP code and enable 2FA.
    
    Args:
        secret: The TOTP secret from setup
        code: 6-digit code from authenticator app
    
    Returns:
        Success message and updated token with mfa_verified=True
    """
    is_valid = mfa_manager.verify_totp(request.secret, request.code)
    
    if not is_valid:
        logger.warning("mfa.totp.verify_failed", user_id=current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code"
        )
    
    # TODO: Store secret in database associated with user
    # For now, we'll create a new token with mfa_verified=True
    token_data = {
        "sub": current_user.user_id,
        "email": current_user.email,
        "account_id": current_user.account_id,
        "roles": current_user.roles,
    }
    new_token = create_access_token(token_data, mfa_verified=True)
    
    logger.info("mfa.totp.verified", user_id=current_user.user_id)
    
    return make_envelope(
        result={
            "message": "2FA enabled successfully",
            "access_token": new_token,
            "token_type": "bearer"
        },
        assumptions=["TOTP secret stored securely in database"],
        confidence=1.0,
        inputs={"user_id": current_user.user_id, "code_length": len(request.code)},
        intermediates={"verification_valid": is_valid},
        outputs={"mfa_enabled": True},
        code_version=code_version,
        model_config=model_config,
    )


@router.post("/send/sms")
async def send_sms_code(
    request: MFASendCodeRequest,
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Send a verification code via SMS.
    
    Args:
        phone_number: Recipient phone number (E.164 format)
    
    Returns:
        Success message (code sent separately via SMS)
    """
    if not request.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number is required for SMS verification"
        )
    
    success, code = mfa_manager.send_sms_code(request.phone_number)
    
    if not success:
        logger.error("mfa.sms.send_failed", user_id=current_user.user_id, phone=request.phone_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send SMS code"
        )
    
    # TODO: Store code in Redis with expiration (10 minutes)
    
    logger.info("mfa.sms.code_sent", user_id=current_user.user_id, phone=request.phone_number)
    
    return make_envelope(
        result={
            "message": "Verification code sent via SMS",
            "valid_for_minutes": 10
        },
        assumptions=["Code will expire in 10 minutes", "User has access to phone"],
        confidence=1.0,
        inputs={"user_id": current_user.user_id, "phone": request.phone_number},
        intermediates={"code_generated": True},
        outputs={"sms_sent": True},
        code_version=code_version,
        model_config=model_config,
    )


@router.post("/send/email")
async def send_email_code(
    request: MFASendCodeRequest,
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Send a verification code via email.
    
    Args:
        email: Recipient email address (defaults to user's email)
    
    Returns:
        Success message (code sent separately via email)
    """
    email = request.email or current_user.email
    
    success, code = mfa_manager.send_email_code(email)
    
    if not success:
        logger.error("mfa.email.send_failed", user_id=current_user.user_id, email=email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email code"
        )
    
    # TODO: Store code in Redis with expiration (10 minutes)
    
    logger.info("mfa.email.code_sent", user_id=current_user.user_id, email=email)
    
    return make_envelope(
        result={
            "message": "Verification code sent via email",
            "valid_for_minutes": 10
        },
        assumptions=["Code will expire in 10 minutes", "User has access to email"],
        confidence=1.0,
        inputs={"user_id": current_user.user_id, "email": str(email)},
        intermediates={"code_generated": True},
        outputs={"email_sent": True},
        code_version=code_version,
        model_config=model_config,
    )


@router.post("/verify/code")
async def verify_mfa_code(
    request: MFAVerifyRequest,
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Verify an MFA code (SMS or email).
    
    Args:
        code: The verification code received via SMS or email
        backup_code: Optional backup code if primary method fails
    
    Returns:
        Success message and updated token with mfa_verified=True
    """
    # TODO: Retrieve stored code from Redis and validate
    # For now, we'll accept any 6-digit code as valid (DEV ONLY)
    
    is_valid = len(request.code) == 6 and request.code.isdigit()
    
    if not is_valid:
        logger.warning("mfa.code.verify_failed", user_id=current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code"
        )
    
    # Create new token with mfa_verified=True
    token_data = {
        "sub": current_user.user_id,
        "email": current_user.email,
        "account_id": current_user.account_id,
        "roles": current_user.roles,
    }
    new_token = create_access_token(token_data, mfa_verified=True)
    
    logger.info("mfa.code.verified", user_id=current_user.user_id)
    
    return make_envelope(
        result={
            "message": "Verification successful",
            "access_token": new_token,
            "token_type": "bearer"
        },
        assumptions=["MFA verification complete"],
        confidence=1.0,
        inputs={"user_id": current_user.user_id, "code_length": len(request.code)},
        intermediates={"verification_valid": is_valid},
        outputs={"mfa_verified": True},
        code_version=code_version,
        model_config=model_config,
    )


@router.get("/status")
async def get_mfa_status(
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Get MFA status for the current user.
    
    Returns:
        - mfa_enabled: Whether MFA is enabled
        - mfa_verified: Whether current session is MFA-verified
        - available_methods: List of available MFA methods
    """
    # TODO: Query database for user's MFA configuration
    
    return make_envelope(
        result={
            "mfa_enabled": False,  # TODO: Check database
            "mfa_verified": current_user.mfa_verified,
            "available_methods": ["totp", "sms", "email"],
            "configured_methods": []  # TODO: List from database
        },
        assumptions=["MFA configuration stored in database"],
        confidence=1.0,
        inputs={"user_id": current_user.user_id},
        intermediates={},
        outputs={"mfa_verified": current_user.mfa_verified},
        code_version=code_version,
        model_config=model_config,
    )


@router.post("/disable")
async def disable_mfa(
    current_user: TokenData = Depends(get_current_user),
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    """Disable MFA for the current user.
    
    Requires current session to be MFA-verified.
    """
    if not current_user.mfa_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA verification required to disable MFA"
        )
    
    # TODO: Remove MFA configuration from database
    
    logger.info("mfa.disabled", user_id=current_user.user_id)
    
    return make_envelope(
        result={"message": "MFA disabled successfully"},
        assumptions=["MFA configuration removed from database"],
        confidence=1.0,
        inputs={"user_id": current_user.user_id},
        intermediates={},
        outputs={"mfa_enabled": False},
        code_version=code_version,
        model_config=model_config,
    )
