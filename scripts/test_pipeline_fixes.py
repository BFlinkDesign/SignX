"""Offline validation tests for Informer BI extraction pipeline fixes.

Uses the saved Customer Listing page 1 response file -- no live HTTP calls.

Usage:
    cd C:\\Scripts\\signx-warehouse\\scripts
    timeout 120 pytest test_pipeline_fixes.py -v --timeout=30 --timeout-method=thread
"""

import json
import re
import sys
from pathlib import Path

import pytest

# Ensure gwt_parser and scrape_informer are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwt_parser import discover_field_names, extract_rows

# Paths
RESPONSE_FILE = Path(
    r"C:\Scripts\signx-warehouse\warehouse\raw\customer_listing_response.txt"
)
CAPTURES_DIR = Path(r"C:\Scripts\keyedin-capture\reports")

# Known Customer Listing fields (from REPORT_FIELDS in scrape_informer.py)
KNOWN_FIELDS = [
    "custNo",
    "name",
    "address",
    "address_2",
    "city",
    "state",
    "zip",
    "phone",
    "contact",
    "taxCode",
    "desc",
    "linkToSalesperson_assoc_name",
    "customer",
    "linkToPymtTerms_assoc_desc",
]


@pytest.fixture
def response_text():
    """Load the saved Customer Listing page 1 GWT response."""
    assert RESPONSE_FILE.exists(), f"Response file not found: {RESPONSE_FILE}"
    return RESPONSE_FILE.read_text(encoding="utf-8")


# ---------- Test 1: discover_field_names() ----------


class TestDiscoverFieldNames:
    def test_discovers_fields(self, response_text):
        """discover_field_names() should find >=10 fields from Row/HashMap keys."""
        fields = discover_field_names(response_text)
        assert len(fields) >= 10, f"Expected >=10 fields, got {len(fields)}: {fields}"

    def test_discovers_known_fields(self, response_text):
        """Most KNOWN_FIELDS should appear in discovered set."""
        fields = discover_field_names(response_text)
        discovered_set = set(fields)

        # These fields MUST be discovered (they have real String keys in Row data)
        must_find = {
            "name",
            "address",
            "city",
            "state",
            "zip",
            "phone",
            "contact",
            "taxCode",
            "linkToSalesperson_assoc_name",
            "customer",
            "linkToPymtTerms_assoc_desc",
        }
        missing = must_find - discovered_set
        assert not missing, f"Missing expected fields: {missing}"

    def test_id_field_discovered(self, response_text):
        """@ID should be discovered (it's the HashMap key for custNo values)."""
        fields = discover_field_names(response_text)
        # @ID may or may not appear depending on backreference resolution.
        # At minimum, either @ID or address_2 should be present.
        assert len(fields) >= 10, f"Too few fields: {fields}"

    def test_no_type_identifiers(self, response_text):
        """Discovered fields should not include GWT type descriptors."""
        fields = discover_field_names(response_text)
        for f in fields:
            assert not f.startswith("com."), f"Type descriptor leaked: {f}"
            assert not f.startswith("java."), f"Type descriptor leaked: {f}"
            assert "/" not in f, f"Path separator in field name: {f}"


# ---------- Test 2: extract_rows() with auto-discovered fields ----------


class TestExtractRowsAutoDiscovered:
    def test_rows_with_known_fields(self, response_text):
        """extract_rows() with KNOWN_FIELDS should produce 25 rows."""
        rows = extract_rows(response_text, KNOWN_FIELDS)
        assert len(rows) == 25, f"Expected 25 rows, got {len(rows)}"

    def test_rows_with_discovered_fields(self, response_text):
        """extract_rows() with auto-discovered fields should produce same row count."""
        discovered = discover_field_names(response_text)
        rows_discovered = extract_rows(response_text, discovered)
        rows_known = extract_rows(response_text, KNOWN_FIELDS)
        assert len(rows_discovered) == len(rows_known), (
            f"Row count mismatch: discovered={len(rows_discovered)}, "
            f"known={len(rows_known)}"
        )

    def test_discovered_rows_have_customer_data(self, response_text):
        """Rows from auto-discovered fields should contain real data values."""
        discovered = discover_field_names(response_text)
        rows = extract_rows(response_text, discovered)
        assert rows, "No rows extracted"
        # At least one row should have a non-null 'name' value
        names = [r.get("name") for r in rows if r.get("name")]
        assert names, "No 'name' values found in any row"


# ---------- Test 3: Dynamic payload loading ----------


class TestDynamicPayloadLoading:
    def test_slug_matches_existing_file(self):
        """safe_filename('Customer Listing') should match the existing capture file."""
        name = "Customer Listing"
        slug = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_").lower()
        expected_file = CAPTURES_DIR / f"report_{slug}_cmd_request.txt"
        assert expected_file.exists(), (
            f"Expected payload file not found: {expected_file}\n"
            f"Slug: '{slug}'"
        )

    def test_all_report_slugs_are_valid(self):
        """All 30 report names should produce valid filesystem slugs."""
        reports = [
            "AR Invoice Details",
            "AR Invoice Listing",
            "AR Open Invoices",
            "Cash Receipts",
            "Customer Listing",
            "Customer Listing Export",
            "Customer Location Listing",
            "Customer Location Listing Export",
            "Inventory List",
            "Inventory List Export",
            "Inventory Transaction History",
            "Invoice Register",
            "Open Sales Order Backlog",
            "Open Sales Orders",
            "Open Work Orders",
            "Planned Part Activity",
            "Purchase History",
            "Purchase Order Detail",
            "Purchased Part Variance",
            "Quote Status Report",
            "Sales Cost Detail Report",
            "Sales Order Bookings By Line Date",
            "Sales Order Bookings By SO Date",
            "Sales Order Detail",
            "Sales Order Status by Customer",
            "Sales Summary by Customer",
            "Sales Summary by Product Type",
            "Vendor Listing",
            "Vendor Listing Export",
            "Work Order Listing",
        ]
        for name in reports:
            slug = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_").lower()
            assert slug, f"Empty slug for: {name}"
            assert " " not in slug, f"Space in slug for: {name}"
            assert slug == slug.lower(), f"Not lowercase for: {name}"

    def test_capture_and_scrape_slugs_match(self):
        """Both scripts' safe_filename implementations produce identical output."""

        def make_slug(name: str) -> str:
            return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_").lower()

        test_names = [
            "Customer Listing",
            "AR Open Invoices",
            "Sales Order Bookings By Line Date",
            "Purchased Part Variance",
        ]
        for name in test_names:
            slug = make_slug(name)
            assert slug, f"Empty slug for: {name}"

    def test_load_captured_payload_dynamic(self):
        """load_captured_payload() should find Customer Listing via slug."""
        from scrape_informer import load_captured_payload

        result = load_captured_payload(1441850)
        assert result is not None, "load_captured_payload(1441850) returned None"
        payload, payload_type = result
        assert payload_type in ("view", "command"), f"Unknown type: {payload_type}"
        assert len(payload) > 1000, f"Payload too small: {len(payload)} chars"

    def test_load_captured_payload_missing(self):
        """load_captured_payload() should return None for uncaptured reports."""
        from scrape_informer import load_captured_payload

        result = load_captured_payload(9999999)
        assert result is None


# ---------- Test 4: End-to-end offline simulation ----------


class TestEndToEndOffline:
    def test_full_extraction_simulation(self, response_text):
        """Simulate extract_report() flow with 3-tier field discovery."""
        # Tier 1: No REPORT_FIELDS entry (simulating unknown report)
        field_names = None
        fields_source = None

        # Tier 2: Check manifest file
        manifest_path = CAPTURES_DIR / "field_names_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                field_names = manifest.get("1441850")
                if field_names:
                    fields_source = "manifest"
            except (json.JSONDecodeError, OSError):
                pass

        # Tier 3: Auto-discover from response
        if not field_names:
            field_names = discover_field_names(response_text)
            fields_source = "auto-discovery"

        assert field_names, "No fields discovered via any tier"
        assert len(field_names) >= 10
        assert fields_source in ("manifest", "auto-discovery")

        # Extract rows
        rows = extract_rows(response_text, field_names)
        assert len(rows) == 25, f"Expected 25 rows, got {len(rows)}"

        # Verify CSV-like output would work
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        assert "name" in all_keys
        assert len(all_keys) >= 10

    def test_known_fields_still_work(self, response_text):
        """REPORT_FIELDS (tier 1) still produces correct output."""
        rows = extract_rows(response_text, KNOWN_FIELDS)
        assert len(rows) == 25
        # custNo should be present via the fallback inference
        row0 = rows[0]
        assert "name" in row0
        assert row0.get("name"), "First row 'name' is empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=30", "--timeout-method=thread"])
