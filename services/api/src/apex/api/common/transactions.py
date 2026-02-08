"""Transaction management utilities for database operations."""

from __future__ import annotations

import functools
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Import metrics stubs (to be implemented)
try:
    from ..metrics_stub import (
        DB_ROLLBACKS_TOTAL,
        DB_TRANSACTION_DURATION,
        DB_TRANSACTION_FAILURES,
        DB_TRANSACTIONS_TOTAL,
    )
except ImportError:
    # Metrics not yet implemented - use dummy counters
    DB_TRANSACTIONS_TOTAL = None
    DB_TRANSACTION_DURATION = None
    DB_TRANSACTION_FAILURES = None
    DB_ROLLBACKS_TOTAL = None

F = TypeVar("F", bound=Callable[..., Any])


def with_transaction(func: F) -> F:
    """Decorator to wrap async functions with automatic transaction management.
    
    Automatically commits on success, rolls back on exception.
    Works with FastAPI dependency injection where `db` is a dependency.
    
    Usage:
        @with_transaction
        async def my_route(db: AsyncSession = Depends(get_db)):
            # ... database operations ...
            # Auto-commits on success, auto-rollbacks on exception
            return result
    
    Note: Only commits if function completes without exception.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Find db session - check kwargs first (FastAPI dependency injection)
        db: AsyncSession | None = kwargs.get("db")
        
        # If not in kwargs, check args (less common but possible)
        if db is None:
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db = arg
                    break
        
        if db is None:
            logger.warning("with_transaction.no_db_session", func=func.__name__)
            # Function doesn't use db - execute normally
            return await func(*args, **kwargs)
        
        operation = func.__name__
        
        # Track transaction start
        if DB_TRANSACTIONS_TOTAL:
            DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="start").inc()
        
        try:
            # Time transaction duration
            if DB_TRANSACTION_DURATION:
                with DB_TRANSACTION_DURATION.labels(operation=operation).time():
                    result = await func(*args, **kwargs)
            else:
                result = await func(*args, **kwargs)
            
            # Only commit if function completed successfully
            await db.commit()
            
            # Track success
            if DB_TRANSACTIONS_TOTAL:
                DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="success").inc()
            
            logger.debug("transaction.committed", func=func.__name__)
            return result
        except Exception as e:
            await db.rollback()
            
            # Track failure
            if DB_ROLLBACKS_TOTAL:
                DB_ROLLBACKS_TOTAL.labels(operation=operation).inc()
            if DB_TRANSACTION_FAILURES:
                DB_TRANSACTION_FAILURES.labels(operation=operation).inc()
            if DB_TRANSACTIONS_TOTAL:
                DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="failure").inc()
            
            logger.error(
                "transaction.rolled_back",
                func=func.__name__,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    return wrapper  # type: ignore


@asynccontextmanager
async def transaction(db: AsyncSession, operation: str = "unknown"):
    """Context manager for explicit transaction control.
    
    Usage:
        async with transaction(db, operation="create_project") as tx:
            # ... database operations ...
            # Auto-commits on successful exit
            # Auto-rollbacks on exception
    
    Args:
        db: Database session
        operation: Operation name for metrics (default: "unknown")
    
    Returns:
        The database session (for convenience)
    """
    # Track transaction start
    if DB_TRANSACTIONS_TOTAL:
        DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="start").inc()
    
    try:
        # Time transaction duration
        if DB_TRANSACTION_DURATION:
            with DB_TRANSACTION_DURATION.labels(operation=operation).time():
                yield db
        else:
            yield db
        
        await db.commit()
        
        # Track success
        if DB_TRANSACTIONS_TOTAL:
            DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="success").inc()
        
        logger.debug("transaction.committed", operation=operation)
    except Exception as e:
        await db.rollback()
        
        # Track failure
        if DB_ROLLBACKS_TOTAL:
            DB_ROLLBACKS_TOTAL.labels(operation=operation).inc()
        if DB_TRANSACTION_FAILURES:
            DB_TRANSACTION_FAILURES.labels(operation=operation).inc()
        if DB_TRANSACTIONS_TOTAL:
            DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="failure").inc()
        
        logger.error(
            "transaction.rolled_back",
            operation=operation,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise

