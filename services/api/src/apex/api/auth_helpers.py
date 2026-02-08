"""Authentication helper functions for account assignment and role management."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


def get_account_from_email(email: str, provider: str) -> tuple[str, str]:
    """Determine account_id and role from email address and auth provider.
    
    Rules:
    - @eaglesign.net (via Azure/Microsoft 365) → "eagle-sign" account, "admin" role
    - Other Microsoft 365 (azure provider) → "custom" account, "client" role (B2B customers)
    - Google/Apple (consumer) → "custom" account, "viewer" role
    - Email/password → "custom" account, "viewer" role
    
    Args:
        email: User email address
        provider: Auth provider ("azure", "google", "apple", "password")
    
    Returns:
        Tuple of (account_id, role)
    """
    email_lower = email.lower() if email else ""
    
    # Internal staff with Microsoft 365
    if email_lower.endswith("@eaglesign.net"):
        logger.info("auth.account.assigned", email=email, account="eagle-sign", role="admin", provider=provider)
        return "eagle-sign", "admin"
    
    # External Microsoft 365 users (B2B clients)
    if provider == "azure":
        logger.info("auth.account.assigned", email=email, account="custom", role="client", provider=provider)
        return "custom", "client"
    
    # Consumer Google/Apple or email/password
    logger.info("auth.account.assigned", email=email, account="custom", role="viewer", provider=provider)
    return "custom", "viewer"


def normalize_provider(provider: str) -> str:
    """Normalize provider name to canonical format.
    
    Args:
        provider: Provider string (case-insensitive)
    
    Returns:
        Normalized provider: "azure", "google", "apple", "password"
    """
    provider_lower = provider.lower() if provider else ""
    
    # Map common variations
    if provider_lower in ("azure", "microsoft", "microsoft365", "azuread"):
        return "azure"
    elif provider_lower in ("google", "google-oauth", "google_oauth"):
        return "google"
    elif provider_lower in ("apple", "apple-id", "sign-in-with-apple"):
        return "apple"
    else:
        return "password"  # Default fallback

