import types
from pathlib import Path

import pytest

import catscale_delta_parser as mod


@pytest.mark.parametrize(
    "text, expected_wo",
    [
        ("... WORK ORDER 12345 ...", "12345"),
        ("... WO # 67890 ...", "67890"),
        ("Order Number: 54321", "54321"),
    ],
)
def test_extract_page_header_work_order(text, expected_wo):
    header = mod.ProductionParser().extract_page_header(text)
    assert header.get("work_order") == expected_wo


@pytest.mark.parametrize(
    "text, expected_part",
    [
        ("Part Number: ABC-123", "ABC-123"),
        ("P/N: ZZ-9", "ZZ-9"),
        ("Item: X1", "X1"),
    ],
)
def test_extract_page_header_part_number(text, expected_part):
    header = mod.ProductionParser().extract_page_header(text)
    assert header.get("part_number") == expected_part


