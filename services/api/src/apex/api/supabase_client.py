"""Supabase client utilities for APEX API.

Provides singleton Supabase clients for both public (anon) and admin (service role) operations.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

try:
    from supabase import create_client
    from gotrue.errors import AuthApiError
except ImportError:
    create_client = None  # type: ignore
    AuthApiError = Exception  # type: ignore


from .deps import settings


@lru_cache()
def get_supabase_client() -> Client:
    """Get singleton Supabase client (anon/public key).
    
    Uses the public/anonymous key for client-side operations.
    Suitable for operations that respect Row Level Security (RLS).
    
    Returns:
        Supabase Client instance
        
    Raises:
        ValueError: If Supabase is not configured
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError(
            "Supabase not configured. Set APEX_SUPABASE_URL and APEX_SUPABASE_KEY environment variables."
        )
    
    if create_client is None:
        raise ImportError(
            "supabase package not installed. Install with: pip install supabase"
        )
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@lru_cache()
def get_supabase_admin() -> Client:
    """Get admin Supabase client with service role key.
    
    Uses the service role key which bypasses Row Level Security (RLS).
    Use with caution - only for server-side admin operations.
    
    Returns:
        Supabase Client instance with admin privileges
        
    Raises:
        ValueError: If Supabase is not configured
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError(
            "Supabase admin not configured. Set APEX_SUPABASE_URL and APEX_SUPABASE_SERVICE_KEY environment variables."
        )
    
    if create_client is None:
        raise ImportError(
            "supabase package not installed. Install with: pip install supabase"
        )
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

