"""Diagnostic: Analyze GWT RPC response structure to understand Row serialization."""

import json
import re
import sys
from pathlib import Path


def parse_response(text: str):
    """Parse GWT response into data array and string table."""
    text = text.strip()
    if not text.startswith("//OK"):
        raise ValueError("Not a //OK response")

    inner = text[4:]  # strip //OK

    # Find string table: last ["..."] array
    st_start = inner.rfind(',["')
    if st_start == -1:
        raise ValueError("No string table found")

    bracket_pos = st_start + 1
    depth = 0
    i = bracket_pos
    while i < len(inner):
        ch = inner[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                st_end = i
                break
        elif ch == '"':
            i += 1
            while i < len(inner) and inner[i] != '"':
                if inner[i] == "\\":
                    i += 1
                i += 1
        i += 1

    # Parse string table
    st_raw = inner[bracket_pos : st_end + 1]
    # Unescape GWT hex escapes for JSON parsing
    st_unescaped = re.sub(
        r"\\x([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), st_raw
    )
    strings = json.loads(st_unescaped)

    # Parse data values (everything before string table)
    data_raw = inner[1 : st_start]  # skip outer [, up to comma before string table
    if data_raw.endswith(","):
        data_raw = data_raw[:-1]

    # Parse tokens - handle inline quoted strings and numbers
    tokens = []
    current = ""
    in_quote = False
    for ch in data_raw:
        if ch == "'" and not in_quote:
            in_quote = True
            current += ch
        elif ch == "'" and in_quote:
            in_quote = False
            current += ch
        elif ch == "," and not in_quote:
            t = current.strip()
            if t:
                tokens.append(_coerce(t))
            current = ""
        else:
            current += ch
    t = current.strip()
    if t:
        tokens.append(_coerce(t))

    # Trailer after string table
    trailer = inner[st_end + 1 :].rstrip("]").lstrip(",")
    trailer_parts = [p.strip() for p in trailer.split(",") if p.strip()]

    return {
        "data": tokens,
        "strings": strings,
        "trailer": trailer_parts,
    }


def _coerce(token):
    if not token:
        return None
    if token.startswith("'") and token.endswith("'"):
        return token  # inline string
    if "E" in token or "e" in token or "." in token:
        try:
            return float(token)
        except ValueError:
            pass
    try:
        return int(token)
    except ValueError:
        return token


def analyze(parsed):
    data = parsed["data"]
    strings = parsed["strings"]

    print(f"Data tokens: {len(data)}")
    print(f"String table entries: {len(strings)}")
    print(f"Trailer: {parsed['trailer']}")
    print()

    # Build type index
    type_index = {}
    for i, s in enumerate(strings):
        if "/" in s and ("com." in s or "java." in s or "[L" in s):
            short = s.split("/")[0].split(".")[-1]
            type_index[i] = short
            # Print key types
            if short in (
                "Row",
                "StringValue",
                "NumberValue",
                "NullValue",
                "ArrayValue",
                "HashMap",
                "ViewPage",
                "ViewToken",
                "String",
                "Double",
                "ArrayList",
                "RunReportResult",
                "DataGroup",
            ):
                print(f"  Type [{i}] (ref {i+1}): {s}")

    print()

    # Find field names
    field_names = {
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
    }
    field_refs = {}
    for i, s in enumerate(strings):
        if s in field_names:
            field_refs[i + 1] = s  # 1-based ref
            print(f"  Field [{i}] (ref {i+1}): {s}")

    print()

    # Find data value strings (non-type, non-field, non-metadata)
    data_strings_start = None
    for i, s in enumerate(strings):
        if s in ("TACO", "100"):  # Known first data values
            data_strings_start = i
            break

    if data_strings_start:
        print(f"Data strings start at index {data_strings_start}")
        for i in range(data_strings_start, min(data_strings_start + 30, len(strings))):
            print(f"  [{i}] = {strings[i]!r}")

    print()

    # Key type refs (1-based)
    ROW_REF = None
    HASHMAP_REF = None
    STRVAL_REF = None
    NUMVAL_REF = None
    NULLVAL_REF = None
    ARRVAL_REF = None
    STRING_REF = None
    DOUBLE_REF = None

    for i, s in enumerate(strings):
        short = s.split("/")[0].split(".")[-1] if "/" in s else ""
        if short == "Row":
            ROW_REF = i + 1
        elif short == "HashMap" and "java.util" in s:
            HASHMAP_REF = i + 1
        elif short == "StringValue":
            STRVAL_REF = i + 1
        elif short == "NumberValue":
            NUMVAL_REF = i + 1
        elif short == "NullValue":
            NULLVAL_REF = i + 1
        elif short == "ArrayValue":
            ARRVAL_REF = i + 1
        elif s == "java.lang.String/2004016611":
            STRING_REF = i + 1
        elif s == "java.lang.Double/858496421":
            DOUBLE_REF = i + 1

    print(f"ROW_REF={ROW_REF}, HASHMAP_REF={HASHMAP_REF}")
    print(f"STRVAL_REF={STRVAL_REF}, NUMVAL_REF={NUMVAL_REF}, NULLVAL_REF={NULLVAL_REF}")
    print(f"ARRVAL_REF={ARRVAL_REF}")
    print(f"STRING_REF={STRING_REF}, DOUBLE_REF={DOUBLE_REF}")
    print()

    # Search for Row type ref in data
    row_positions = [i for i, v in enumerate(data) if v == ROW_REF]
    print(f"Row type ref ({ROW_REF}) found at {len(row_positions)} positions in data:")
    for pos in row_positions[:5]:
        context = data[max(0, pos - 3) : pos + 10]
        print(f"  pos {pos}: ...{context}...")
    if len(row_positions) > 5:
        print(f"  ... and {len(row_positions) - 5} more")
    print()

    # Search for HashMap ref near Row refs
    hashmap_positions = [i for i, v in enumerate(data) if v == HASHMAP_REF]
    print(f"HashMap type ref ({HASHMAP_REF}) found at {len(hashmap_positions)} positions")
    print()

    # Look at data around first Row ref
    if row_positions:
        first_row = row_positions[0]
        print(f"=== Data around first Row (pos {first_row}) ===")
        start = max(0, first_row - 5)
        end = min(len(data), first_row + 60)
        for i in range(start, end):
            val = data[i]
            annotation = ""
            if isinstance(val, int) and val > 0 and val <= len(strings):
                s = strings[val - 1]
                if "/" in s and ("com." in s or "java." in s):
                    short = s.split("/")[0].split(".")[-1]
                    annotation = f" → TYPE:{short}"
                elif s in field_names:
                    annotation = f" → FIELD:{s}"
                elif val - 1 >= data_strings_start and not ("com." in s or "java." in s):
                    annotation = f" → DATA:{s!r}"
            elif isinstance(val, int) and val < 0:
                annotation = f" → BACKREF(obj #{-val})"
            elif val == 0:
                annotation = " → NULL"
            if i == first_row:
                annotation += " <<<< ROW"
            print(f"  [{i:4d}] = {val!r}{annotation}")
        print()

    # Try to trace from beginning of data
    print("=== First 50 data tokens with annotations ===")
    for i in range(min(50, len(data))):
        val = data[i]
        annotation = ""
        if isinstance(val, int) and val > 0 and val <= len(strings):
            s = strings[val - 1]
            if "/" in s and ("com." in s or "java." in s):
                short = s.split("/")[0].split(".")[-1]
                annotation = f" → TYPE:{short}"
            elif s in field_names:
                annotation = f" → FIELD:{s}"
            elif not _is_type_string(s):
                annotation = f" → STR:{s!r}"
        elif isinstance(val, int) and val < 0:
            annotation = f" → BACKREF(obj #{-val})"
        elif val == 0:
            annotation = " → NULL"
        print(f"  [{i:4d}] = {val!r}{annotation}")
    print()

    # Try to trace from END of data (in case it's a stack)
    print("=== Last 60 data tokens with annotations ===")
    start_pos = max(0, len(data) - 60)
    for i in range(start_pos, len(data)):
        val = data[i]
        annotation = ""
        if isinstance(val, int) and val > 0 and val <= len(strings):
            s = strings[val - 1]
            if "/" in s and ("com." in s or "java." in s):
                short = s.split("/")[0].split(".")[-1]
                annotation = f" → TYPE:{short}"
            elif s in field_names:
                annotation = f" → FIELD:{s}"
            elif not _is_type_string(s):
                annotation = f" → STR:{s!r}"
        elif isinstance(val, int) and val < 0:
            annotation = f" → BACKREF(obj #{-val})"
        elif val == 0:
            annotation = " → NULL"
        print(f"  [{i:4d}] = {val!r}{annotation}")

    # Look for pattern: StringValue ref followed by data string ref
    print()
    print("=== StringValue patterns ===")
    sv_count = 0
    for i, v in enumerate(data):
        if v == STRVAL_REF and i + 1 < len(data):
            next_val = data[i + 1]
            if isinstance(next_val, int) and next_val > 0 and next_val <= len(strings):
                s = strings[next_val - 1]
                if not _is_type_string(s):
                    sv_count += 1
                    if sv_count <= 20:
                        # Check what's before (likely field name)
                        prev = ""
                        if i >= 2:
                            p = data[i - 1]
                            if isinstance(p, int) and p > 0 and p <= len(strings):
                                prev = strings[p - 1]
                            elif isinstance(p, int) and p < 0:
                                prev = f"backref({-p})"
                        if i >= 3:
                            pp = data[i - 2]
                            if isinstance(pp, int) and pp > 0 and pp <= len(strings):
                                pp_str = strings[pp - 1]
                                if pp_str in field_names:
                                    prev = f"{pp_str} → {prev}"
                        print(f"  pos {i}: StringValue → {s!r}  (before: {prev})")
    print(f"Total StringValue instances with data: {sv_count}")

    # Look for NumberValue patterns
    print()
    print("=== NumberValue patterns ===")
    nv_count = 0
    for i, v in enumerate(data):
        if v == NUMVAL_REF and i + 1 < len(data):
            next_val = data[i + 1]
            # NumberValue wraps a Double, which has its own type ref
            if next_val == DOUBLE_REF and i + 2 < len(data):
                double_val = data[i + 2]
                nv_count += 1
                if nv_count <= 10:
                    print(f"  pos {i}: NumberValue → Double → {double_val}")
            elif isinstance(next_val, (int, float)):
                nv_count += 1
                if nv_count <= 10:
                    print(f"  pos {i}: NumberValue → {next_val}")
    print(f"Total NumberValue instances: {nv_count}")

    # Look for sequences: field_ref, STRING_REF, field_value_ref, STRVAL_REF, data_ref
    # This would be: key=String("field"), value=StringValue(String("data"))
    print()
    print("=== Attempting key-value pair decode ===")
    pairs_found = 0
    for i in range(len(data) - 4):
        if data[i] == STRING_REF:  # java.lang.String type for key
            key_ref = data[i + 1]
            if isinstance(key_ref, int) and key_ref > 0 and key_ref <= len(strings):
                key_str = strings[key_ref - 1]
                if key_str in field_names:
                    val_type = data[i + 2] if i + 2 < len(data) else None
                    val_data = data[i + 3] if i + 3 < len(data) else None
                    val_str = ""
                    if val_type == STRVAL_REF and isinstance(val_data, int) and val_data > 0 and val_data <= len(strings):
                        val_str = strings[val_data - 1]
                    elif val_type == NULLVAL_REF:
                        val_str = "NULL"
                    pairs_found += 1
                    if pairs_found <= 30:
                        print(f"  pos {i}: String({key_str}) → type={val_type} data={val_data} = {val_str!r}")
    print(f"Total field key-value pairs found: {pairs_found}")


def _is_type_string(s):
    return any(
        s.startswith(p) for p in ("com.entrinsik.", "com.google.", "java.", "[L", "rO0AB")
    )


if __name__ == "__main__":
    response_file = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\customer_listing_response.txt")
    text = response_file.read_text(encoding="utf-8")
    parsed = parse_response(text)
    analyze(parsed)
