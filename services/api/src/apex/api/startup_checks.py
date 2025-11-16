from __future__ import annotations

import sys

import structlog

from .deps import settings
import logging

logger = logging.getLogger(__name__)


logger = structlog.get_logger(__name__)


def validate_prod_requirements() -> None:
    """Fail-fast in prod if required secrets/env are missing."""
    if settings.ENV != "prod":
        return

    failures: list[str] = []

    # DATABASE_URL
    if not settings.DATABASE_URL or settings.DATABASE_URL.startswith(("postgresql://apex:apex@", "sqlite")):
        failures.append("DATABASE_URL must be set and non-default in prod")

    # REDIS_URL
    if not settings.REDIS_URL or settings.REDIS_URL.startswith(("redis://cache:6379", "memory")):
        failures.append("REDIS_URL must be set and non-default in prod")

    # MINIO credentials
    if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
        failures.append("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set in prod")

    # CORS must be explicitly configured (not empty allowlist)
    if not settings.CORS_ALLOW_ORIGINS:
        failures.append("CORS_ALLOW_ORIGINS must be configured in prod (default deny)")

    # GIT_SHA should not be 'dev' in prod
    if settings.GIT_SHA == "dev":
        failures.append("GIT_SHA must be set to actual git commit SHA in prod")

    if failures:
        logger.error("prod_validation_failed", failures=failures)
        logger.error("FATAL: Production environment validation failed:", file=sys.stderr)
        for f in failures:
            logger.info(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    logger.info("prod_validation_passed")

