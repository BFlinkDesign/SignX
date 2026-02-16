"""Parse saved Informer GWT-RPC report responses to extract names and columns."""
import re
import os
import json

report_dir = r"C:\Users\Brady.EAGLE\Desktop\SignX\SignX-Intake\recon\responses\informer_reports"
reports = {}

for f in sorted(os.listdir(report_dir)):
    if not f.startswith("report_") or not f.endswith(".txt"):
        continue
    report_id = f.replace("report_", "").replace(".txt", "")
    filepath = os.path.join(report_dir, f)

    with open(filepath, "r", errors="replace") as fh:
        resp = fh.read()

    if not resp.startswith("//OK"):
        reports[report_id] = {"status": "ERROR", "size": len(resp)}
        continue

    # Extract string table from GWT-RPC response
    m = re.search(r'\["((?:[^"\\]|\\.)*)"', resp)
    if not m:
        reports[report_id] = {"status": "PARSE_ERROR", "size": len(resp)}
        continue

    # Find the last [...] in the response which is the string table
    bracket_start = resp.rfind('["')
    if bracket_start < 0:
        reports[report_id] = {"status": "NO_STRINGS", "size": len(resp)}
        continue

    bracket_end = resp.find("]", bracket_start)
    string_section = resp[bracket_start : bracket_end + 1]
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', string_section)

    report_name = None
    report_columns = []

    for s in strings:
        # Skip Java class names, base64, etc
        if s.startswith("com.") or s.startswith("java.") or s.startswith("[L"):
            continue
        if s.startswith("rO0") or "/" in s:
            continue
        if s.startswith("{"):
            continue

        # Look for column names (ALL CAPS with dots)
        if re.match(r"^[A-Z][A-Z0-9_.]+$", s) and 2 < len(s) < 30:
            report_columns.append(s)

    # Find report name - look for strings with spaces that look like titles
    for s in strings:
        if (
            5 < len(s) < 80
            and " " in s
            and s[0].isupper()
            and not s.startswith("com.")
            and not s.startswith("java.")
            and "/" not in s
            and not s.startswith("rO0")
            and not s.startswith("G*")
            and not s.startswith("font-")
        ):
            report_name = s
            break

    if not report_name:
        # Try any capitalized string
        for s in reversed(strings):
            if (
                3 < len(s) < 60
                and s[0].isupper()
                and not s.startswith("com.")
                and not s.startswith("java.")
                and "/" not in s
                and not s.startswith("rO0")
            ):
                report_name = s
                break

    reports[report_id] = {
        "name": report_name or "Unknown",
        "size": len(resp),
        "columns": report_columns[:20],
        "num_strings": len(strings),
    }

# Print summary
print("INFORMER REPORT INVENTORY")
print("=" * 80)
for rid in sorted(reports.keys()):
    r = reports[rid]
    if "name" in r:
        cols = ", ".join(r.get("columns", [])[:8])
        extra = f", +{len(r['columns']) - 8} more" if len(r.get("columns", [])) > 8 else ""
        print(f"  {rid}: {r['name']} ({r['size']:,} chars)")
        if cols:
            print(f"           Columns: {cols}{extra}")
    else:
        print(f"  {rid}: {r.get('status', '?')}")

# Save full inventory
outpath = r"C:\Users\Brady.EAGLE\Desktop\SignX\SignX-Intake\recon\informer_report_inventory.json"
with open(outpath, "w") as f:
    json.dump(reports, f, indent=2)
print(f"\nSaved to {outpath}")
