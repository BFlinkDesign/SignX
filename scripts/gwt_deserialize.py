"""GWT RPC v7 Response Deserializer.

Properly reads the GWT response data array RIGHT-TO-LEFT (matching the
client-side ClientSerializationStreamReader which uses --index).

The server writes tokens left-to-right, reverses them in the response encoding,
and the client reads from the end backward. This means:
  - readObject() first reads the TYPE ref (from current position, moving left)
  - Then reads FIELDS of that type (continuing leftward)
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Parse raw response into data array + string table
# ---------------------------------------------------------------------------

def parse_response(text: str) -> dict:
    text = text.strip()
    assert text.startswith("//OK"), "Not a //OK response"
    inner = text[4:]

    # Find string table
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
    st_unescaped = re.sub(
        r"\\x([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), st_raw
    )
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

    return {"data": tokens, "strings": strings}


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


# ---------------------------------------------------------------------------
# GWT Stream Reader (reads right-to-left)
# ---------------------------------------------------------------------------

class GwtStreamReader:
    """Reads GWT RPC v7 response data from right to left."""

    def __init__(self, data: list, strings: list[str]):
        self.data = data
        self.strings = strings
        self.index = len(data)  # Start past end, will --index before read
        self.objects: list[Any] = []  # Object table for backreferences
        self.object_count = 0

        # Build type lookup
        self.type_map: dict[int, str] = {}  # 1-based ref -> short type name
        for i, s in enumerate(strings):
            if "/" in s and ("com." in s or "java." in s or "[L" in s):
                self.type_map[i + 1] = s

    def read_int(self) -> int:
        self.index -= 1
        val = self.data[self.index]
        if isinstance(val, int):
            return val
        return int(val)

    def read_double(self) -> float:
        self.index -= 1
        val = self.data[self.index]
        if isinstance(val, float):
            return val
        if isinstance(val, int):
            return float(val)
        return float(val)

    def read_long(self) -> int:
        # GWT encodes longs as two ints (low, high) or as a string
        self.index -= 1
        val = self.data[self.index]
        if isinstance(val, str):
            return int(val.strip("'"), 36) if val.startswith("'") else int(val)
        return int(val)

    def read_string(self) -> str | None:
        ref = self.read_int()
        if ref == 0:
            return None
        if ref > 0:
            return self.strings[ref - 1]
        # Negative string ref - treat as empty/null
        return None

    def read_object(self) -> Any:
        token = self.read_int()
        if token == 0:
            return None
        if token < 0:
            # Backreference to previously deserialized object
            obj_index = -token
            if obj_index <= len(self.objects):
                return self.objects[obj_index - 1]
            return f"<backref:{obj_index}>"

        # New object - token is 1-based string table index for type
        type_sig = self.strings[token - 1]
        short_name = type_sig.split("/")[0].split(".")[-1]

        # Reserve slot in object table
        obj_slot = len(self.objects)
        self.objects.append(None)  # Placeholder

        # Deserialize based on type
        obj = self._deserialize(short_name, type_sig)
        self.objects[obj_slot] = obj
        return obj

    def _deserialize(self, short_name: str, type_sig: str) -> Any:
        if short_name == "HashMap":
            return self._read_hashmap()
        elif short_name == "ArrayList":
            return self._read_arraylist()
        elif short_name == "HashSet":
            return self._read_hashset()
        elif short_name == "Row":
            return self._read_row()
        elif short_name == "String":
            return self._read_java_string()
        elif short_name == "Double":
            return self._read_java_double()
        elif short_name == "Integer":
            return self._read_java_integer()
        elif short_name == "Boolean":
            return self._read_java_boolean()
        elif short_name == "StringValue":
            return self._read_string_value()
        elif short_name == "NumberValue":
            return self._read_number_value()
        elif short_name == "NullValue":
            return self._read_null_value()
        elif short_name == "ArrayValue":
            return self._read_array_value()
        elif short_name == "ViewPage":
            return self._read_view_page()
        elif short_name == "ViewToken":
            return self._read_view_token()
        elif short_name == "DataGroup":
            return self._read_data_group()
        elif short_name == "RunReportResult":
            return self._read_run_report_result()
        elif short_name == "Order":
            return self._read_order()
        elif short_name == "Timestamp":
            return self._read_timestamp()
        elif short_name == "MultipartCommand":
            return self._read_multipart_command()
        else:
            # Unknown type - try to skip gracefully
            return {"_type": short_name, "_unknown": True}

    def _read_hashmap(self) -> dict:
        size = self.read_int()
        result = {}
        for _ in range(size):
            key = self.read_object()
            value = self.read_object()
            if key is not None:
                result[str(key)] = value
        return result

    def _read_arraylist(self) -> list:
        size = self.read_int()
        items = []
        for _ in range(size):
            items.append(self.read_object())
        return items

    def _read_hashset(self) -> list:
        size = self.read_int()
        items = []
        for _ in range(size):
            items.append(self.read_object())
        return items

    def _read_row(self) -> dict:
        # Row serialization: it contains a HashMap<String, Value>
        # The HashMap is serialized inline (not as a separate readObject)
        inner = self.read_object()  # This reads the HashMap
        if isinstance(inner, dict):
            return {"_type": "Row", "_data": inner}
        return {"_type": "Row", "_data": {}}

    def _read_java_string(self) -> str:
        return self.read_string() or ""

    def _read_java_double(self) -> float:
        return self.read_double()

    def _read_java_integer(self) -> int:
        return self.read_int()

    def _read_java_boolean(self) -> bool:
        return self.read_int() != 0

    def _read_string_value(self) -> dict:
        val = self.read_string()
        return {"_type": "StringValue", "value": val}

    def _read_number_value(self) -> dict:
        val = self.read_object()  # Reads a Double object
        if isinstance(val, (int, float)):
            return {"_type": "NumberValue", "value": val}
        return {"_type": "NumberValue", "value": val}

    def _read_null_value(self) -> dict:
        return {"_type": "NullValue", "value": None}

    def _read_array_value(self) -> dict:
        # ArrayValue contains a Value[] array
        arr = self.read_object()  # reads the array
        return {"_type": "ArrayValue", "values": arr}

    def _read_view_token(self) -> dict:
        token_id = self.read_string()
        return {"_type": "ViewToken", "id": token_id}

    def _read_view_page(self) -> dict:
        # ViewPage fields: ViewToken, rows (List), totalCount, offset, etc.
        # Need to figure out exact field order
        # Try: read fields one at a time
        view_token = self.read_object()
        data_or_rows = self.read_object()  # Could be ArrayList of Rows or DataGroup
        total_count = self.read_int()
        offset = self.read_int()
        return {
            "_type": "ViewPage",
            "viewToken": view_token,
            "data": data_or_rows,
            "totalCount": total_count,
            "offset": offset,
        }

    def _read_data_group(self) -> dict:
        # DataGroup probably contains rows
        rows = self.read_object()  # ArrayList of Rows
        return {"_type": "DataGroup", "rows": rows}

    def _read_run_report_result(self) -> dict:
        # RunReportResult contains report + view page
        view_page = self.read_object()
        return {"_type": "RunReportResult", "viewPage": view_page}

    def _read_order(self) -> dict:
        field = self.read_string()
        ascending = self.read_int()
        return {"_type": "Order", "field": field, "ascending": ascending != 0}

    def _read_timestamp(self) -> dict:
        # java.sql.Timestamp: serialized as long (millis) then int (nanos)
        # But GWT may serialize differently
        high = self.read_long()
        low = self.read_long()
        return {"_type": "Timestamp", "value": f"{high}:{low}"}

    def _read_multipart_command(self) -> dict:
        # MultipartCommand wraps results in an ArrayList
        results = self.read_object()
        return {"_type": "MultipartCommand", "results": results}


def extract_rows_from_response(text: str) -> list[dict]:
    """Extract Row data from a GWT RunReportCommand response."""
    parsed = parse_response(text)
    reader = GwtStreamReader(parsed["data"], parsed["strings"])

    try:
        result = reader.read_object()
    except Exception as e:
        print(f"Deserialization failed at index {reader.index}: {e}", file=sys.stderr)
        print(f"Trying targeted row extraction...", file=sys.stderr)
        return _extract_rows_targeted(parsed["data"], parsed["strings"])

    # Navigate the result structure to find rows
    rows = _find_rows(result)
    if rows:
        return rows

    # If structured deserialization didn't work, try targeted
    return _extract_rows_targeted(parsed["data"], parsed["strings"])


def _find_rows(obj, depth=0) -> list[dict]:
    """Recursively search for Row objects in the deserialized tree."""
    if depth > 20:
        return []

    if isinstance(obj, dict):
        if obj.get("_type") == "Row":
            data = obj.get("_data", {})
            # Flatten Value wrappers
            flat = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    if v.get("_type") in ("StringValue", "NumberValue"):
                        flat[k] = v.get("value")
                    elif v.get("_type") == "NullValue":
                        flat[k] = None
                    elif v.get("_type") == "ArrayValue":
                        vals = v.get("values", [])
                        if isinstance(vals, list):
                            flat[k] = "; ".join(
                                str(item.get("value", ""))
                                if isinstance(item, dict) else str(item)
                                for item in vals
                            )
                        else:
                            flat[k] = str(vals)
                    else:
                        flat[k] = str(v)
                else:
                    flat[k] = v
            return [flat]

        # Search in dict values
        all_rows = []
        for v in obj.values():
            all_rows.extend(_find_rows(v, depth + 1))
        return all_rows

    if isinstance(obj, list):
        all_rows = []
        for item in obj:
            all_rows.extend(_find_rows(item, depth + 1))
        return all_rows

    return []


def _extract_rows_targeted(data: list, strings: list[str]) -> list[dict]:
    """Targeted extraction: find Row objects by scanning data right-to-left."""
    # Find key type refs
    ROW_REF = HASHMAP_REF = STRVAL_REF = NUMVAL_REF = NULLVAL_REF = None
    STRING_REF = DOUBLE_REF = ARRVAL_REF = None

    for i, s in enumerate(strings):
        short = s.split("/")[0].split(".")[-1] if "/" in s else ""
        ref = i + 1
        if short == "Row":
            ROW_REF = ref
        elif short == "HashMap" and "java.util" in s:
            HASHMAP_REF = ref
        elif short == "StringValue":
            STRVAL_REF = ref
        elif short == "NumberValue":
            NUMVAL_REF = ref
        elif short == "NullValue":
            NULLVAL_REF = ref
        elif short == "ArrayValue":
            ARRVAL_REF = ref
        elif s == "java.lang.String/2004016611":
            STRING_REF = ref
        elif s == "java.lang.Double/858496421":
            DOUBLE_REF = ref

    # Find field names in string table
    field_names = set()
    known_fields = {
        "custNo", "name", "address", "address_2", "city", "state", "zip",
        "phone", "contact", "taxCode", "desc", "linkToSalesperson_assoc_name",
        "customer", "linkToPymtTerms_assoc_desc",
    }
    field_refs = {}
    for i, s in enumerate(strings):
        if s in known_fields:
            field_refs[i + 1] = s
            field_names.add(s)

    # Find Row positions
    row_positions = [i for i, v in enumerate(data) if v == ROW_REF]

    print(f"Found {len(row_positions)} Row refs, reading right-to-left", file=sys.stderr)

    rows = []
    # For each Row, read the HashMap that follows it (to its LEFT in the array)
    # Pattern: ... [key-value pairs] size HashMap_ref Row_ref ...
    # Reading right-to-left from Row_ref:
    #   1. Row_ref (143) - already found
    #   2. HashMap_ref (5) - the next value to the left
    #   3. size (14) - HashMap size
    #   4. 14 key-value pairs, each pair = key_obj + value_obj

    for row_pos in row_positions:
        # Read leftward from row_pos
        idx = row_pos  # Current position

        # Skip Row ref itself (we know it's 143)
        idx -= 1

        # Next should be HashMap ref
        if idx < 0 or data[idx] != HASHMAP_REF:
            # Maybe HashMap is a backreference
            if idx >= 0 and isinstance(data[idx], int) and data[idx] < 0:
                idx -= 1  # skip backreference
            else:
                continue

        idx -= 1  # move past HashMap ref

        # Read size
        if idx < 0:
            continue
        size = data[idx]
        if not isinstance(size, int) or size < 1 or size > 30:
            continue
        idx -= 1

        # Read key-value pairs (right to left)
        row_data = {}
        obj_table = {}  # Simple object tracking for backrefs within this row

        for pair_idx in range(size):
            if idx < 0:
                break

            # Read key (right to left): type_ref then string_ref
            # Or backreference
            key_token = data[idx]
            idx -= 1
            key_str = None

            if isinstance(key_token, int) and key_token == STRING_REF:
                # New String object - next value (to left) is the string ref
                if idx >= 0:
                    str_ref = data[idx]
                    idx -= 1
                    if isinstance(str_ref, int) and 0 < str_ref <= len(strings):
                        key_str = strings[str_ref - 1]
            elif isinstance(key_token, int) and key_token < 0:
                # Backreference to a previously seen String object
                # The object was a field name string
                backref_idx = -key_token
                key_str = obj_table.get(f"obj_{backref_idx}")

            if key_str and key_str in field_names:
                # Read value object
                if idx < 0:
                    break
                val_token = data[idx]
                idx -= 1
                value = None

                if val_token == STRVAL_REF:
                    # StringValue: next is the string content ref
                    if idx >= 0:
                        content_ref = data[idx]
                        idx -= 1
                        if isinstance(content_ref, int) and 0 < content_ref <= len(strings):
                            value = strings[content_ref - 1]
                        elif isinstance(content_ref, int) and content_ref < 0:
                            # Backreference to a string
                            pass
                elif val_token == NUMVAL_REF:
                    # NumberValue: next is a Double object
                    if idx >= 0:
                        double_token = data[idx]
                        idx -= 1
                        if double_token == DOUBLE_REF:
                            if idx >= 0:
                                value = data[idx]
                                idx -= 1
                        elif isinstance(double_token, int) and double_token < 0:
                            # Backref to Double
                            pass
                elif val_token == NULLVAL_REF:
                    value = None
                elif val_token == ARRVAL_REF:
                    # ArrayValue - complex, skip for now
                    value = "<array>"
                elif isinstance(val_token, int) and val_token < 0:
                    # Backreference to a Value object
                    pass

                row_data[key_str] = value
            else:
                # Unknown key or not a field we care about
                # Need to skip the value too
                if idx >= 0:
                    val_token = data[idx]
                    idx -= 1
                    # Skip value payload based on type
                    if isinstance(val_token, int) and val_token == STRVAL_REF:
                        idx -= 1  # skip string ref
                    elif isinstance(val_token, int) and val_token == NUMVAL_REF:
                        if idx >= 0 and data[idx] == DOUBLE_REF:
                            idx -= 2  # skip Double type + value
                        else:
                            idx -= 1
                    elif isinstance(val_token, int) and val_token == NULLVAL_REF:
                        pass  # no payload
                    elif isinstance(val_token, int) and val_token < 0:
                        pass  # backreference, no extra payload

        if row_data:
            rows.append(row_data)

    return rows


if __name__ == "__main__":
    response_file = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\customer_listing_response.txt")
    text = response_file.read_text(encoding="utf-8")
    parsed = parse_response(text)
    data = parsed["data"]
    strings = parsed["strings"]

    print(f"Data tokens: {len(data)}")
    print(f"String table: {len(strings)} entries")
    print()

    # First: try the full deserializer
    reader = GwtStreamReader(data, strings)
    print(f"Starting deserialization from index {reader.index}...")
    try:
        result = reader.read_object()
        print(f"Top-level type: {result.get('_type', 'unknown') if isinstance(result, dict) else type(result)}")
        print(f"Reader stopped at index: {reader.index}")
        print()

        # Find rows
        rows = _find_rows(result)
        if rows:
            print(f"Found {len(rows)} rows via structured deserialization")
            for i, row in enumerate(rows[:3]):
                print(f"  Row {i}: {row}")
        else:
            print("No rows found via structured deserialization")
    except Exception as e:
        print(f"Structured deserialization failed: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print()

    # Second: try targeted extraction
    print("Trying targeted extraction...")
    rows = _extract_rows_targeted(data, strings)
    print(f"Found {len(rows)} rows via targeted extraction")
    for i, row in enumerate(rows[:5]):
        print(f"  Row {i}:")
        for k, v in sorted(row.items()):
            print(f"    {k}: {v!r}")
