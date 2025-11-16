"""Duo Security 2FA integration for APEX API.

Provides Duo authentication services with graceful fallback if not configured.
"""

from __future__ import annotations

import structlog
from typing import Any, Optional

logger = structlog.get_logger(__name__)

try:
    from duo_client import Auth
    DUO_AVAILABLE = True
except ImportError:
    DUO_AVAILABLE = False
    Auth = None  # type: ignore


class DuoService:
    """Duo Security authentication service.
    
    Provides 2FA verification, enrollment, and status checking.
    Gracefully handles missing configuration (2FA optional).
    """
    
    def __init__(self, ikey: Optional[str], skey: Optional[str], host: Optional[str]):
        """Initialize Duo service.
        
        Args:
            ikey: Duo integration key
            skey: Duo secret key
            host: Duo API hostname (e.g., api-xxxxx.duosecurity.com)
        """
        self.ikey = ikey
        self.skey = skey
        self.host = host
        self._client: Optional[Auth] = None
        
        if DUO_AVAILABLE and ikey and skey and host:
            try:
                self._client = Auth(ikey=ikey, skey=skey, host=host)
                logger.info("duo.service.initialized", host=host)
            except Exception as e:
                logger.warning("duo.service.init_failed", error=str(e))
                self._client = None
        else:
            logger.debug("duo.service.not_configured")
    
    @property
    def is_configured(self) -> bool:
        """Check if Duo is fully configured and available."""
        return self._client is not None
    
    async def verify_user(
        self, 
        username: str, 
        factor: str = "push",
        device: str = "auto",
        passcode: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Verify user with Duo 2FA.
        
        Args:
            username: Duo username (typically email or user_id)
            factor: Verification factor ("push", "sms", "phone", "passcode")
            device: Device selector ("auto" or specific device ID)
            passcode: Passcode for "passcode" factor (required if factor="passcode")
        
        Returns:
            Tuple of (success: bool, txid: Optional[str])
            txid is provided for async flows (push, SMS, phone)
        """
        if not self.is_configured:
            logger.debug("duo.verify.skipped", username=username, reason="not_configured")
            return False, None
        
        try:
            # Prepare auth parameters
            auth_params: dict[str, Any] = {
                "username": username,
                "factor": factor,
                "device": device,
            }
            
            if factor == "passcode" and passcode:
                auth_params["passcode"] = passcode
            
            # Perform authentication
            response = self._client.auth(**auth_params)
            
            if response.get("result") == "allow":
                logger.info("duo.verify.success", username=username, factor=factor)
                return True, response.get("txid")
            else:
                logger.warning("duo.verify.denied", username=username, result=response.get("result"))
                return False, response.get("txid")
                
        except Exception as e:
            logger.error("duo.verify.error", username=username, error=str(e))
            return False, None
    
    async def check_enrollment(self, username: str) -> bool:
        """Check if user is enrolled in Duo.
        
        Args:
            username: Duo username
        
        Returns:
            True if user is enrolled, False otherwise
        """
        if not self.is_configured:
            return False
        
        try:
            # Query user's devices
            response = self._client.user(username)
            devices = response.get("devices", [])
            
            # User is enrolled if they have at least one device
            enrolled = len(devices) > 0
            logger.debug("duo.enrollment.check", username=username, enrolled=enrolled)
            return enrolled
            
        except Exception as e:
            logger.warning("duo.enrollment.check_error", username=username, error=str(e))
            return False
    
    async def enroll_user(self, username: str) -> dict[str, Any]:
        """Enroll user in Duo (requires admin API - not typically used).
        
        Args:
            username: Duo username
        
        Returns:
            Enrollment response data
        """
        if not self.is_configured:
            return {"error": "Duo not configured"}
        
        try:
            # This typically requires admin API access
            # For most setups, enrollment happens via Duo Admin portal
            logger.info("duo.enroll.attempt", username=username)
            return {"status": "requires_admin_portal"}
            
        except Exception as e:
            logger.error("duo.enroll.error", username=username, error=str(e))
            return {"error": str(e)}


def get_duo_service() -> Optional[DuoService]:
    """Get configured Duo service instance.
    
    Returns:
        DuoService if configured, None otherwise
    """
    from .deps import settings
    
    if not settings.DUO_IKEY or not settings.DUO_SKEY or not settings.DUO_HOST:
        return None
    
    return DuoService(
        ikey=settings.DUO_IKEY,
        skey=settings.DUO_SKEY,
        host=settings.DUO_HOST,
    )

