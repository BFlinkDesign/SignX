"""
test_sign_types.py -- Unit tests for the sign_types.py canonical taxonomy module.

Covers:
  - SIGN_TYPE_ALIASES completeness and structure
  - expand_sign_type() for group names, member codes, and unknowns
  - sign_type_label() human-friendly formatting
  - find_warehouse_csv() / find_quote_csv() path resolution
  - No duplicate codes across groups
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sign_types import (
    FILENAME_TYPE_MAP,
    SIGN_TYPE_ALIASES,
    WAREHOUSE_CSV_PATHS,
    WAREHOUSE_DB_PATHS,
    QUOTE_CSV_PATHS,
    expand_sign_type,
    find_quote_csv,
    find_warehouse_csv,
    find_warehouse_db,
    sign_type_label,
)


# -- SIGN_TYPE_ALIASES structure -----------------------------------------------

def test_aliases_is_nonempty_dict():
    """SIGN_TYPE_ALIASES contains at least 20 sign type groups."""
    assert isinstance(SIGN_TYPE_ALIASES, dict)
    assert len(SIGN_TYPE_ALIASES) >= 20, (
        f"Expected >= 20 sign type groups, got {len(SIGN_TYPE_ALIASES)}"
    )


def test_aliases_values_are_nonempty_lists():
    """Every alias group maps to a non-empty list of code strings."""
    for group, codes in SIGN_TYPE_ALIASES.items():
        assert isinstance(codes, list), f"{group}: expected list, got {type(codes)}"
        assert len(codes) > 0, f"{group}: empty code list"
        for code in codes:
            assert isinstance(code, str), f"{group}: code {code!r} is not a string"
            assert code == code.upper(), f"{group}: code {code!r} should be uppercase"


def test_no_duplicate_codes_across_groups():
    """Each warehouse code appears in exactly one group (no overlaps)."""
    seen: dict[str, str] = {}
    for group, codes in SIGN_TYPE_ALIASES.items():
        for code in codes:
            if code in seen:
                pytest.fail(
                    f"Code {code!r} appears in both {seen[code]!r} and {group!r}"
                )
            seen[code] = group


def test_core_sign_types_present():
    """Key sign type groups are present in the taxonomy."""
    required = [
        "CHANNEL_LETTER", "MONUMENT", "PYLON", "CABINET",
        "AWNING", "DIRECTIONAL", "DIMENSIONAL", "REMOVAL",
    ]
    for group in required:
        assert group in SIGN_TYPE_ALIASES, f"Missing core group: {group}"


def test_channel_letter_codes():
    """CHANNEL_LETTER contains CLLIT, CLNON, CHANNL."""
    codes = SIGN_TYPE_ALIASES["CHANNEL_LETTER"]
    for expected in ("CLLIT", "CLNON", "CHANNL"):
        assert expected in codes, f"CHANNEL_LETTER missing {expected}"


def test_total_code_count():
    """Total number of unique codes across all groups is >= 50."""
    all_codes = set()
    for codes in SIGN_TYPE_ALIASES.values():
        all_codes.update(codes)
    assert len(all_codes) >= 50, (
        f"Expected >= 50 total codes, got {len(all_codes)}"
    )


# -- expand_sign_type() -------------------------------------------------------

def test_expand_group_name():
    """expand_sign_type('CHANNEL_LETTER') returns all channel letter codes."""
    result = expand_sign_type("CHANNEL_LETTER")
    assert "CLLIT" in result
    assert "CLNON" in result
    assert "CHANNL" in result
    assert "CHANNEL_LETTER" in result  # group name included


def test_expand_member_code():
    """expand_sign_type('CLLIT') returns all channel letter codes."""
    result = expand_sign_type("CLLIT")
    assert "CLLIT" in result
    assert "CLNON" in result
    assert "CHANNL" in result


def test_expand_unknown_code():
    """expand_sign_type('XYZUNK') returns a set with just that code."""
    result = expand_sign_type("XYZUNK")
    assert result == {"XYZUNK"}


def test_expand_case_insensitive():
    """expand_sign_type is case-insensitive."""
    result_upper = expand_sign_type("CLLIT")
    result_lower = expand_sign_type("cllit")
    result_mixed = expand_sign_type("ClLiT")
    assert result_upper == result_lower == result_mixed


def test_expand_strips_whitespace():
    """expand_sign_type strips leading/trailing whitespace."""
    result = expand_sign_type("  CLLIT  ")
    assert "CLLIT" in result
    assert "CLNON" in result


def test_expand_monument():
    """expand_sign_type('MONDF') returns both monument codes."""
    result = expand_sign_type("MONDF")
    assert "MONDF" in result
    assert "MONSF" in result


def test_expand_pylon():
    """expand_sign_type('POLLIT') returns both pylon codes."""
    result = expand_sign_type("POLLIT")
    assert "POLLIT" in result
    assert "POLNON" in result


def test_expand_returns_set():
    """expand_sign_type always returns a set."""
    assert isinstance(expand_sign_type("CLLIT"), set)
    assert isinstance(expand_sign_type("UNKNOWN"), set)
    assert isinstance(expand_sign_type("CHANNEL_LETTER"), set)


# -- sign_type_label() --------------------------------------------------------

def test_label_from_code():
    """sign_type_label('CLLIT') returns 'Channel Letter'."""
    assert sign_type_label("CLLIT") == "Channel Letter"


def test_label_from_group_name():
    """sign_type_label('CHANNEL_LETTER') returns 'Channel Letter'."""
    assert sign_type_label("CHANNEL_LETTER") == "Channel Letter"


def test_label_monument():
    """sign_type_label('MONDF') returns 'Monument'."""
    assert sign_type_label("MONDF") == "Monument"


def test_label_pylon():
    """sign_type_label('POLLIT') returns 'Pylon'."""
    assert sign_type_label("POLLIT") == "Pylon"


def test_label_unknown_returns_original():
    """sign_type_label('FOOBAR') returns 'FOOBAR' unchanged."""
    assert sign_type_label("FOOBAR") == "FOOBAR"


def test_label_case_insensitive():
    """sign_type_label is case-insensitive."""
    assert sign_type_label("cllit") == "Channel Letter"
    assert sign_type_label("Cllit") == "Channel Letter"


def test_label_post_and_panel():
    """sign_type_label for POST_AND_PANEL group."""
    assert sign_type_label("P&P") == "Post And Panel"


# -- find_warehouse_csv() / find_quote_csv() / find_warehouse_db() ─────────────

def test_find_warehouse_csv_returns_path_or_none():
    """find_warehouse_csv() returns a Path or None (never raises)."""
    result = find_warehouse_csv()
    assert result is None or isinstance(result, Path)


def test_find_quote_csv_returns_path_or_none():
    """find_quote_csv() returns a Path or None (never raises)."""
    result = find_quote_csv()
    assert result is None or isinstance(result, Path)


def test_find_warehouse_db_returns_path_or_none():
    """find_warehouse_db() returns a Path or None (never raises)."""
    result = find_warehouse_db()
    assert result is None or isinstance(result, Path)


def test_warehouse_csv_paths_are_paths():
    """WAREHOUSE_CSV_PATHS entries are all Path objects."""
    for p in WAREHOUSE_CSV_PATHS:
        assert isinstance(p, Path), f"Expected Path, got {type(p)}: {p}"


def test_quote_csv_paths_are_paths():
    """QUOTE_CSV_PATHS entries are all Path objects."""
    for p in QUOTE_CSV_PATHS:
        assert isinstance(p, Path), f"Expected Path, got {type(p)}: {p}"


def test_warehouse_db_paths_are_paths():
    """WAREHOUSE_DB_PATHS entries are all Path objects."""
    for p in WAREHOUSE_DB_PATHS:
        assert isinstance(p, Path), f"Expected Path, got {type(p)}: {p}"


def test_env_override_warehouse(tmp_path):
    """SIGNX_WAREHOUSE_CSV env var adds a path to search list."""
    fake_csv = tmp_path / "test_warehouse.csv"
    fake_csv.write_text("header\n")
    with patch.dict(os.environ, {"SIGNX_WAREHOUSE_CSV": str(fake_csv)}):
        # Re-import to pick up env var (test the _env_or_default logic)
        from sign_types import _env_or_default
        paths = _env_or_default("SIGNX_WAREHOUSE_CSV", [])
        assert Path(str(fake_csv)) in paths


def test_env_override_quote(tmp_path):
    """SIGNX_QUOTE_CSV env var adds a path to search list."""
    fake_csv = tmp_path / "test_quote.csv"
    fake_csv.write_text("header\n")
    with patch.dict(os.environ, {"SIGNX_QUOTE_CSV": str(fake_csv)}):
        from sign_types import _env_or_default
        paths = _env_or_default("SIGNX_QUOTE_CSV", [])
        assert Path(str(fake_csv)) in paths


# -- Cross-module integration sanity -------------------------------------------

def test_expand_all_groups_no_crash():
    """expand_sign_type works for every group name without raising."""
    for group in SIGN_TYPE_ALIASES:
        result = expand_sign_type(group)
        # Group name is always included; single-code groups where
        # group name == code (e.g. DESIGN: ["DESIGN"]) produce len=1
        assert len(result) >= 1, (
            f"expand_sign_type({group!r}) returned empty set"
        )


def test_expand_all_codes_no_crash():
    """expand_sign_type works for every individual code without raising."""
    for group, codes in SIGN_TYPE_ALIASES.items():
        for code in codes:
            result = expand_sign_type(code)
            assert code in result, f"expand_sign_type({code!r}) doesn't include itself"
            # Single-member groups (e.g. DIRECTIONAL: ["DIRECT"]) return len=1
            assert len(result) >= 1, (
                f"expand_sign_type({code!r}) returned empty set"
            )


def test_label_all_codes_no_crash():
    """sign_type_label works for every code without raising."""
    for group, codes in SIGN_TYPE_ALIASES.items():
        expected_label = group.replace("_", " ").title()
        for code in codes:
            label = sign_type_label(code)
            assert label == expected_label, (
                f"sign_type_label({code!r}): expected {expected_label!r}, got {label!r}"
            )


# -- FILENAME_TYPE_MAP ---------------------------------------------------------

def test_filename_type_map_is_nonempty():
    """FILENAME_TYPE_MAP contains filename keyword -> estimator type entries."""
    assert isinstance(FILENAME_TYPE_MAP, dict)
    assert len(FILENAME_TYPE_MAP) >= 20, (
        f"Expected >= 20 filename type entries, got {len(FILENAME_TYPE_MAP)}"
    )


def test_filename_type_map_keys_lowercase():
    """All FILENAME_TYPE_MAP keys are lowercase."""
    for key in FILENAME_TYPE_MAP:
        assert key == key.lower(), f"Key {key!r} should be lowercase"


def test_filename_type_map_covers_core_types():
    """FILENAME_TYPE_MAP values include core estimator types."""
    values = set(FILENAME_TYPE_MAP.values())
    for expected in ("monument", "pylon", "channel_letter", "cabinet", "awning",
                     "directional", "dimensional", "removal"):
        assert expected in values, f"Missing estimator type: {expected}"


def test_filename_type_map_shared_with_drawing_search():
    """drawing_search.py uses the same FILENAME_TYPE_MAP from sign_types.py."""
    from drawing_search import FILENAME_TYPE_MAP as ds_map
    assert ds_map is FILENAME_TYPE_MAP, (
        "drawing_search.FILENAME_TYPE_MAP should be the same object as sign_types.FILENAME_TYPE_MAP"
    )


def test_filename_type_map_shared_with_project_files():
    """project_files.py uses the same FILENAME_TYPE_MAP from sign_types.py."""
    from project_files import SIGN_TYPE_MAP as pf_map
    assert pf_map is FILENAME_TYPE_MAP, (
        "project_files.SIGN_TYPE_MAP should be the same object as sign_types.FILENAME_TYPE_MAP"
    )
