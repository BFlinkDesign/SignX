"""
test_estimators.py -- Comprehensive pytest suite for all 6 abc_engine estimators.

Tests:
  1. Regression (lock in values with 5% tolerance)
  2. Boundaries (zero SF, zero letters, extreme values)
  3. Properties (parametrized across all 6 estimators)
  4. Scaling (monotonic: more SF/letters -> more hours)
"""

import sys
from pathlib import Path

# Add parent dir so abc_engine can be imported without install
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from abc_engine import (
    JobInput,
    EstimateResult,
    SignType,
    FontType,
    ConstructionType,
    CabinetFace,
    CabinetFrame,
    CabinetShape,
    WORK_CODES,
    MAX_SINGLE_TASK_HOURS,
    estimate,
    estimate_monument,
    estimate_awning,
    estimate_removal,
    estimate_pylon,
    estimate_cabinet,
)


# ---------------------------------------------------------------------------
# Helpers -- build canonical JobInput for each estimator
# ---------------------------------------------------------------------------

def _channel_job(letter_count=10, height=18.0, font=FontType.BLOCK):
    """Channel letter job: N block letters at given height."""
    job = JobInput()
    job.letter_count = letter_count
    job.letter_height_inches = height
    job.font_type = font
    job.construction = ConstructionType.FACE_LIT
    job.sign_type = SignType.CLLIT
    return job


def _monument_job(sf_per_face=32.0, num_faces=2, illuminated=False):
    """Monument sign: DF by default, SF per face."""
    job = JobInput()
    job.sign_type = SignType.MONDF
    job.num_faces = num_faces
    job.sign_sf_per_face = sf_per_face
    job.is_illuminated = illuminated
    return job


def _awning_job(sf=30.0):
    """Awning job at given total SF."""
    job = JobInput()
    job.sign_type = SignType.AWNNON
    job.sign_sf_per_face = sf
    job.num_faces = 1
    return job


def _removal_job(sign_type=SignType.CLLIT, num_units=1):
    """Standalone removal job."""
    job = JobInput()
    job.sign_type = sign_type
    job.num_units = num_units
    return job


def _pylon_job(sf_per_face=48.0, num_faces=2, height_ft=25.0, footing=True):
    """Pylon sign job (illuminated)."""
    job = JobInput()
    job.sign_type = SignType.POLLIT
    job.num_faces = num_faces
    job.sign_sf_per_face = sf_per_face
    job.install_height_ft = height_ft
    job.has_footing = footing
    job.is_illuminated = True
    return job


def _polnon_job(sf_per_face=48.0, num_faces=2, height_ft=25.0, footing=True):
    """Pole sign job (non-illuminated)."""
    job = JobInput()
    job.sign_type = SignType.POLNON
    job.num_faces = num_faces
    job.sign_sf_per_face = sf_per_face
    job.install_height_ft = height_ft
    job.has_footing = footing
    job.is_illuminated = False
    return job


def _cabinet_job(sf_per_face=24.0, num_faces=1, illuminated=True):
    """Aluminum cabinet job."""
    job = JobInput()
    job.sign_type = SignType.ALULIT
    job.num_faces = num_faces
    job.sign_sf_per_face = sf_per_face
    job.is_illuminated = illuminated
    return job


def _all_lines(result: EstimateResult):
    """Return labor_lines + install_lines combined."""
    return result.labor_lines + result.install_lines


# ===========================================================================
# 1. REGRESSION TESTS -- lock in known-good values with 5% tolerance
# ===========================================================================

class TestRegression:
    """Lock regression targets to within 5% relative tolerance."""

    def test_channel_10_block_18in(self):
        r = estimate(_channel_job(10, 18.0))
        assert r.total_man_hours == pytest.approx(18.25, rel=0.05)

    def test_monument_8x4_df_32sf(self):
        r = estimate_monument(_monument_job(sf_per_face=32.0, num_faces=2))
        assert r.total_man_hours == pytest.approx(56.94, rel=0.05)

    def test_awning_30sf(self):
        r = estimate_awning(_awning_job(30.0))
        assert r.total_man_hours == pytest.approx(20.05, rel=0.05)

    def test_removal_cllit(self):
        r = estimate_removal(_removal_job(SignType.CLLIT))
        # Recalibrated from 253K-row dataset: removal + load + OT
        assert r.total_man_hours == pytest.approx(3.96, rel=0.05)

    def test_pylon_8x6_df_25ft_48sf(self):
        r = estimate_pylon(_pylon_job(sf_per_face=48.0, num_faces=2, height_ft=25.0))
        assert r.total_man_hours == pytest.approx(167.78, rel=0.05)
        assert r.total_crew_hours == pytest.approx(8.50, rel=0.05)

    def test_polnon_8x6_df_25ft_48sf(self):
        """POLNON should produce fewer hours than POLLIT (no electrical)."""
        r_lit = estimate_pylon(_pylon_job(sf_per_face=48.0, num_faces=2, height_ft=25.0))
        r_non = estimate_pylon(_polnon_job(sf_per_face=48.0, num_faces=2, height_ft=25.0))
        # POLNON must be less — no 0340 Electrical Wiring
        assert r_non.total_man_hours < r_lit.total_man_hours
        # Should have no 0340 line
        all_codes = [l.work_code for l in r_non.labor_lines + r_non.install_lines]
        assert "0340" not in all_codes
        # POLLIT should have 0340
        lit_codes = [l.work_code for l in r_lit.labor_lines + r_lit.install_lines]
        assert "0340" in lit_codes

    def test_cabinet_6x4_illum_24sf(self):
        r = estimate_cabinet(_cabinet_job(sf_per_face=24.0, num_faces=1, illuminated=True))
        assert r.total_man_hours == pytest.approx(38.08, rel=0.05)


# ===========================================================================
# 2. BOUNDARY TESTS -- edge cases, zero inputs, extremes
# ===========================================================================

class TestBoundaries:
    """Zero SF, zero letters, large values -- warn but never crash."""

    def test_monument_zero_sf_returns_warning(self):
        job = _monument_job(sf_per_face=0.0)
        r = estimate_monument(job)
        assert any("sign_sf_per_face" in w for w in r.warnings)
        assert r.total_man_hours >= 0

    def test_pylon_zero_sf_returns_warning(self):
        job = _pylon_job(sf_per_face=0.0)
        r = estimate_pylon(job)
        assert any("sign_sf_per_face" in w for w in r.warnings)
        assert r.total_man_hours >= 0

    def test_cabinet_zero_sf_returns_warning(self):
        job = _cabinet_job(sf_per_face=0.0)
        r = estimate_cabinet(job)
        assert any("sign_sf_per_face" in w for w in r.warnings)
        assert r.total_man_hours >= 0

    def test_awning_zero_sf_returns_warning(self):
        job = _awning_job(sf=0.0)
        r = estimate_awning(job)
        assert any("sign_sf_per_face" in w for w in r.warnings)
        assert r.total_man_hours >= 0

    def test_channel_zero_letters_returns_no_pf(self):
        """Zero letters with no PF source returns early with warning."""
        job = JobInput()
        job.letter_count = 0
        job.letter_height_inches = 18.0
        job.sign_type = SignType.CLLIT
        r = estimate(job)
        assert r.total_man_hours >= 0
        assert len(r.warnings) > 0

    def test_large_pylon_60ft_120sf(self):
        """Very large pylon stays in 200-1000h range."""
        job = _pylon_job(sf_per_face=60.0, num_faces=2, height_ft=60.0)
        r = estimate_pylon(job)
        assert 200 <= r.total_man_hours <= 1000

    def test_single_unit_removal_positive(self):
        """Single unit removal must produce > 0 hours."""
        r = estimate_removal(_removal_job(SignType.CLLIT, num_units=1))
        assert r.total_man_hours > 0


# ===========================================================================
# 3. PROPERTY TESTS -- parametrized across all 6 estimators
# ===========================================================================

ALL_ESTIMATOR_FIXTURES = [
    ("channel", lambda: estimate(_channel_job())),
    ("monument", lambda: estimate_monument(_monument_job())),
    ("awning", lambda: estimate_awning(_awning_job())),
    ("removal", lambda: estimate_removal(_removal_job())),
    ("pylon", lambda: estimate_pylon(_pylon_job())),
    ("polnon", lambda: estimate_pylon(_polnon_job())),
    ("cabinet", lambda: estimate_cabinet(_cabinet_job())),
]


@pytest.fixture(params=ALL_ESTIMATOR_FIXTURES, ids=[x[0] for x in ALL_ESTIMATOR_FIXTURES])
def estimator_result(request):
    """Yield (name, EstimateResult) for each estimator."""
    name, factory = request.param
    return name, factory()


class TestProperties:
    """Universal properties that hold for every estimator."""

    def test_total_man_hours_non_negative(self, estimator_result):
        name, r = estimator_result
        assert r.total_man_hours >= 0, f"{name}: total_man_hours={r.total_man_hours}"

    def test_no_negative_labor_lines(self, estimator_result):
        name, r = estimator_result
        for line in _all_lines(r):
            assert line.hours >= 0, (
                f"{name}: {line.work_code} has negative hours={line.hours}"
            )

    def test_all_work_codes_in_dict(self, estimator_result):
        name, r = estimator_result
        for line in _all_lines(r):
            assert line.work_code in WORK_CODES, (
                f"{name}: unknown work_code={line.work_code}"
            )

    def test_total_matches_line_sum(self, estimator_result):
        """total_man_hours == sum of man-hrs lines (within 0.02h tolerance)."""
        name, r = estimator_result
        line_sum = sum(
            l.hours for l in _all_lines(r) if l.unit_type == "man-hrs"
        )
        assert abs(r.total_man_hours - line_sum) <= 0.02, (
            f"{name}: total={r.total_man_hours} vs line_sum={line_sum}"
        )

    def test_no_single_code_exceeds_max(self, estimator_result):
        """No individual work code should exceed MAX_SINGLE_TASK_HOURS (80h)."""
        name, r = estimator_result
        for line in _all_lines(r):
            assert line.hours <= MAX_SINGLE_TASK_HOURS, (
                f"{name}: {line.work_code} hours={line.hours} > {MAX_SINGLE_TASK_HOURS}"
            )


# ===========================================================================
# 4. SCALING TESTS -- monotonic: more input -> more hours
# ===========================================================================

class TestScaling:
    """Verify that increasing input size increases output hours."""

    def test_more_sf_more_hours_monument(self):
        r_small = estimate_monument(_monument_job(sf_per_face=10.0))
        r_large = estimate_monument(_monument_job(sf_per_face=40.0))
        assert r_large.total_man_hours > r_small.total_man_hours

    def test_more_sf_more_hours_pylon(self):
        r_small = estimate_pylon(_pylon_job(sf_per_face=15.0))
        r_large = estimate_pylon(_pylon_job(sf_per_face=60.0))
        assert r_large.total_man_hours > r_small.total_man_hours

    def test_more_sf_more_hours_polnon(self):
        r_small = estimate_pylon(_polnon_job(sf_per_face=15.0))
        r_large = estimate_pylon(_polnon_job(sf_per_face=60.0))
        assert r_large.total_man_hours > r_small.total_man_hours

    def test_more_sf_more_hours_cabinet(self):
        r_small = estimate_cabinet(_cabinet_job(sf_per_face=10.0))
        r_large = estimate_cabinet(_cabinet_job(sf_per_face=40.0))
        assert r_large.total_man_hours > r_small.total_man_hours

    def test_more_sf_more_hours_awning(self):
        r_small = estimate_awning(_awning_job(10.0))
        r_large = estimate_awning(_awning_job(60.0))
        assert r_large.total_man_hours > r_small.total_man_hours

    def test_more_letters_more_hours_channel(self):
        r_few = estimate(_channel_job(letter_count=5))
        r_many = estimate(_channel_job(letter_count=20))
        assert r_many.total_man_hours > r_few.total_man_hours

    def test_double_face_gt_single_face_monument(self):
        r_sf = estimate_monument(_monument_job(sf_per_face=20.0, num_faces=1))
        r_df = estimate_monument(_monument_job(sf_per_face=20.0, num_faces=2))
        assert r_df.total_man_hours > r_sf.total_man_hours
