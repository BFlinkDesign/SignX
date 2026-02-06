"""Dump raw data around each Row position to understand the serialization pattern."""

import json
import re
import sys
from pathlib import Path


def parse_response(text):
    text = text.strip()
    inner = text[4:]
    st_start = inner.rfind(',["')
    bracket_pos = st_start + 1
    depth = 0
    i = bracket_pos
    st_end = -1
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

    st_raw = inner[bracket_pos : st_end + 1]
    st_unescaped = re.sub(r"\\x([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), st_raw)
    strings = json.loads(st_unescaped)

    data_raw = inner[1 : st_start]
    if data_raw.endswith(","):
        data_raw = data_raw[:-1]

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

    return tokens, strings


def _coerce(token):
    if not token:
        return None
    if token.startswith("'") and token.endswith("'"):
        return token
    if "E" in token or "e" in token or "." in token:
        try:
            return float(token)
        except ValueError:
            pass
    try:
        return int(token)
    except ValueError:
        return token


def annotate(val, strings, field_names):
    """Return annotation for a data value."""
    if isinstance(val, int) and val > 0 and val <= len(strings):
        s = strings[val - 1]
        if "/" in s and ("com." in s or "java." in s or "[L" in s):
            return f"TYPE:{s.split('/')[0].split('.')[-1]}"
        if s in field_names:
            return f"FIELD:{s}"
        return f"STR:{s!r:.40}"
    if isinstance(val, int) and val < 0:
        return f"BACKREF(#{-val})"
    if val == 0:
        return "NULL"
    if isinstance(val, float):
        return f"FLOAT:{val}"
    if isinstance(val, str):
        return f"INLINE:{val}"
    return ""


if __name__ == "__main__":
    data, strings = parse_response(
        Path(r"C:\Scripts\signx-warehouse\warehouse\raw\customer_listing_response.txt")
        .read_text(encoding="utf-8")
    )

    field_names = {
        "custNo", "name", "address", "address_2", "city", "state", "zip",
        "phone", "contact", "taxCode", "desc", "linkToSalesperson_assoc_name",
        "customer", "linkToPymtTerms_assoc_desc",
    }

    # Key type refs
    type_refs = {}
    for i, s in enumerate(strings):
        if "/" in s:
            short = s.split("/")[0].split(".")[-1]
            type_refs[short] = i + 1

    ROW_REF = type_refs.get("Row", 0)
    row_positions = [i for i, v in enumerate(data) if v == ROW_REF]

    print(f"Data: {len(data)} tokens, Strings: {len(strings)}")
    print(f"Row positions ({len(row_positions)}): {row_positions}")
    print(f"Key type refs: Row={ROW_REF}, HashMap={type_refs.get('HashMap')}, "
          f"String={type_refs.get('String')}, StringValue={type_refs.get('StringValue')}, "
          f"NumberValue={type_refs.get('NumberValue')}, NullValue={type_refs.get('NullValue')}, "
          f"Double={type_refs.get('Double')}, ArrayValue={type_refs.get('ArrayValue')}")
    print()

    # Dump data around first 3 Row positions (reading right-to-left)
    for row_idx, row_pos in enumerate(row_positions[:3]):
        print(f"=== Row {row_idx} at data pos {row_pos} ===")
        # Show data from row_pos going LEFT (which is how the client reads)
        start = max(0, row_pos - 55)
        end = row_pos + 1
        print(f"Reading right-to-left from pos {row_pos} to {start}:")
        for i in range(end - 1, start - 1, -1):
            val = data[i]
            ann = annotate(val, strings, field_names)
            marker = " <<<" if i == row_pos else ""
            print(f"  [{i:4d}] {val!r:>12}  {ann}{marker}")
        print()

    # Also dump the LAST row
    if len(row_positions) > 3:
        last_pos = row_positions[-1]
        print(f"=== Last Row at data pos {last_pos} ===")
        start = max(0, last_pos - 55)
        for i in range(last_pos, start - 1, -1):
            val = data[i]
            ann = annotate(val, strings, field_names)
            marker = " <<<" if i == last_pos else ""
            print(f"  [{i:4d}] {val!r:>12}  {ann}{marker}")
