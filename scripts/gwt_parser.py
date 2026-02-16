"""GWT RPC v7 Response Parser for Entrinsik Informer 4.x.

Parses ``//OK[...]`` and ``//EX[...]`` responses from the Informer BI
GWT-RPC layer into structured Python data.  Designed for **read-only**
data extraction from legitimately authenticated Informer sessions.

GWT RPC v7 response anatomy::

    //OK[<numeric_data>, ["string_table_entries"], <offset>, <version>]

The numeric section encodes an object graph whose leaf values reference
entries in the string table by 1-based index.  Row payloads are
serialised as ``HashMap<String, Value>`` where *Value* is one of
``StringValue``, ``NumberValue``, ``NullValue``, or ``ArrayValue``.

This module exposes five public helpers:

* ``parse_gwt_response``   -- low-level parse into data / strings / trailer
* ``extract_rows``         -- high-level: response text -> list[dict]
* ``discover_field_names`` -- auto-discover column names from a response
* ``extract_view_token``   -- pull the ViewToken UUID out of a response
* ``extract_total_count``  -- pull the total-row-count integer
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any

# ---------------------------------------------------------------------------
# GWT base-64 long decoder
# ---------------------------------------------------------------------------
# GWT-RPC encodes Java longs as base-64 strings using the alphabet:
#   A=0 .. Z=25, a=26 .. z=51, 0=52 .. 9=61, _=62, $=63
# A leading '$' indicates a negative value.

_GWT_B64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$"
_GWT_B64_CHARMAP: dict[str, int] = {c: i for i, c in enumerate(_GWT_B64_ALPHABET)}


def _decode_gwt_long(encoded: str) -> int | None:
    """Decode a GWT base-64 encoded long to a Python int."""
    if not encoded or not isinstance(encoded, str):
        return None
    neg = encoded[0] == "$"
    s = encoded[1:] if neg else encoded
    val = 0
    for c in s:
        v = _GWT_B64_CHARMAP.get(c)
        if v is None:
            return None
        val = val * 64 + v
    return -val if neg else val


def _gwt_timestamp_to_date(encoded: str) -> str | None:
    """Decode a GWT timestamp string to YYYY-MM-DD format."""
    ms = _decode_gwt_long(encoded)
    if ms is None:
        return None
    try:
        dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (OSError, ValueError, OverflowError):
        return None


def _gwt_timestamp_to_time(encoded: str) -> str | None:
    """Decode a GWT timestamp string to HH:MM:SS format."""
    ms = _decode_gwt_long(encoded)
    if ms is None:
        return None
    try:
        dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
        return dt.strftime("%H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return None

__all__ = [
    "GwtParseError",
    "parse_gwt_response",
    "extract_rows",
    "extract_view_token",
    "extract_total_count",
    "discover_field_names",
]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GwtParseError(Exception):
    """Raised when a GWT response cannot be parsed."""

    def __init__(self, message: str, response_text: str = "") -> None:
        self.response_text = response_text
        super().__init__(message)


# ---------------------------------------------------------------------------
# GWT string-escape map
# ---------------------------------------------------------------------------

_GWT_ESCAPES: dict[str, str] = {
    r"\x3D": "=",
    r"\x3d": "=",
    r"\x27": "'",
    r"\x26": "&",
    r"\x3C": "<",
    r"\x3c": "<",
    r"\x3E": ">",
    r"\x3e": ">",
    r"\x22": '"',
    r"\x5C": "\\",
    r"\x5c": "\\",
    r"\x09": "\t",
    r"\x0A": "\n",
    r"\x0a": "\n",
    r"\x0D": "\r",
    r"\x0d": "\r",
}

# Pre-compiled regex covering all \xHH escapes
_GWT_ESCAPE_RE = re.compile(r"\\x([0-9A-Fa-f]{2})")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _unescape_gwt(text: str) -> str:
    """Replace GWT ``\\xHH`` hex escapes with their character equivalents.

    Args:
        text: Raw GWT string content (may contain ``\\x`` escapes).

    Returns:
        Unescaped string.
    """
    # Fast path -- most strings have no escapes.
    if r"\x" not in text:
        return text

    # Apply the known fixed escapes first (cheap dict lookups).
    for escaped, replacement in _GWT_ESCAPES.items():
        if escaped in text:
            text = text.replace(escaped, replacement)

    # Catch any remaining \xHH sequences with a regex fallback.
    def _hex_replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return _GWT_ESCAPE_RE.sub(_hex_replace, text)


# ---------------------------------------------------------------------------
# Low-level response parser
# ---------------------------------------------------------------------------


def _find_string_table_bounds(inner: str) -> tuple[int, int]:
    """Return (start, end) character indices of the string table array.

    The string table is the *last* ``[...]`` array in the outer ``[...]``
    wrapper.  It always begins with ``,[\"`` when preceded by the data
    section.

    Args:
        inner: The content inside ``//OK`` (including outer brackets).

    Returns:
        Tuple of (start_of_open_bracket, end_of_close_bracket) indices.

    Raises:
        GwtParseError: If the string table cannot be located.
    """
    # Search backwards for the opening of the string table.
    # Pattern: ,["  (comma, open bracket, double-quote)
    start = inner.rfind(',["')
    if start == -1:
        raise GwtParseError("String table not found in GWT response")

    # The bracket itself is at start+1.
    bracket_pos = start + 1
    depth = 0
    i = bracket_pos
    while i < len(inner):
        ch = inner[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return bracket_pos, i
        elif ch == '"':
            # Skip over quoted string (respecting backslash escapes).
            i += 1
            while i < len(inner) and inner[i] != '"':
                if inner[i] == "\\":
                    i += 1  # skip escaped character
                i += 1
        i += 1

    raise GwtParseError("Unterminated string table bracket")


def _parse_string_table(raw: str) -> list[str]:
    """Parse a JSON-encoded string array, handling GWT hex escapes.

    Args:
        raw: Raw JSON array text, e.g. ``["foo","bar"]``.

    Returns:
        List of unescaped strings.
    """
    unescaped = _unescape_gwt(raw)
    try:
        result: list[str] = json.loads(unescaped)
        return result
    except json.JSONDecodeError:
        # Fallback: extract quoted strings via regex.
        return re.findall(r'"((?:[^"\\]|\\.)*)"', unescaped)


def _parse_data_values(raw: str) -> list[int | float | str | None]:
    """Parse the comma-separated numeric/string data section.

    Values may be integers, floats, or single-quoted inline strings.
    The data section sits between the outer ``[`` and the string table.

    Args:
        raw: Raw comma-separated values text.

    Returns:
        List of parsed values.
    """
    values: list[int | float | str | None] = []
    if not raw.strip():
        return values

    current = ""
    in_quote = False

    for ch in raw:
        if ch == "'" and not in_quote:
            in_quote = True
            current += ch
        elif ch == "'" and in_quote:
            in_quote = False
            current += ch
        elif ch == "," and not in_quote:
            token = current.strip()
            if token:
                values.append(_coerce_token(token))
            current = ""
        else:
            current += ch

    token = current.strip()
    if token:
        values.append(_coerce_token(token))

    return values


def _coerce_token(token: str) -> int | float | str | None:
    """Coerce a raw GWT data token to its Python type."""
    if not token:
        return None
    # Single-quoted inline string (rare in responses, but valid).
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    # Negative-exponent floats (e.g. "1.5E-4")
    if "E" in token or "e" in token or "." in token:
        try:
            return float(token)
        except ValueError:
            pass
    try:
        return int(token)
    except ValueError:
        pass
    return token


def parse_gwt_response(text: str) -> dict[str, Any]:
    """Parse a GWT RPC v7 ``//OK[...]`` or ``//EX[...]`` response.

    Args:
        text: Full HTTP response body starting with ``//OK`` or ``//EX``.

    Returns:
        Dictionary with keys:
            * ``data``     -- list of numeric/inline values from the object graph
            * ``strings``  -- list of strings from the string table
            * ``offset``   -- integer trailer value (usually 0)
            * ``version``  -- protocol version (usually 7)
            * ``is_exception`` -- True if the response was ``//EX``

    Raises:
        GwtParseError: On ``//EX`` responses or malformed input.
        ValueError: If *text* is not a GWT response at all.
    """
    text = text.strip()

    is_exception = text.startswith("//EX")

    if not text.startswith("//OK") and not is_exception:
        raise ValueError(f"Not a GWT response (first 80 chars): {text[:80]}")

    # Strip the prefix.
    inner = text[4:]

    # Locate the string table.
    try:
        st_start, st_end = _find_string_table_bounds(inner)
    except GwtParseError:
        # Degenerate response with no string table.
        return {
            "data": [],
            "strings": [],
            "offset": 0,
            "version": 7,
            "is_exception": is_exception,
            "raw": inner,
        }

    # Parse the three sections.
    str_table_raw = inner[st_start : st_end + 1]
    strings = _parse_string_table(str_table_raw)

    # Data values live between the outer '[' and the comma before the string table.
    data_raw = inner[1 : st_start - (0 if inner[st_start - 1] != "," else 0)]
    # Trim trailing comma that precedes the string table.
    if data_raw.endswith(","):
        data_raw = data_raw[:-1]
    data_values = _parse_data_values(data_raw)

    # Trailer: everything after the string table close bracket, inside the outer ']'.
    trailer_raw = inner[st_end + 1 :].rstrip("]").lstrip(",")
    trailer_parts = [p.strip() for p in trailer_raw.split(",") if p.strip()]
    offset = int(trailer_parts[0]) if len(trailer_parts) > 0 else 0
    version = int(trailer_parts[1]) if len(trailer_parts) > 1 else 7

    result: dict[str, Any] = {
        "data": data_values,
        "strings": strings,
        "offset": offset,
        "version": version,
        "is_exception": is_exception,
    }

    if is_exception:
        # Pull the first meaningful string as the error message.
        _TYPE_PREFIXES = ("com.entrinsik.", "com.google.", "java.", "[L")
        for s in strings:
            if not any(s.startswith(p) for p in _TYPE_PREFIXES):
                result["error_message"] = s
                break
        raise GwtParseError(
            f"GWT RPC exception: {result.get('error_message', text[:200])}",
            response_text=text,
        )

    return result


# ---------------------------------------------------------------------------
# Type-class detection helpers
# ---------------------------------------------------------------------------

# Prefixes that identify GWT type descriptors (not user data).
_TYPE_PREFIXES = (
    "com.entrinsik.",
    "com.google.",
    "java.",
    "[L",
    "rO0AB",
)


def _is_type_string(s: str) -> bool:
    """Return True if *s* looks like a GWT type descriptor."""
    return any(s.startswith(p) for p in _TYPE_PREFIXES)


def _find_type_index(strings: list[str], fragment: str) -> int | None:
    """Find the 0-based string-table index whose value contains *fragment*."""
    for idx, s in enumerate(strings):
        if fragment in s and "/" in s:
            return idx
    return None


# ---------------------------------------------------------------------------
# Row extraction -- the core algorithm
# ---------------------------------------------------------------------------


def _build_field_index_map(
    strings: list[str],
    field_names: list[str],
) -> dict[str, int]:
    """Map each known field name to its 0-based string-table index.

    Args:
        strings: The string table from the parsed response.
        field_names: Column / field names to search for.

    Returns:
        Dict mapping field_name -> string-table index.
    """
    index_map: dict[str, int] = {}
    for name in field_names:
        for idx, s in enumerate(strings):
            if s == name:
                index_map[name] = idx
                break
    return index_map


def _find_type_refs(strings: list[str]) -> dict[str, int]:
    """Build a map of short_type_name -> 1-based string-table ref."""
    refs: dict[str, int] = {}
    for i, s in enumerate(strings):
        if "/" in s and ("com." in s or "java." in s or "[L" in s):
            short = s.split("/")[0].split(".")[-1]
            refs[short] = i + 1
    return refs


def _rtl_read_value(
    pos: int,
    data: list[int | float | str | None],
    strings: list[str],
    type_refs: dict[str, int],
) -> tuple[str | float | None, int]:
    """Read a Value object right-to-left from *pos* in the data array.

    Handles StringValue, NumberValue, NullValue, ArrayValue, and
    negative backreference tokens.

    Args:
        pos: Current index in *data* (reading leftward).
        data: Parsed numeric data array.
        strings: Parsed string table.
        type_refs: Mapping of short type name to 1-based string ref,
            as returned by ``_find_type_refs``.

    Returns:
        Tuple of (extracted_value, new_position_after_reading).
        *new_position* is the index of the next unread token to the left.
    """
    STRVAL_REF = type_refs.get("StringValue")
    NUMVAL_REF = type_refs.get("NumberValue")
    NULLVAL_REF = type_refs.get("NullValue")
    ARRVAL_REF = type_refs.get("ArrayValue")
    DOUBLE_REF = type_refs.get("Double")
    DATEVAL_REF = type_refs.get("DateValue")
    TIMEVAL_REF = type_refs.get("TimeValue")
    DATE_REF = type_refs.get("Date")
    TIME_REF = type_refs.get("Time")
    ENUMVAL_REF = type_refs.get("EnumValue")

    if pos < 0:
        return None, pos
    val_token = data[pos]
    pos -= 1

    if val_token == STRVAL_REF:
        # StringValue: next token (leftward) is the string ref
        if pos >= 0:
            str_ref = data[pos]
            pos -= 1
            if isinstance(str_ref, int) and 0 < str_ref <= len(strings):
                return strings[str_ref - 1], pos
        return None, pos

    elif val_token == NUMVAL_REF:
        # NumberValue: next is a Double object (type + value) or backref
        if pos >= 0:
            dbl_token = data[pos]
            pos -= 1
            if dbl_token == DOUBLE_REF:
                # New Double: next is the raw value
                if pos >= 0:
                    raw_val = data[pos]
                    pos -= 1
                    if isinstance(raw_val, (int, float)):
                        return float(raw_val), pos
            elif isinstance(dbl_token, int) and dbl_token < 0:
                # Backref to a previously seen Double (value = 0.0 typically)
                return 0.0, pos
            elif isinstance(dbl_token, (int, float)):
                return float(dbl_token), pos
        return None, pos

    elif val_token == NULLVAL_REF:
        # NullValue: no payload
        return None, pos

    elif val_token == DATEVAL_REF:
        # DateValue has 3 serialized fields (RTL):
        #   1. dateCode string ref  (writeString - format ID like "300")
        #   2. intermediate object  (writeObject - usually null=0)
        #   3. java.util.Date object (writeObject - type_ref + GWT-b64 timestamp)
        date_val = None
        if pos >= 0:
            # 1. dateCode string ref (skip - just a format ID)
            str_ref = data[pos]
            pos -= 1
            # 2. intermediate object (usually null=0, could be backref)
            if pos >= 0:
                mid_token = data[pos]
                pos -= 1
                if mid_token == DATE_REF:
                    # No intermediate field - this IS the Date type ref
                    if pos >= 0:
                        ts = data[pos]
                        pos -= 1
                        date_val = _gwt_timestamp_to_date(ts) if isinstance(ts, str) else None
                elif mid_token == 0 or (isinstance(mid_token, int) and mid_token < 0):
                    # Null or backref intermediate - now read the Date object
                    if pos >= 0:
                        date_type = data[pos]
                        pos -= 1
                        if date_type == DATE_REF:
                            if pos >= 0:
                                ts = data[pos]
                                pos -= 1
                                date_val = _gwt_timestamp_to_date(ts) if isinstance(ts, str) else None
                        elif date_type == 0:
                            pass  # null Date
                        elif isinstance(date_type, int) and date_type < 0:
                            pass  # backref to a previously seen Date
        return date_val, pos

    elif val_token == TIMEVAL_REF:
        # TimeValue has 3 serialized fields (RTL):
        #   1. timeCode string ref  (writeString - format ID like "360")
        #   2. intermediate object  (writeObject - usually null=0)
        #   3. java.sql.Time object (writeObject - type_ref + GWT-b64 timestamp)
        time_val = None
        if pos >= 0:
            # 1. timeCode string ref (skip - just a format ID)
            str_ref = data[pos]
            pos -= 1
            # 2. intermediate object (usually null=0, could be backref)
            if pos >= 0:
                mid_token = data[pos]
                pos -= 1
                if mid_token == TIME_REF:
                    # No intermediate field - this IS the Time type ref
                    if pos >= 0:
                        ts = data[pos]
                        pos -= 1
                        time_val = _gwt_timestamp_to_time(ts) if isinstance(ts, str) else None
                elif mid_token == 0 or (isinstance(mid_token, int) and mid_token < 0):
                    # Null or backref intermediate - now read the Time object
                    if pos >= 0:
                        time_type = data[pos]
                        pos -= 1
                        if time_type == TIME_REF:
                            if pos >= 0:
                                ts = data[pos]
                                pos -= 1
                                time_val = _gwt_timestamp_to_time(ts) if isinstance(ts, str) else None
                        elif time_type == 0:
                            pass  # null Time
                        elif isinstance(time_type, int) and time_type < 0:
                            pass  # backref to a previously seen Time
        return time_val, pos

    elif val_token == ENUMVAL_REF:
        # EnumValue: enum_type_ref, ordinal
        if pos >= 0:
            _enum_type = data[pos]
            pos -= 1
            if pos >= 0:
                ordinal = data[pos]
                pos -= 1
                if isinstance(ordinal, int) and 0 < ordinal <= len(strings):
                    return strings[ordinal - 1], pos
                return str(ordinal) if ordinal is not None else None, pos
        return None, pos

    elif isinstance(val_token, int) and val_token < 0:
        # Backreference to a previously seen Value object.
        return None, pos

    elif val_token == ARRVAL_REF:
        # ArrayValue: reads a Value[] array.
        # Pattern: ArrayValue_ref, Value[]_type_ref, array_size, elements...
        if pos >= 0:
            arr_type = data[pos]
            pos -= 1
            if pos >= 0:
                arr_size = data[pos]
                pos -= 1
                if isinstance(arr_size, int) and 0 < arr_size <= 20:
                    parts = []
                    for _ in range(arr_size):
                        elem_val, pos = _rtl_read_value(
                            pos, data, strings, type_refs
                        )
                        if elem_val is not None:
                            parts.append(str(elem_val))
                    return "; ".join(parts), pos
        return "<array>", pos

    # Unknown value type
    return None, pos


def _rtl_read_key(
    pos: int,
    data: list[int | float | str | None],
    strings: list[str],
    type_refs: dict[str, int],
) -> tuple[str | None, int, int | None]:
    """Read a HashMap key right-to-left from *pos* in the data array.

    Args:
        pos: Current index in *data* (reading leftward).
        data: Parsed numeric data array.
        strings: Parsed string table.
        type_refs: Mapping of short type name to 1-based string ref,
            as returned by ``_find_type_refs``.

    Returns:
        Tuple of (field_name_or_None, new_position, key_token).
        *key_token* is the raw data token for backref tracking.
    """
    STRING_REF = type_refs.get("String")

    if pos < 0:
        return None, pos, None
    key_token = data[pos]
    pos -= 1

    if isinstance(key_token, int) and key_token == STRING_REF:
        # New String object: next token is the string table ref
        if pos >= 0:
            str_ref = data[pos]
            pos -= 1
            if isinstance(str_ref, int) and 0 < str_ref <= len(strings):
                return strings[str_ref - 1], pos, key_token
        return None, pos, key_token

    elif isinstance(key_token, int) and key_token < 0:
        # Backreference -- resolved via positional mapping later
        return None, pos, key_token

    elif isinstance(key_token, int) and 0 < key_token <= len(strings):
        # Direct string ref
        return strings[key_token - 1], pos, key_token

    return None, pos, key_token


def _extract_rows_rtl(
    strings: list[str],
    data: list[int | float | str | None],
    field_names: list[str],
) -> list[dict[str, str | float | None]]:
    """Extract rows by reading the GWT data array RIGHT-TO-LEFT.

    GWT RPC v7 responses are read from the end of the data array toward
    the beginning (the client uses ``--index`` pre-decrement).  The
    server writes tokens in order and reverses them in the response.

    Each Row object is serialised as::

        143  (Row type ref)
        5    (HashMap type ref)
        N    (HashMap size = number of fields)
        [key_obj, value_obj] * N  (key-value pairs, reading rightward)

    Where each key is a ``readObject()`` call (type 144 = java.lang.String
    for new keys, or a negative backreference for reused keys), and each
    value is a ``readObject()`` call to a Value subclass.

    This function:
    1.  Locates all Row type markers in the data.
    2.  For the *first* full-size Row (read from the right, which is the
        first row deserialized), builds a field-name mapping by tracking
        new String objects for keys.
    3.  For all remaining rows, uses the established backref-to-field map.

    Args:
        strings: Parsed string table.
        data: Parsed numeric data array.
        field_names: Known column field names for the report.

    Returns:
        List of row dicts, each mapping field_name -> value.
    """
    if not strings or not data or not field_names:
        return []

    type_refs = _find_type_refs(strings)
    ROW_REF = type_refs.get("Row")
    HASHMAP_REF = type_refs.get("HashMap")
    STRVAL_REF = type_refs.get("StringValue")
    NUMVAL_REF = type_refs.get("NumberValue")
    NULLVAL_REF = type_refs.get("NullValue")
    ARRVAL_REF = type_refs.get("ArrayValue")
    STRING_REF = type_refs.get("String")
    DOUBLE_REF = type_refs.get("Double")

    if ROW_REF is None or HASHMAP_REF is None:
        log.warning("Row or HashMap type not found in string table")
        return []

    # Build field name ref lookup (1-based string index -> field name)
    field_name_refs: dict[int, str] = {}
    field_name_set = set(field_names)
    for i, s in enumerate(strings):
        if s in field_name_set:
            field_name_refs[i + 1] = s

    # Find all Row positions in data (left-to-right array indices)
    row_positions = [i for i, v in enumerate(data) if v == ROW_REF]
    if not row_positions:
        log.warning("No Row type markers found in data")
        return []

    # Determine which rows are "full" data rows (size > 1)
    # by checking the HashMap size value
    full_row_positions = []
    for rp in row_positions:
        # Pattern: data[rp] = ROW_REF, data[rp-1] = HASHMAP_REF, data[rp-2] = size
        if rp >= 2:
            hm = data[rp - 1]
            sz = data[rp - 2]
            # HashMap ref could be positive (first time) or negative (backref)
            is_hashmap = (hm == HASHMAP_REF) or (isinstance(hm, int) and hm < 0)
            if is_hashmap and isinstance(sz, int) and sz > 1:
                full_row_positions.append(rp)

    if not full_row_positions:
        log.warning("No full-size Row objects found")
        return []

    log.info(
        "Found %d full rows (of %d total Row markers)",
        len(full_row_positions),
        len(row_positions),
    )

    def _read_value_rtl(pos: int) -> tuple[str | float | None, int]:
        """Read a Value object right-to-left (delegates to module helper)."""
        return _rtl_read_value(pos, data, strings, type_refs)

    def _read_key_rtl(pos: int) -> tuple[str | None, int, int | None]:
        """Read a HashMap key right-to-left (delegates to module helper)."""
        return _rtl_read_key(pos, data, strings, type_refs)

    # --- Two-pass extraction ---
    #
    # Pass 1: Process the RIGHTMOST full row.  Its keys are either new
    #         String objects or backrefs.  Any new-String keys give us
    #         a field name directly.  We record the field order.
    #
    # Pass 2: Apply the same field order to ALL rows using positional
    #         mapping.  Since every row has the same HashMap key order,
    #         pair N in every row corresponds to the same field.

    # --- Pass 1: Discover field order from rightmost full row ---
    rightmost = full_row_positions[-1]  # Closest to right = deserialized first
    idx = rightmost - 2
    size_right = data[idx] if idx >= 0 else 0
    if not isinstance(size_right, int) or size_right < 1:
        log.warning("Could not determine HashMap size for rightmost row")
        return []
    idx -= 1

    field_order: list[str | None] = []
    for pair_num in range(size_right):
        if idx < 0:
            break
        key_name, idx, _ = _read_key_rtl(idx)
        _, idx = _read_value_rtl(idx)
        field_order.append(key_name)

    # Fill in None entries by checking other full rows.
    # If a field_order slot is None (key was a backref we couldn't resolve),
    # try the second-rightmost row, etc.
    if None in field_order:
        for alt_row_pos in reversed(full_row_positions[:-1]):
            alt_idx = alt_row_pos - 2
            alt_size = data[alt_idx] if alt_idx >= 0 else 0
            if not isinstance(alt_size, int) or alt_size != size_right:
                continue
            alt_idx -= 1
            for pair_num in range(alt_size):
                if alt_idx < 0:
                    break
                key_name, alt_idx, _ = _read_key_rtl(alt_idx)
                _, alt_idx = _read_value_rtl(alt_idx)
                if pair_num < len(field_order) and field_order[pair_num] is None:
                    if key_name is not None:
                        field_order[pair_num] = key_name
            if None not in field_order:
                break

    # Last resort: for any remaining None positions, try to infer from
    # the set of field names not yet assigned.  The unresolved position
    # likely corresponds to 'custNo' (the customer number field).
    if None in field_order:
        assigned = {f for f in field_order if f is not None}
        unassigned = [f for f in field_names if f not in assigned]
        none_indices = [i for i, f in enumerate(field_order) if f is None]
        for ni, ua in zip(none_indices, unassigned):
            field_order[ni] = ua

    log.info("Field order (resolved): %s", field_order)

    # --- Pass 2: Extract ALL rows using positional field mapping ---
    all_rows: list[dict[str, str | float | None]] = []

    for row_pos in reversed(full_row_positions):
        idx = row_pos - 2
        if idx < 0:
            continue
        size = data[idx]
        if not isinstance(size, int) or size < 1:
            continue
        idx -= 1

        row_data: dict[str, str | float | None] = {}

        for pair_num in range(size):
            if idx < 0:
                break

            # Read key (we mostly ignore it -- use positional mapping)
            key_name, idx, _ = _read_key_rtl(idx)

            # Read value
            value, idx = _read_value_rtl(idx)

            # Determine field name: prefer direct key, fall back to position
            field_name = key_name
            if field_name is None and pair_num < len(field_order):
                field_name = field_order[pair_num]

            if field_name and field_name in field_name_set:
                row_data[field_name] = value
            elif field_name:
                # Unknown field (e.g. "@ID") -- include it
                row_data[field_name] = value

        if row_data:
            all_rows.append(row_data)

    # Rows were collected in reverse order (rightmost first), so reverse
    # to get them in page display order.
    all_rows.reverse()

    # Normalise: ensure every row has all field_names.
    for row in all_rows:
        for name in field_names:
            row.setdefault(name, None)

    return all_rows


def extract_rows(
    response_text: str,
    field_names: list[str],
) -> list[dict[str, str | float | None]]:
    """Extract structured row dicts from a GWT RPC response.

    This is the primary public entry point for row extraction.  It reads
    the GWT data array right-to-left (matching the GWT client's
    ``--index`` pre-decrement pattern) to properly deserialise Row
    objects containing ``HashMap<String, Value>`` entries.

    Args:
        response_text: Full ``//OK[...]`` HTTP response body.
        field_names: List of column field names (e.g.
            ``["custNo", "name", "city", ...]``).

    Returns:
        List of dicts, each mapping field_name -> value (str, float,
        or None).

    Raises:
        GwtParseError: If the response is an ``//EX`` exception.
        ValueError: If the input is not a GWT response.
    """
    parsed = parse_gwt_response(response_text)
    rows = _extract_rows_rtl(
        parsed["strings"],
        parsed["data"],
        field_names,
    )
    return rows


# ---------------------------------------------------------------------------
# Field-name auto-discovery
# ---------------------------------------------------------------------------


# Patterns that indicate a GWT type identifier rather than a user field name.
_TYPE_NAME_RE = re.compile(r"[/\\]|^com\.|^java\.|^org\.|^\[L")


def _is_type_identifier(name: str) -> bool:
    """Return True if *name* looks like a GWT type descriptor, not a field."""
    return bool(_TYPE_NAME_RE.search(name))


def discover_field_names(response_text: str) -> list[str]:
    """Auto-discover field names from a GWT RPC response.

    Analyzes the Row/HashMap structure in the response to extract
    column field names without requiring them to be pre-configured.

    Uses the same RTL reading algorithm as ``_extract_rows_rtl`` pass 1:
    finds the rightmost full Row, reads its HashMap keys, and returns
    the field names in order.

    Args:
        response_text: Full ``//OK[...]`` HTTP response body.

    Returns:
        List of field name strings (e.g. ``["custNo", "name", "city", ...]``).
        Returns empty list if no rows found.
    """
    parsed = parse_gwt_response(response_text)
    data: list[int | float | str | None] = parsed["data"]
    strings: list[str] = parsed["strings"]

    if not data or not strings:
        return []

    type_refs = _find_type_refs(strings)
    ROW_REF = type_refs.get("Row")
    HASHMAP_REF = type_refs.get("HashMap")

    if ROW_REF is None or HASHMAP_REF is None:
        log.warning("discover_field_names: Row or HashMap type not found")
        return []

    # Find all Row positions in data
    row_positions = [i for i, v in enumerate(data) if v == ROW_REF]
    if not row_positions:
        log.warning("discover_field_names: No Row type markers found")
        return []

    # Filter to full rows (HashMap size > 1)
    full_row_positions: list[int] = []
    for rp in row_positions:
        if rp >= 2:
            hm = data[rp - 1]
            sz = data[rp - 2]
            is_hashmap = (hm == HASHMAP_REF) or (isinstance(hm, int) and hm < 0)
            if is_hashmap and isinstance(sz, int) and sz > 1:
                full_row_positions.append(rp)

    if not full_row_positions:
        log.warning("discover_field_names: No full-size Row objects found")
        return []

    # --- Read keys from the rightmost full row ---
    rightmost = full_row_positions[-1]
    idx = rightmost - 2
    size_right = data[idx] if idx >= 0 else 0
    if not isinstance(size_right, int) or size_right < 1:
        log.warning("discover_field_names: Could not determine HashMap size")
        return []
    idx -= 1

    field_order: list[str | None] = []
    for _ in range(size_right):
        if idx < 0:
            break
        key_name, idx, _ = _rtl_read_key(idx, data, strings, type_refs)
        _, idx = _rtl_read_value(idx, data, strings, type_refs)
        field_order.append(key_name)

    # --- Fallback: try secondary rows for any None entries ---
    if None in field_order:
        for alt_row_pos in reversed(full_row_positions[:-1]):
            alt_idx = alt_row_pos - 2
            alt_size = data[alt_idx] if alt_idx >= 0 else 0
            if not isinstance(alt_size, int) or alt_size != size_right:
                continue
            alt_idx -= 1
            for pair_num in range(alt_size):
                if alt_idx < 0:
                    break
                key_name, alt_idx, _ = _rtl_read_key(
                    alt_idx, data, strings, type_refs
                )
                _, alt_idx = _rtl_read_value(
                    alt_idx, data, strings, type_refs
                )
                if pair_num < len(field_order) and field_order[pair_num] is None:
                    if key_name is not None:
                        field_order[pair_num] = key_name
            if None not in field_order:
                break

    # Filter out None entries and type identifiers
    result: list[str] = [
        name
        for name in field_order
        if name is not None and not _is_type_identifier(name)
    ]

    log.info("discover_field_names: discovered %d fields: %s", len(result), result)
    return result


# ---------------------------------------------------------------------------
# ViewToken extraction
# ---------------------------------------------------------------------------


def extract_view_token(response_text: str) -> str | None:
    """Extract the ViewToken UUID from a GWT RPC response.

    The ViewToken is a UUID that follows the ``ViewToken/XXXXXXXXXX``
    type descriptor in the string table.

    Args:
        response_text: Full ``//OK[...]`` response body.

    Returns:
        UUID string, or None if not found.
    """
    try:
        parsed = parse_gwt_response(response_text)
    except (GwtParseError, ValueError):
        return None

    strings: list[str] = parsed["strings"]
    for idx, s in enumerate(strings):
        if "ViewToken" in s and "/" in s:
            # The UUID should be the next string-table entry.
            if idx + 1 < len(strings):
                candidate: str = strings[idx + 1]
                if _UUID_RE.match(candidate):
                    return candidate
            # Also scan forward a bit more in case there is an
            # intervening type string.
            for scan_offset in range(2, min(6, len(strings) - idx)):
                fwd_candidate: str = strings[idx + scan_offset]
                if _UUID_RE.match(fwd_candidate):
                    return fwd_candidate
            break

    # Brute-force: look for any UUID in the string table.
    for s in strings:
        if _UUID_RE.match(s):
            return s

    return None


# ---------------------------------------------------------------------------
# Total-count extraction
# ---------------------------------------------------------------------------


def extract_total_count(response_text: str) -> int:
    """Extract the total row count from a GWT response.

    The total count appears near the Row/ViewPage metadata in the data
    section.  In RunReportCommand responses, it is written as part of
    the ViewPage serialisation, typically adjacent to the page-size
    value (25) and the ViewToken.

    Strategy:
    1.  Look for a ViewPage type ref in the data.
    2.  The total count is the integer immediately following the
        page-size (25) in the ViewPage structure.
    3.  Fallback: find the smallest integer > len(strings) and
        < 10_000_000 that looks like a row count.

    Args:
        response_text: Full ``//OK[...]`` response body.

    Returns:
        Total row count (0 if it cannot be determined).
    """
    try:
        parsed = parse_gwt_response(response_text)
    except (GwtParseError, ValueError):
        return 0

    data = parsed["data"]
    strings = parsed["strings"]
    num_strings = len(strings)

    # Find ViewPage type ref
    vp_ref = None
    for i, s in enumerate(strings):
        if "ViewPage" in s and "/" in s:
            vp_ref = i + 1
            break

    # Look for pattern near ViewPage: ..., page_size(25), ViewPage_ref, ...
    # The total count appears near the page size in the ViewPage structure.
    if vp_ref is not None:
        for i, v in enumerate(data):
            if v == vp_ref:
                # Search nearby for a plausible count
                # In the RTL data layout, look LEFT of ViewPage ref
                # Pattern: ..., total_count, 25, ViewToken_ref, ViewPage_ref
                window = data[max(0, i - 5) : i]
                for w in window:
                    if isinstance(w, int) and num_strings < w < 10_000_000:
                        return w

    # Fallback: find the smallest plausible count (> string table size,
    # < 10M, not a known artifact value).
    candidates: list[int] = []
    for val in data:
        if isinstance(val, int) and num_strings < val < 10_000_000:
            # Skip common artifact values
            if val > 100:
                candidates.append(val)

    if candidates:
        # The total count is the SMALLEST plausible candidate
        # (larger values are typically object IDs or timestamps).
        return min(candidates)

    return 0


# ---------------------------------------------------------------------------
# Convenience: parse + paginate (for use by scrape_informer.py)
# ---------------------------------------------------------------------------


def parse_page_response(
    response_text: str,
    field_names: list[str],
) -> dict[str, Any]:
    """Parse a single getData page response into a structured result.

    Combines ``parse_gwt_response``, ``extract_rows``, and token/count
    extraction into one call.

    Args:
        response_text: Full ``//OK[...]`` response body.
        field_names: Column field names for this report.

    Returns:
        Dict with keys:
            * ``rows``        -- list[dict]
            * ``view_token``  -- str | None
            * ``total_count`` -- int
            * ``strings``     -- list[str]  (for debugging)
            * ``data``        -- list       (for debugging)
    """
    parsed = parse_gwt_response(response_text)
    rows = _extract_rows_rtl(
        parsed["strings"],
        parsed["data"],
        field_names,
    )
    view_token = extract_view_token(response_text)
    total_count = extract_total_count(response_text)

    return {
        "rows": rows,
        "view_token": view_token,
        "total_count": total_count,
        "strings": parsed["strings"],
        "data": parsed["data"],
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Test with real response if available
    real_file = Path(
        r"C:\Scripts\signx-warehouse\warehouse\raw\customer_listing_response.txt"
    )
    if real_file.exists():
        print("=== Testing with real Customer Listing response ===")
        text = real_file.read_text(encoding="utf-8")

        print("\n--- parse_gwt_response ---")
        result = parse_gwt_response(text)
        print(f"  data count : {len(result['data'])}")
        print(f"  strings    : {len(result['strings'])}")

        print("\n--- extract_view_token ---")
        token = extract_view_token(text)
        print(f"  ViewToken: {token}")

        print("\n--- extract_total_count ---")
        count = extract_total_count(text)
        print(f"  Total count: {count}")

        print("\n--- extract_rows (RTL algorithm) ---")
        fields = [
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
        rows = extract_rows(text, fields)
        print(f"  Extracted {len(rows)} rows")
        for i, row in enumerate(rows[:5]):
            non_null = {k: v for k, v in row.items() if v is not None}
            print(f"  Row {i}: {non_null}")

        if rows:
            # Verify known data
            has_data = any(
                row.get("name") and row["name"] != "" for row in rows
            )
            print(f"\n  Rows with name data: {has_data}")
            names = [r.get("name", "") for r in rows if r.get("name")]
            if names:
                print(f"  Sample names: {names[:5]}")
    else:
        print("Real response file not found, running synthetic test")

    # Synthetic test for ViewToken extraction
    sample = (
        '//OK[1,2,3,["com.entrinsik.gwt.data.shared.ViewToken/3777265110",'
        '"90463d2b-7350-4f4e-82da-60fd1779a046"],0,7]'
    )
    token = extract_view_token(sample)
    assert token == "90463d2b-7350-4f4e-82da-60fd1779a046", f"ViewToken test failed: {token}"
    print("\nViewToken extraction: PASS")
    print("All tests complete.")
