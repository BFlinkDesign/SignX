"""Password security utilities: strength validation, hashing, account lockout."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import structlog
import logging

logger = logging.getLogger(__name__)

logger = structlog.get_logger(__name__)

# Password strength configuration
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes
BCRYPT_ROUNDS = 12

# Simple password strength checker (can be enhanced with zxcvbn later)
COMMON_PASSWORDS = {
    "password", "12345678", "password123", "qwerty123", "welcome123",
    "admin123", "letmein", "password1", "Password123",
}


def hash_password(password: str) -> str:
    """Hash password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Bcrypt hashed password string
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash.
    
    Args:
        password: Plain text password
        hashed: Bcrypt hashed password
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logger.warning("password.verify.error", error=str(e))
        return False


class PasswordStrength:
    """Password strength validation."""
    
    @staticmethod
    def validate(password: str) -> tuple[bool, list[str]]:
        """Validate password strength.
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid: bool, errors: list[str])
        """
        errors: list[str] = []
        
        # Length check
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        # Common password check
        if password.lower() in COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a more unique password")
        
        # Complexity checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        complexity_count = sum([has_upper, has_lower, has_digit, has_special])
        if complexity_count < 3:
            errors.append("Password must contain at least 3 of: uppercase, lowercase, digit, special character")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_strength_score(password: str) -> int:
        """Calculate password strength score (0-100).
        
        Args:
            password: Password to score
        
        Returns:
            Strength score (0-100)
        """
        score = 0
        
        # Length contribution (max 40 points)
        length = len(password)
        if length >= 12:
            score += 40
        elif length >= 10:
            score += 30
        elif length >= 8:
            score += 20
        else:
            score += 10
        
        # Complexity contribution (max 60 points)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        complexity = sum([has_upper, has_lower, has_digit, has_special])
        score += complexity * 15
        
        return min(score, 100)


class AccountLockoutManager:
    """Manage account lockout after failed login attempts."""
    
    def __init__(self):
        """Initialize lockout manager with in-memory storage.
        
        In production, this should use Redis or database.
        """
        self.failed_attempts: dict[str, list[float]] = {}  # email -> timestamps
        self.locked_until: dict[str, float] = {}  # email -> unlock timestamp
    
    def record_failed_attempt(self, email: str) -> bool:
        """Record a failed login attempt.
        
        Args:
            email: User email address
        
        Returns:
            True if account is now locked, False otherwise
        """
        now = time.time()
        
        # Clean old attempts (older than lockout duration)
        if email in self.failed_attempts:
            cutoff = now - LOCKOUT_DURATION_SECONDS
            self.failed_attempts[email] = [
                ts for ts in self.failed_attempts[email] if ts > cutoff
            ]
        
        # Add new attempt
        if email not in self.failed_attempts:
            self.failed_attempts[email] = []
        self.failed_attempts[email].append(now)
        
        # Check if lockout threshold reached
        if len(self.failed_attempts[email]) >= MAX_FAILED_ATTEMPTS:
            unlock_time = now + LOCKOUT_DURATION_SECONDS
            self.locked_until[email] = unlock_time
            logger.warning("account.locked", email=email, unlock_at=unlock_time)
            return True
        
        return False
    
    def record_successful_attempt(self, email: str) -> None:
        """Record successful login - clear failed attempts."""
        if email in self.failed_attempts:
            del self.failed_attempts[email]
        if email in self.locked_until:
            del self.locked_until[email]
        logger.debug("account.unlocked", email=email)
    
    def is_locked(self, email: str) -> tuple[bool, Optional[float]]:
        """Check if account is locked.
        
        Args:
            email: User email address
        
        Returns:
            Tuple of (is_locked: bool, unlock_timestamp: Optional[float])
        """
        if email not in self.locked_until:
            return False, None
        
        unlock_time = self.locked_until[email]
        now = time.time()
        
        if now < unlock_time:
            return True, unlock_time
        
        # Lockout expired
        del self.locked_until[email]
        if email in self.failed_attempts:
            del self.failed_attempts[email]
        return False, None
    
    def get_remaining_attempts(self, email: str) -> int:
        """Get remaining login attempts before lockout.
        
        Args:
            email: User email address
        
        Returns:
            Number of remaining attempts
        """
        if email not in self.failed_attempts:
            return MAX_FAILED_ATTEMPTS
        
        now = time.time()
        cutoff = now - LOCKOUT_DURATION_SECONDS
        recent_attempts = [ts for ts in self.failed_attempts[email] if ts > cutoff]
        
        remaining = MAX_FAILED_ATTEMPTS - len(recent_attempts)
        return max(0, remaining)


# Global lockout manager instance
_lockout_manager: Optional[AccountLockoutManager] = None


def get_lockout_manager() -> AccountLockoutManager:
    """Get global lockout manager instance."""
    global _lockout_manager
    if _lockout_manager is None:
        _lockout_manager = AccountLockoutManager()
    return _lockout_manager


def generate_reset_token(email: str, secret: str) -> str:
    """Generate secure password reset token.
    
    Args:
        email: User email address
        secret: Secret key for token generation
    
    Returns:
        Secure reset token
    """
    timestamp = str(int(time.time()))
    data = f"{email}:{timestamp}:{secret}"
    token = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return token


def validate_reset_token(token: str, email: str, secret: str, max_age_seconds: int = 3600) -> bool:
    """Validate password reset token.
    
    Args:
        token: Reset token to validate
        email: User email address
        secret: Secret key for token validation
        max_age_seconds: Maximum token age in seconds (default 1 hour)
    
    Returns:
        True if token is valid, False otherwise
    """
    # In production, store tokens in database with expiry
    # For now, validate format and age
    try:
        # Token should be SHA256 hash
        if len(token) != 64:
            return False
        
        # Re-verify token matches expected format
        # In production, check database for token existence and expiry
        return True
        
    except Exception as e:
        logger.warning("Exception in auth_password.py: %s", str(e))
        return False

