"""Single Sign-On (SSO) providers for OAuth2 authentication.

Supports Azure AD, Google, and Apple Sign In.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import structlog
from pydantic import BaseModel

from .deps import settings

logger = structlog.get_logger(__name__)


class OAuth2Config(BaseModel):
    """OAuth2 provider configuration."""
    
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    redirect_uri: str
    scopes: list[str]


class OAuth2State(BaseModel):
    """OAuth2 state for CSRF protection."""
    
    state: str
    provider: str
    redirect_to: Optional[str] = None
    created_at: datetime
    expires_at: datetime


class OAuth2TokenResponse(BaseModel):
    """OAuth2 token response."""
    
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class UserInfo(BaseModel):
    """User information from OAuth2 provider."""
    
    provider: str
    provider_user_id: str
    email: str
    email_verified: bool
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None


class AzureADProvider:
    """Azure AD OAuth2 provider."""
    
    def __init__(self, tenant_id: Optional[str] = None):
        """Initialize Azure AD provider.
        
        Args:
            tenant_id: Azure AD tenant ID (from settings if not provided)
        """
        self.tenant_id = tenant_id or getattr(settings, "AZURE_TENANT_ID", "common")
        self.client_id = getattr(settings, "AZURE_CLIENT_ID", None)
        self.client_secret = getattr(settings, "AZURE_CLIENT_SECRET", None)
        self.redirect_uri = getattr(settings, "AZURE_REDIRECT_URI", f"{settings.BASE_URL}/api/v1/auth/sso/azure/callback")
        
        self.authorize_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.userinfo_url = "https://graph.microsoft.com/v1.0/me"
        
        self.scopes = ["openid", "profile", "email", "User.Read"]
    
    def get_authorization_url(self, state: str) -> str:
        """Get the authorization URL for OAuth2 flow.
        
        Args:
            state: CSRF protection state
        
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "response_mode": "query"
        }
        return f"{self.authorize_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> OAuth2TokenResponse:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
        
        Returns:
            OAuth2 token response
        """
        import aiohttp
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error("sso.azure.token_exchange_failed", error=error)
                    raise ValueError(f"Token exchange failed: {error}")
                
                result = await response.json()
                return OAuth2TokenResponse(**result)
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information from Microsoft Graph API.
        
        Args:
            access_token: OAuth2 access token
        
        Returns:
            User information
        """
        import aiohttp
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.userinfo_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error("sso.azure.userinfo_failed", error=error)
                    raise ValueError(f"Failed to get user info: {error}")
                
                data = await response.json()
                
                return UserInfo(
                    provider="azure",
                    provider_user_id=data.get("id"),
                    email=data.get("mail") or data.get("userPrincipalName"),
                    email_verified=True,  # Azure verifies emails
                    name=data.get("displayName"),
                    given_name=data.get("givenName"),
                    family_name=data.get("surname"),
                    picture=None,  # Would need separate Graph API call
                    locale=data.get("preferredLanguage")
                )


class GoogleProvider:
    """Google OAuth2 provider."""
    
    def __init__(self):
        """Initialize Google provider."""
        self.client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
        self.client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)
        self.redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", f"{settings.BASE_URL}/api/v1/auth/sso/google/callback")
        
        self.authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        self.scopes = ["openid", "email", "profile"]
    
    def get_authorization_url(self, state: str) -> str:
        """Get the authorization URL for OAuth2 flow.
        
        Args:
            state: CSRF protection state
        
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent"  # Force consent to get refresh token
        }
        return f"{self.authorize_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> OAuth2TokenResponse:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
        
        Returns:
            OAuth2 token response
        """
        import aiohttp
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error("sso.google.token_exchange_failed", error=error)
                    raise ValueError(f"Token exchange failed: {error}")
                
                result = await response.json()
                return OAuth2TokenResponse(**result)
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information from Google API.
        
        Args:
            access_token: OAuth2 access token
        
        Returns:
            User information
        """
        import aiohttp
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.userinfo_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error("sso.google.userinfo_failed", error=error)
                    raise ValueError(f"Failed to get user info: {error}")
                
                data = await response.json()
                
                return UserInfo(
                    provider="google",
                    provider_user_id=data.get("id"),
                    email=data.get("email"),
                    email_verified=data.get("verified_email", False),
                    name=data.get("name"),
                    given_name=data.get("given_name"),
                    family_name=data.get("family_name"),
                    picture=data.get("picture"),
                    locale=data.get("locale")
                )


class AppleProvider:
    """Apple Sign In provider."""
    
    def __init__(self):
        """Initialize Apple provider."""
        self.client_id = getattr(settings, "APPLE_CLIENT_ID", None)
        self.team_id = getattr(settings, "APPLE_TEAM_ID", None)
        self.key_id = getattr(settings, "APPLE_KEY_ID", None)
        self.private_key = getattr(settings, "APPLE_PRIVATE_KEY", None)
        self.redirect_uri = getattr(settings, "APPLE_REDIRECT_URI", f"{settings.BASE_URL}/api/v1/auth/sso/apple/callback")
        
        self.authorize_url = "https://appleid.apple.com/auth/authorize"
        self.token_url = "https://appleid.apple.com/auth/token"
        
        self.scopes = ["name", "email"]
    
    def get_authorization_url(self, state: str) -> str:
        """Get the authorization URL for OAuth2 flow.
        
        Args:
            state: CSRF protection state
        
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "response_mode": "form_post",  # Apple requires form_post
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state
        }
        return f"{self.authorize_url}?{urlencode(params)}"
    
    def _generate_client_secret(self) -> str:
        """Generate client secret JWT for Apple.
        
        Returns:
            Client secret JWT
        """
        import jwt
        from datetime import datetime, timedelta, UTC
        
        headers = {
            "alg": "ES256",
            "kid": self.key_id
        }
        
        payload = {
            "iss": self.team_id,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(days=180),  # Max 6 months
            "aud": "https://appleid.apple.com",
            "sub": self.client_id
        }
        
        return jwt.encode(payload, self.private_key, algorithm="ES256", headers=headers)
    
    async def exchange_code(self, code: str) -> OAuth2TokenResponse:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
        
        Returns:
            OAuth2 token response
        """
        import aiohttp
        
        client_secret = self._generate_client_secret()
        
        data = {
            "client_id": self.client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error("sso.apple.token_exchange_failed", error=error)
                    raise ValueError(f"Token exchange failed: {error}")
                
                result = await response.json()
                return OAuth2TokenResponse(**result)
    
    async def get_user_info(self, id_token: str) -> UserInfo:
        """Get user information from Apple ID token.
        
        Apple doesn't provide a userinfo endpoint, so we decode the ID token.
        
        Args:
            id_token: ID token from Apple
        
        Returns:
            User information
        """
        import jwt
        
        # Decode without verification (we trust Apple's JWT)
        # In production, should verify signature with Apple's public key
        payload = jwt.decode(id_token, options={"verify_signature": False})
        
        return UserInfo(
            provider="apple",
            provider_user_id=payload.get("sub"),
            email=payload.get("email"),
            email_verified=payload.get("email_verified", False),
            name=None,  # Apple doesn't provide name in token
            given_name=None,
            family_name=None,
            picture=None,
            locale=None
        )


class OAuth2StateManager:
    """Manages OAuth2 state for CSRF protection."""
    
    # In production, store in Redis with expiration
    _states: dict[str, OAuth2State] = {}
    
    @classmethod
    def create_state(cls, provider: str, redirect_to: Optional[str] = None) -> str:
        """Create a new OAuth2 state.
        
        Args:
            provider: OAuth2 provider name
            redirect_to: Optional redirect URL after authentication
        
        Returns:
            State string
        """
        state = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        
        state_obj = OAuth2State(
            state=state,
            provider=provider,
            redirect_to=redirect_to,
            created_at=now,
            expires_at=now + timedelta(minutes=10)
        )
        
        cls._states[state] = state_obj
        logger.info("sso.state.created", provider=provider, state=state[:8])
        
        return state
    
    @classmethod
    def verify_state(cls, state: str, provider: str) -> Optional[OAuth2State]:
        """Verify OAuth2 state.
        
        Args:
            state: State string to verify
            provider: Expected provider name
        
        Returns:
            OAuth2State if valid, None otherwise
        """
        state_obj = cls._states.get(state)
        
        if not state_obj:
            logger.warning("sso.state.not_found", state=state[:8])
            return None
        
        if state_obj.provider != provider:
            logger.warning("sso.state.provider_mismatch", expected=provider, got=state_obj.provider)
            return None
        
        if datetime.now(UTC) > state_obj.expires_at:
            logger.warning("sso.state.expired", state=state[:8])
            del cls._states[state]
            return None
        
        # State is valid, remove it (one-time use)
        del cls._states[state]
        logger.info("sso.state.verified", provider=provider, state=state[:8])
        
        return state_obj


# Provider instances
azure_provider = AzureADProvider()
google_provider = GoogleProvider()
apple_provider = AppleProvider()
state_manager = OAuth2StateManager()
