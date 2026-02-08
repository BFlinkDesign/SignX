"""Multi-Factor Authentication (MFA) implementation for APEX API.

Supports TOTP (Time-based One-Time Password), SMS, and email-based 2FA.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

import pyotp
import structlog
from pydantic import BaseModel, EmailStr

from .deps import settings

logger = structlog.get_logger(__name__)


class MFASetupResponse(BaseModel):
    """Response for MFA setup initiation."""
    
    secret: str
    qr_code_url: str
    backup_codes: list[str]
    

class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code."""
    
    code: str
    backup_code: Optional[str] = None
    

class MFAMethod(BaseModel):
    """MFA method configuration."""
    
    method_type: str  # "totp", "sms", "email"
    enabled: bool
    verified: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class TOTPManager:
    """Manages TOTP-based 2FA."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_provisioning_uri(secret: str, email: str, issuer: str = "SignX") -> str:
        """Get the provisioning URI for QR code generation."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    @staticmethod
    def verify_code(secret: str, code: str, window: int = 1) -> bool:
        """Verify a TOTP code.
        
        Args:
            secret: The TOTP secret
            code: The code to verify
            window: Number of time windows to check (default 1 = ±30 seconds)
        
        Returns:
            True if code is valid
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)


class BackupCodeManager:
    """Manages backup codes for account recovery."""
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """Generate a set of backup codes.
        
        Args:
            count: Number of backup codes to generate
        
        Returns:
            List of backup codes (8 characters each)
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8 character hex
            codes.append(f"{code[:4]}-{code[4:]}")  # Format: XXXX-XXXX
        return codes
    
    @staticmethod
    def hash_backup_code(code: str) -> str:
        """Hash a backup code for storage.
        
        Args:
            code: The backup code to hash
        
        Returns:
            Hashed backup code
        """
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()
    
    @staticmethod
    def verify_backup_code(code: str, stored_hash: str) -> bool:
        """Verify a backup code against its hash.
        
        Args:
            code: The backup code to verify
            stored_hash: The stored hash to compare against
        
        Returns:
            True if code matches
        """
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest() == stored_hash


class SMSProvider:
    """Manages SMS-based 2FA (Twilio integration)."""
    
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None):
        """Initialize SMS provider.
        
        Args:
            account_sid: Twilio account SID (from settings if not provided)
            auth_token: Twilio auth token (from settings if not provided)
        """
        self.account_sid = account_sid or getattr(settings, "TWILIO_ACCOUNT_SID", None)
        self.auth_token = auth_token or getattr(settings, "TWILIO_AUTH_TOKEN", None)
        self.from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)
        
        self._client = None
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                logger.warning("mfa.sms.twilio_not_installed")
    
    def send_code(self, phone_number: str, code: str) -> bool:
        """Send a verification code via SMS.
        
        Args:
            phone_number: Recipient phone number (E.164 format)
            code: The verification code to send
        
        Returns:
            True if SMS sent successfully
        """
        if not self._client:
            logger.error("mfa.sms.not_configured")
            return False
        
        try:
            message = self._client.messages.create(
                body=f"Your SignX verification code is: {code}. Valid for 10 minutes.",
                from_=self.from_number,
                to=phone_number
            )
            logger.info("mfa.sms.sent", phone=phone_number, message_sid=message.sid)
            return True
        except Exception as e:
            logger.error("mfa.sms.send_failed", phone=phone_number, error=str(e))
            return False
    
    @staticmethod
    def generate_code(length: int = 6) -> str:
        """Generate a random numeric code.
        
        Args:
            length: Length of the code (default 6)
        
        Returns:
            Random numeric code
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


class EmailProvider:
    """Manages email-based 2FA and magic links."""
    
    def __init__(self):
        """Initialize email provider."""
        self.from_email = getattr(settings, "EMAIL_FROM", "noreply@signx.com")
        self._client = None
        
        # Try to initialize email client (e.g., SendGrid, AWS SES)
        try:
            import sendgrid
            api_key = getattr(settings, "SENDGRID_API_KEY", None)
            if api_key:
                self._client = sendgrid.SendGridAPIClient(api_key)
        except ImportError:
            logger.warning("mfa.email.sendgrid_not_installed")
    
    def send_code(self, email: EmailStr, code: str) -> bool:
        """Send a verification code via email.
        
        Args:
            email: Recipient email address
            code: The verification code to send
        
        Returns:
            True if email sent successfully
        """
        if not self._client:
            logger.warning("mfa.email.not_configured", email=email, code=code)
            # In development, just log the code
            return True
        
        try:
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=self.from_email,
                to_emails=str(email),
                subject="SignX - Verification Code",
                html_content=f"""
                <h2>SignX Verification</h2>
                <p>Your verification code is:</p>
                <h1 style="font-size: 32px; letter-spacing: 5px;">{code}</h1>
                <p>This code is valid for 10 minutes.</p>
                <p>If you didn't request this code, please ignore this email.</p>
                """
            )
            
            response = self._client.send(message)
            logger.info("mfa.email.sent", email=email, status=response.status_code)
            return response.status_code == 202
        except Exception as e:
            logger.error("mfa.email.send_failed", email=email, error=str(e))
            return False
    
    def send_magic_link(self, email: EmailStr, token: str, base_url: str) -> bool:
        """Send a magic link for passwordless authentication.
        
        Args:
            email: Recipient email address
            token: The authentication token
            base_url: Base URL for the magic link
        
        Returns:
            True if email sent successfully
        """
        if not self._client:
            logger.warning("mfa.email.magic_link_not_configured", email=email)
            return True
        
        magic_link = f"{base_url}/auth/magic?token={token}"
        
        try:
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=self.from_email,
                to_emails=str(email),
                subject="SignX - Sign In Link",
                html_content=f"""
                <h2>SignX Sign In</h2>
                <p>Click the link below to sign in to your account:</p>
                <p><a href="{magic_link}" style="font-size: 18px;">Sign In to SignX</a></p>
                <p>This link is valid for 10 minutes and can only be used once.</p>
                <p>If you didn't request this link, please ignore this email.</p>
                """
            )
            
            response = self._client.send(message)
            logger.info("mfa.email.magic_link_sent", email=email, status=response.status_code)
            return response.status_code == 202
        except Exception as e:
            logger.error("mfa.email.magic_link_failed", email=email, error=str(e))
            return False
    
    @staticmethod
    def generate_code(length: int = 6) -> str:
        """Generate a random numeric code.
        
        Args:
            length: Length of the code (default 6)
        
        Returns:
            Random numeric code
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


class MFAManager:
    """High-level MFA management."""
    
    def __init__(self):
        """Initialize MFA manager."""
        self.totp = TOTPManager()
        self.backup = BackupCodeManager()
        self.sms = SMSProvider()
        self.email = EmailProvider()
    
    def setup_totp(self, email: str) -> MFASetupResponse:
        """Set up TOTP-based 2FA for a user.
        
        Args:
            email: User's email address
        
        Returns:
            Setup response with secret, QR code URL, and backup codes
        """
        secret = self.totp.generate_secret()
        qr_code_url = self.totp.get_provisioning_uri(secret, email)
        backup_codes = self.backup.generate_backup_codes()
        
        logger.info("mfa.totp.setup", email=email)
        
        return MFASetupResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes
        )
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code.
        
        Args:
            secret: The TOTP secret
            code: The code to verify
        
        Returns:
            True if code is valid
        """
        is_valid = self.totp.verify_code(secret, code)
        logger.info("mfa.totp.verify", valid=is_valid)
        return is_valid
    
    def send_sms_code(self, phone_number: str) -> tuple[bool, str]:
        """Send a verification code via SMS.
        
        Args:
            phone_number: Recipient phone number
        
        Returns:
            Tuple of (success, code)
        """
        code = self.sms.generate_code()
        success = self.sms.send_code(phone_number, code)
        
        if success:
            logger.info("mfa.sms.code_sent", phone=phone_number)
        else:
            logger.error("mfa.sms.code_failed", phone=phone_number)
        
        return success, code
    
    def send_email_code(self, email: EmailStr) -> tuple[bool, str]:
        """Send a verification code via email.
        
        Args:
            email: Recipient email address
        
        Returns:
            Tuple of (success, code)
        """
        code = self.email.generate_code()
        success = self.email.send_code(email, code)
        
        if success:
            logger.info("mfa.email.code_sent", email=email)
        else:
            logger.error("mfa.email.code_failed", email=email)
        
        return success, code
    
    def send_magic_link(self, email: EmailStr, token: str, base_url: str) -> bool:
        """Send a magic link for passwordless authentication.
        
        Args:
            email: Recipient email address
            token: The authentication token
            base_url: Base URL for the magic link
        
        Returns:
            True if email sent successfully
        """
        success = self.email.send_magic_link(email, token, base_url)
        
        if success:
            logger.info("mfa.magic_link.sent", email=email)
        else:
            logger.error("mfa.magic_link.failed", email=email)
        
        return success


# Global MFA manager instance
mfa_manager = MFAManager()
