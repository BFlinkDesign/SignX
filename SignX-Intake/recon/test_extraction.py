"""
Test the bid-request extraction prompt against real sampled emails.
Calls Anthropic API with each email body and validates the output.

Usage:
    python recon/test_extraction.py
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
except ImportError:
    pass  # dotenv not required if env var is set directly

try:
    import anthropic
except ImportError:
    print("ERROR: 'anthropic' package required. Install with: pip install anthropic")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)

SYSTEM_PROMPT = """You are a bid request parser for Eagle Sign Co., a commercial sign manufacturer.
Extract project details from this bid request email. Return ONLY valid JSON, no markdown, no backticks.

{
  "quote_name": "short descriptive project name — used as the Notion title",
  "customer": "company or person name requesting the sign",
  "location": "city, state if mentioned, else null",
  "sign_type": one of: "EMC_MONUMENT", "EMC_POLE", "EMC_RETROFIT", "EMC", "CHANNEL_LETTERS", "CHANNEL_LOGO", "MONUMENT_BASE", "MONUMENT_MANUAL_READER", "CABINET_ILLUMINATED", "INFO_PANEL", "MASONRY_SUB", "REMOVAL", "STRUCTURAL_BASE", or null if unclear,
  "estimated_value": dollar amount as number if mentioned, else null,
  "description": "1-3 sentence summary of what they need",
  "sq_ft": number if sign dimensions mentioned (calculate from WxH), else null,
  "faces": number of sign faces if mentioned (typically 1 or 2), else null,
  "cabinet_dims": "W x H format if cabinet dimensions mentioned, else null",
  "pixel_pitch": number in mm if EMC pixel pitch mentioned, else null,
  "delivery_date": "YYYY-MM-DD if deadline mentioned, else null",
  "is_redo": true if this is a re-bid or revision of a previous quote, else false,
  "has_drawings": true if email mentions attached drawings/plans/specs,
  "has_specs": true if email mentions specifications document,
  "blocking": list from ["watchfire_pricing", "needs_drawings", "needs_specs", "masonry_sub_quote"] — include any that seem needed based on context, else []
}

Rules:
- If sign_type is unclear from the email, use null — don't guess.
- For EMC projects, try to extract pixel pitch from specs.
- "is_redo" = true ONLY if email explicitly references a previous quote number or says "re-bid" / "revise".
- estimated_value: only if the email states a budget or target price. Don't fabricate.
- MASONRY_SUB = project is primarily masonry/brick/stone work for a sign base
- REMOVAL = sign removal, demolition, or decommission job
- STRUCTURAL_BASE = structural foundation, pole, or mounting structure only (no sign fabrication)"""

VALID_SIGN_TYPES = [
    "EMC_MONUMENT", "EMC_POLE", "EMC_RETROFIT", "EMC",
    "CHANNEL_LETTERS", "CHANNEL_LOGO", "MONUMENT_BASE",
    "MONUMENT_MANUAL_READER", "CABINET_ILLUMINATED", "INFO_PANEL",
    "MASONRY_SUB", "REMOVAL", "STRUCTURAL_BASE",
    None,
]

VALID_BLOCKING = [
    "watchfire_pricing", "needs_drawings", "needs_specs", "masonry_sub_quote"
]


def load_email_samples() -> list:
    """Load sampled emails from email-samples.json."""
    samples_path = os.path.join(SCRIPT_DIR, "email-samples.json")
    with open(samples_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    emails = []
    for folder in data["folders"]:
        for sample in folder["samples"]:
            emails.append({
                "folder": folder["folder_name"],
                "subject": sample["subject"],
                "from": sample["from"],
                "received": sample["received"],
                "body": sample["body_preview"],
            })
    return emails


def call_anthropic(email: dict) -> str:
    """Call Anthropic API with the extraction prompt."""
    client = anthropic.Anthropic()

    user_content = (
        f"SALESPERSON: {email['folder']}\n"
        f"SUBJECT: {email['subject']}\n"
        f"FROM: {email['from']}\n"
        f"DATE: {email['received']}\n\n"
        f"EMAIL BODY:\n{email['body']}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    return response.content[0].text


def validate_extraction(extraction: dict) -> dict:
    """Validate an extraction result against the schema."""
    results = {
        "valid_json": True,
        "sign_type_valid": True,
        "blocking_valid": True,
        "value_type_valid": True,
        "date_format_valid": True,
        "required_fields_present": True,
        "issues": [],
    }

    # Check sign_type
    sign_type = extraction.get("sign_type")
    if sign_type not in VALID_SIGN_TYPES:
        results["sign_type_valid"] = False
        results["issues"].append(f"sign_type '{sign_type}' not in allowed enum")

    # Check blocking
    blocking = extraction.get("blocking", [])
    if not isinstance(blocking, list):
        results["blocking_valid"] = False
        results["issues"].append(f"blocking is not a list: {type(blocking)}")
    else:
        for item in blocking:
            if item not in VALID_BLOCKING:
                results["blocking_valid"] = False
                results["issues"].append(f"blocking item '{item}' not in allowed values")

    # Check estimated_value type
    est_value = extraction.get("estimated_value")
    if est_value is not None and not isinstance(est_value, (int, float)):
        results["value_type_valid"] = False
        results["issues"].append(f"estimated_value is {type(est_value)}, expected number or null")

    # Check delivery_date format
    delivery_date = extraction.get("delivery_date")
    if delivery_date is not None:
        try:
            datetime.strptime(delivery_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            results["date_format_valid"] = False
            results["issues"].append(f"delivery_date '{delivery_date}' not in YYYY-MM-DD format")

    # Check required fields
    required = ["quote_name", "customer", "description", "is_redo", "blocking"]
    for field in required:
        if field not in extraction:
            results["required_fields_present"] = False
            results["issues"].append(f"Missing required field: {field}")

    return results


def main():
    print("Loading email samples...")
    emails = load_email_samples()
    print(f"Found {len(emails)} emails to test.\n")

    tests = []
    passed_count = 0
    failed_count = 0
    failure_details = []

    for i, email in enumerate(emails, 1):
        print(f"[{i}/{len(emails)}] Testing: {email['subject'][:60]}...")

        try:
            raw_response = call_anthropic(email)
        except Exception as e:
            print(f"  API ERROR: {e}")
            tests.append({
                "email_subject": email["subject"],
                "folder": email["folder"],
                "extraction": None,
                "validation": {"valid_json": False, "issues": [str(e)]},
                "pass": False,
                "error": str(e),
            })
            failed_count += 1
            failure_details.append(f"{email['subject']}: API error - {e}")
            continue

        # Strip markdown code fences if present (Sonnet sometimes wraps despite instructions)
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # Try to parse JSON
        try:
            extraction = json.loads(cleaned)
            valid_json = True
        except json.JSONDecodeError as e:
            print(f"  JSON PARSE ERROR: {e}")
            print(f"  Raw response: {raw_response[:200]}")
            tests.append({
                "email_subject": email["subject"],
                "folder": email["folder"],
                "extraction": raw_response,
                "validation": {
                    "valid_json": False,
                    "issues": [f"Invalid JSON: {e}"],
                },
                "pass": False,
            })
            failed_count += 1
            failure_details.append(f"{email['subject']}: Invalid JSON response")
            continue

        # Validate extraction
        validation = validate_extraction(extraction)
        test_passed = all([
            validation["valid_json"],
            validation["sign_type_valid"],
            validation["blocking_valid"],
            validation["value_type_valid"],
            validation["date_format_valid"],
            validation["required_fields_present"],
        ])

        if test_passed:
            passed_count += 1
            print(f"  PASS - {extraction.get('quote_name', 'N/A')} | "
                  f"type={extraction.get('sign_type')} | "
                  f"value={extraction.get('estimated_value')}")
        else:
            failed_count += 1
            failure_details.append(
                f"{email['subject']}: {'; '.join(validation['issues'])}"
            )
            print(f"  FAIL - Issues: {', '.join(validation['issues'])}")

        tests.append({
            "email_subject": email["subject"],
            "folder": email["folder"],
            "extraction": extraction,
            "validation": validation,
            "pass": test_passed,
        })

    # Summary
    total = len(tests)
    failure_rate = (failed_count / total * 100) if total > 0 else 0

    print(f"\n{'=' * 70}")
    print(f"EXTRACTION TEST RESULTS")
    print(f"{'=' * 70}")
    print(f"Total:  {total}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Rate:   {100 - failure_rate:.1f}% pass")

    if failure_rate > 20:
        print(f"\nGATE FAILED: {failure_rate:.0f}% failure rate exceeds 20% threshold.")
        print("STOP: The extraction prompt needs tuning before Phase 1.")
    else:
        print(f"\nGATE PASSED: Failure rate {failure_rate:.0f}% is within 20% threshold.")

    if failure_details:
        print(f"\nFailure details:")
        for detail in failure_details:
            print(f"  - {detail}")

    # Save results
    output = {
        "tests": tests,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": failed_count,
            "failure_rate_pct": round(failure_rate, 1),
            "gate_passed": failure_rate <= 20,
            "failure_details": failure_details,
        },
        "tested_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = os.path.join(SCRIPT_DIR, "extraction-test-results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")

    sys.exit(0 if failure_rate <= 20 else 1)


if __name__ == "__main__":
    main()
