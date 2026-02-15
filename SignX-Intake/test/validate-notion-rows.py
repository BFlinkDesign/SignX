"""
Notion Bid Pipeline Validation Script
Queries rows created in the last 30 minutes and validates extracted fields
against expected test email results.

Usage:
    python test/validate-notion-rows.py
    python test/validate-notion-rows.py --minutes 60  # extend search window
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
except ImportError:
    pass

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN not set. Add it to SignX-Intake/.env or set as env var.")
    sys.exit(1)
DATABASE_ID = "304c1e58d2dd814aae63c6a0d44e6679"
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

EXPECTED_RESULTS = [
    {
        "quote_name": "First National Bank EMC Monument",
        "customer": "First National Bank",
        "location": "Ankeny",
        "sign_type": "EMC_MONUMENT",
        "estimated_value": 85000,
        "pixel_pitch": 10,
        "is_redo": False,
        "faces": 2,
        "blocking": ["watchfire_pricing"],
    },
    {
        "quote_name": "Pancheros Ames Channel Letters",
        "customer": "Pancheros",
        "location": "Ames",
        "sign_type": "CHANNEL_LETTERS",
        "estimated_value": None,
        "is_redo": False,
        "blocking": [],
    },
    {
        "quote_name": "Kum & Go Removal 4th & Grand",
        "customer": "Kum & Go",
        "location": "Des Moines",
        "sign_type": "REMOVAL",
        "estimated_value": None,
        "is_redo": True,
        "blocking": [],
    },
]


def query_recent_pages(minutes: int = 30) -> list:
    """Query Notion DB for pages created in the last N minutes."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "filter": {
            "timestamp": "created_time",
            "created_time": {"on_or_after": cutoff},
        },
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
    }

    resp = requests.post(
        f"{NOTION_BASE_URL}/databases/{DATABASE_ID}/query",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def extract_property(page: dict, prop_name: str, prop_type: str):
    """Extract a property value from a Notion page object."""
    prop = page.get("properties", {}).get(prop_name)
    if not prop:
        return None

    if prop_type == "title":
        title_arr = prop.get("title", [])
        return title_arr[0]["plain_text"] if title_arr else None

    if prop_type == "rich_text":
        text_arr = prop.get("rich_text", [])
        return text_arr[0]["plain_text"] if text_arr else None

    if prop_type == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None

    if prop_type == "multi_select":
        return [ms["name"] for ms in prop.get("multi_select", [])]

    if prop_type == "number":
        return prop.get("number")

    if prop_type == "checkbox":
        return prop.get("checkbox")

    if prop_type == "date":
        date_obj = prop.get("date")
        return date_obj["start"] if date_obj else None

    return None


def extract_page_fields(page: dict) -> dict:
    """Extract all relevant fields from a Notion page."""
    return {
        "quote_name": extract_property(page, "Quote #", "title"),
        "customer": extract_property(page, "Customer", "rich_text"),
        "location": extract_property(page, "Location", "rich_text"),
        "sign_type": extract_property(page, "Sign Type", "select"),
        "estimated_value": extract_property(page, "Est. Value", "number"),
        "description": extract_property(page, "Description", "rich_text"),
        "cabinet_dims": extract_property(page, "Cabinet Dims", "rich_text"),
        "pixel_pitch": extract_property(page, "Pixel Pitch (mm)", "number"),
        "faces": extract_property(page, "Faces", "number"),
        "sq_ft": extract_property(page, "Sq Ft", "number"),
        "is_redo": extract_property(page, "Is Redo", "checkbox"),
        "blocking": extract_property(page, "Blocking", "multi_select"),
        "salesman": extract_property(page, "Salesman", "select"),
        "pipeline_stage": extract_property(page, "Pipeline Stage", "select"),
        "status": extract_property(page, "Status", "select"),
        "delivery_date": extract_property(page, "Delivery Date", "date"),
        "email_received": extract_property(page, "Email Received", "date"),
        "page_id": page.get("id"),
    }


def match_page_to_expected(page_fields: dict, expected: dict) -> bool:
    """Check if a Notion page matches an expected result by customer name."""
    page_customer = (page_fields.get("customer") or "").lower()
    expected_customer = (expected.get("customer") or "").lower()
    return expected_customer in page_customer


def validate_field(
    actual, expected, field_name: str, fuzzy_text: bool = False
) -> dict:
    """Validate a single field. Returns validation result dict."""
    if fuzzy_text and isinstance(actual, str) and isinstance(expected, str):
        passed = expected.lower() in actual.lower()
    elif isinstance(expected, list) and isinstance(actual, list):
        passed = set(expected) == set(actual)
    else:
        passed = actual == expected

    return {
        "field": field_name,
        "expected": expected,
        "actual": actual,
        "pass": passed,
    }


def validate_page(page_fields: dict, expected: dict) -> dict:
    """Validate a Notion page against expected values."""
    results = []

    # Validate fields that exist in the expected dict
    field_configs = {
        "quote_name": {"fuzzy": True},
        "customer": {"fuzzy": True},
        "location": {"fuzzy": True},
        "sign_type": {"fuzzy": False},
        "estimated_value": {"fuzzy": False},
        "pixel_pitch": {"fuzzy": False},
        "faces": {"fuzzy": False},
        "is_redo": {"fuzzy": False},
        "blocking": {"fuzzy": False},
    }

    for field, config in field_configs.items():
        if field in expected:
            results.append(
                validate_field(
                    page_fields.get(field),
                    expected[field],
                    field,
                    fuzzy_text=config["fuzzy"],
                )
            )

    # Always validate auto-set fields
    results.append(
        validate_field(page_fields.get("salesman"), "Jeff Fye", "salesman")
    )
    results.append(
        validate_field(
            page_fields.get("pipeline_stage"), "INTAKE", "pipeline_stage"
        )
    )

    expected_status = (
        "REDO BID REQUEST" if expected.get("is_redo") else "BID REQUEST"
    )
    results.append(
        validate_field(page_fields.get("status"), expected_status, "status")
    )

    all_passed = all(r["pass"] for r in results)
    return {
        "page_id": page_fields.get("page_id"),
        "quote_name": page_fields.get("quote_name"),
        "field_results": results,
        "pass": all_passed,
        "failures": [r for r in results if not r["pass"]],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate Notion bid pipeline rows against test emails"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=30,
        help="Search window in minutes (default: 30)",
    )
    args = parser.parse_args()

    print(f"Querying Notion for pages created in last {args.minutes} minutes...")

    try:
        pages = query_recent_pages(args.minutes)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Notion API returned {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Notion API. Check network.")
        sys.exit(1)

    print(f"Found {len(pages)} recent pages.\n")

    if not pages:
        print("No pages found in the search window.")
        print(f"Try: python {sys.argv[0]} --minutes 60")
        sys.exit(0)

    # Extract fields from all pages
    page_fields_list = [extract_page_fields(p) for p in pages]

    # Match and validate
    validation_results = []
    unmatched_expected = list(range(len(EXPECTED_RESULTS)))

    for expected_idx, expected in enumerate(EXPECTED_RESULTS):
        matched = False
        for pf in page_fields_list:
            if match_page_to_expected(pf, expected):
                result = validate_page(pf, expected)
                result["expected_email"] = expected.get("quote_name", "unknown")
                validation_results.append(result)
                if expected_idx in unmatched_expected:
                    unmatched_expected.remove(expected_idx)
                matched = True
                break

        if not matched:
            validation_results.append(
                {
                    "expected_email": expected.get("quote_name", "unknown"),
                    "pass": False,
                    "error": "No matching Notion page found",
                    "failures": [
                        {
                            "field": "page_exists",
                            "expected": True,
                            "actual": False,
                            "pass": False,
                        }
                    ],
                }
            )

    # Print results
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    total = len(validation_results)
    passed = sum(1 for r in validation_results if r["pass"])
    failed = total - passed

    for r in validation_results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"\n[{status}] {r.get('expected_email', 'unknown')}")
        if r.get("error"):
            print(f"  ERROR: {r['error']}")
        if r.get("failures"):
            for f in r["failures"]:
                print(
                    f"  FAIL: {f['field']} — expected={f['expected']}, actual={f['actual']}"
                )
        if r.get("field_results"):
            pass_count = sum(1 for fr in r["field_results"] if fr["pass"])
            print(
                f"  Fields: {pass_count}/{len(r['field_results'])} passed"
            )

    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {passed}/{total} test emails passed validation")
    if failed > 0:
        print(f"FAILURES: {failed} test email(s) need investigation")
    else:
        print("ALL TESTS PASSED — Phase 1 proof is validated!")
    print(f"{'=' * 70}")

    # Save results to JSON
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "recon",
        "validation-results.json",
    )
    output = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "search_window_minutes": args.minutes,
        "pages_found": len(pages),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "results": validation_results,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {output_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
