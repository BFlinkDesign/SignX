"""
Pytest configuration and shared fixtures for APEX API tests.

This module provides:
- Async database session fixtures with transaction rollback
- Test database initialization and cleanup
- Common test data fixtures (pole sections, configurations)
- AISC database connection fixtures
- Mock external service fixtures

Usage:
    pytest tests/                    # Run all tests
    pytest tests/unit/               # Run unit tests only
    pytest tests/integration/        # Run integration tests only
    pytest -v --cov=apex             # Run with coverage report
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from apex.api.db import Base
from apex.domains.signage.single_pole_solver import PoleSection
from apex.domains.signage.asce7_wind import ExposureCategory, RiskCategory


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "contract: marks tests as contract/API schema tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests requiring database connection"
    )
    config.addinivalue_line(
        "markers", "determinism: marks tests validating calculation determinism"
    )


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.

    This ensures all async tests share the same event loop,
    which is required for async fixtures with session scope.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Get test database URL from environment or use default.

    Set TEST_DATABASE_URL environment variable to override default.
    Default: postgresql+asyncpg://apex:apex@localhost:5432/apex_test
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://apex:apex@localhost:5432/apex_test"
    )


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create async database engine for testing.

    Uses NullPool to avoid connection pooling issues in tests.
    Creates all tables at session start and drops them at session end.
    """
    engine = create_async_engine(
        test_database_url,
        echo=False,  # Set to True for SQL debugging
        poolclass=NullPool,  # No connection pooling for tests
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session with automatic transaction rollback.

    Each test runs in a transaction that is rolled back after the test,
    ensuring test isolation and fast cleanup.

    Usage:
        async def test_something(db_session: AsyncSession):
            result = await db_session.execute(select(Project))
            assert result is not None
    """
    # Create a new connection for this test
    async with test_engine.connect() as connection:
        # Start a transaction
        transaction = await connection.begin()

        # Create session bound to this connection/transaction
        async_session_maker = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        session = async_session_maker()

        yield session

        # Rollback transaction (undoes all changes)
        await session.close()
        await transaction.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session_commit(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session that commits changes.

    Use this for tests that need to verify committed data or test
    commit hooks. Most tests should use db_session instead.

    WARNING: Changes are NOT automatically rolled back. Use sparingly.
    """
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    session = async_session_maker()

    yield session

    await session.close()


# ============================================================================
# AISC Database Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def aisc_connection(test_database_url: str):
    """
    Create asyncpg connection for AISC database queries.

    Use this for testing raw SQL queries to the AISC shapes database.

    Usage:
        async def test_aisc_query(aisc_connection):
            result = await aisc_connection.fetch(
                "SELECT * FROM aisc_shapes_v16 WHERE type = 'HSS' LIMIT 5"
            )
            assert len(result) > 0
    """
    import asyncpg

    # Convert SQLAlchemy URL to asyncpg format
    # postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    asyncpg_url = test_database_url.replace("+asyncpg", "")

    conn = await asyncpg.connect(asyncpg_url)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def seed_aisc_test_data(db_session: AsyncSession):
    """
    Seed AISC test data for database tests.

    Populates test database with a subset of AISC shapes for testing.
    Data is automatically rolled back after the test.
    """
    # Insert test AISC shapes
    test_shapes = [
        {
            "aisc_manual_label": "HSS8X8X1/4",
            "type": "HSS",
            "w": 24.2,
            "area": 7.11,
            "d": 8.0,
            "sx": 19.8,
            "ix": 79.3,
            "rx": 3.34,
            "is_astm_a1085": False,
        },
        {
            "aisc_manual_label": "HSS6X6X1/4",
            "type": "HSS",
            "w": 18.2,
            "area": 5.36,
            "d": 6.0,
            "sx": 11.2,
            "ix": 33.5,
            "rx": 2.50,
            "is_astm_a1085": False,
        },
        {
            "aisc_manual_label": "HSS10X10X3/8",
            "type": "HSS",
            "w": 49.0,
            "area": 14.4,
            "d": 10.0,
            "sx": 49.1,
            "ix": 245.0,
            "rx": 4.12,
            "is_astm_a1085": True,
        },
    ]

    for shape in test_shapes:
        await db_session.execute(
            text("""
                INSERT INTO aisc_shapes_v16
                (aisc_manual_label, type, w, area, d, sx, ix, rx, is_astm_a1085)
                VALUES
                (:aisc_manual_label, :type, :w, :area, :d, :sx, :ix, :rx, :is_astm_a1085)
                ON CONFLICT (aisc_manual_label) DO NOTHING
            """),
            shape
        )

    await db_session.commit()
    yield
    # Rollback happens automatically via db_session fixture


# ============================================================================
# Domain Model Fixtures (Pole Sections)
# ============================================================================

@pytest.fixture
def hss_8x8x1_4() -> PoleSection:
    """
    HSS 8×8×1/4 section properties from AISC Shapes Database.

    Common monument sign pole section (A500 Grade C steel).
    """
    return PoleSection(
        designation="HSS8X8X1/4",
        type="HSS",
        area_in2=7.11,
        depth_in=8.0,
        weight_plf=24.2,
        sx_in3=19.8,
        ix_in4=79.3,
        rx_in=3.34,
        fy_ksi=50.0,  # A500 Grade C
        fu_ksi=65.0,
    )


@pytest.fixture
def hss_6x6x1_4() -> PoleSection:
    """
    HSS 6×6×1/4 section properties from AISC Shapes Database.

    Smaller pole section for lower monument signs.
    """
    return PoleSection(
        designation="HSS6X6X1/4",
        type="HSS",
        area_in2=5.36,
        depth_in=6.0,
        weight_plf=18.2,
        sx_in3=11.2,
        ix_in4=33.5,
        rx_in=2.50,
        fy_ksi=50.0,
        fu_ksi=65.0,
    )


@pytest.fixture
def hss_10x10x3_8() -> PoleSection:
    """
    HSS 10×10×3/8 section properties from AISC Shapes Database.

    Heavy-duty pole section for tall pylon signs (A1085 high-strength).
    """
    return PoleSection(
        designation="HSS10X10X3/8",
        type="HSS",
        area_in2=14.4,
        depth_in=10.0,
        weight_plf=49.0,
        sx_in3=49.1,
        ix_in4=245.0,
        rx_in=4.12,
        fy_ksi=65.0,  # A1085 high-strength
        fu_ksi=80.0,
        is_a1085=True,
    )


@pytest.fixture
def pipe_6_std() -> PoleSection:
    """
    PIPE 6 STD section properties from AISC Shapes Database.

    Standard 6-inch steel pipe (A53 Grade B).
    """
    return PoleSection(
        designation="PIPE6STD",
        type="PIPE",
        area_in2=5.58,
        depth_in=6.625,
        weight_plf=18.97,
        sx_in3=8.50,
        ix_in4=28.1,
        rx_in=2.25,
        fy_ksi=35.0,  # A53 Grade B
        fu_ksi=60.0,
    )


# ============================================================================
# Wind Load Parameter Fixtures
# ============================================================================

@pytest.fixture
def grimes_iowa_wind_config() -> dict:
    """
    Baseline wind configuration for Grimes, Iowa.

    - Wind speed: 115 mph (3-second gust per ASCE 7-22 Figure 26.5-1A)
    - Exposure: C (open terrain, typical for Iowa)
    - Risk category: II (normal structures)
    """
    return {
        "basic_wind_speed_mph": 115.0,
        "risk_category": RiskCategory.II,
        "exposure_category": ExposureCategory.C,
        "topographic_factor_kzt": 1.0,
        "wind_directionality_factor_kd": 0.85,
        "elevation_factor_ke": 1.0,
        "gust_effect_factor_g": 0.85,
        "force_coefficient_cf": 1.2,
    }


@pytest.fixture
def high_wind_config() -> dict:
    """
    High wind configuration (coastal/hurricane zones).

    - Wind speed: 150 mph
    - Exposure: D (coastal, unobstructed)
    - Risk category: III (substantial hazard)
    """
    return {
        "basic_wind_speed_mph": 150.0,
        "risk_category": RiskCategory.III,
        "exposure_category": ExposureCategory.D,
        "topographic_factor_kzt": 1.0,
        "wind_directionality_factor_kd": 0.85,
        "elevation_factor_ke": 1.0,
        "gust_effect_factor_g": 0.85,
        "force_coefficient_cf": 1.2,
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing cache operations."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client for testing object storage operations."""
    mock = Mock()
    mock.bucket_exists = Mock(return_value=True)
    mock.put_object = Mock(return_value=True)
    mock.get_object = Mock(return_value=Mock())
    mock.remove_object = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_celery_client():
    """Mock Celery client for testing async task operations."""
    mock = Mock()
    mock.send_task = Mock(return_value=Mock(id="test-task-id"))
    return mock


# ============================================================================
# Parametrized Test Data
# ============================================================================

@pytest.fixture
def standard_test_cases() -> list[dict]:
    """
    Standard test cases for parametrized testing.

    Covers common sign configurations with known results.
    """
    return [
        {
            "name": "small_monument_sign",
            "pole_height_ft": 10.0,
            "sign_area_sqft": 16.0,  # 4×4 ft
            "wind_speed_mph": 115.0,
            "expected_force_range": (300, 500),  # lbs
        },
        {
            "name": "medium_monument_sign",
            "pole_height_ft": 15.0,
            "sign_area_sqft": 32.0,  # 8×4 ft
            "wind_speed_mph": 115.0,
            "expected_force_range": (600, 900),  # lbs
        },
        {
            "name": "large_pylon_sign",
            "pole_height_ft": 40.0,
            "sign_area_sqft": 80.0,  # 10×8 ft
            "wind_speed_mph": 120.0,
            "expected_force_range": (1800, 2400),  # lbs
        },
    ]


# ============================================================================
# Test Utilities
# ============================================================================

@pytest.fixture
def assert_within_tolerance():
    """
    Helper function for engineering tolerance checks.

    Usage:
        assert_within_tolerance(actual, expected, percent=1.0)
    """
    def _assert(actual: float, expected: float, percent: float = 1.0, label: str = ""):
        tolerance = abs(expected * percent / 100.0)
        diff = abs(actual - expected)
        assert diff <= tolerance, (
            f"{label} Tolerance check failed: "
            f"actual={actual:.3f}, expected={expected:.3f}, "
            f"diff={diff:.3f}, tolerance={tolerance:.3f} ({percent}%)"
        )
    return _assert


@pytest.fixture
def verify_determinism():
    """
    Helper function to verify calculation determinism.

    Runs the same calculation N times and ensures identical results.

    Usage:
        verify_determinism(lambda: my_calculation(args), runs=10)
    """
    def _verify(calc_func, runs: int = 5):
        results = [calc_func() for _ in range(runs)]
        first = results[0]

        for i, result in enumerate(results[1:], start=2):
            assert result == first, (
                f"Determinism check failed: run 1 != run {i}\n"
                f"Run 1: {first}\n"
                f"Run {i}: {result}"
            )

        return first

    return _verify
