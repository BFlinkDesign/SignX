"""
Drawing Search — Searches G: drive (//ES-FS02/Customers2) for sign drawings.

Matches customer names to folder structure, finds PDFs with WO numbers,
classifies sign type from filename, returns latest revisions.

Fuzzy matching: difflib.SequenceMatcher + alias table + multi-folder search.
WO format: MMYY-NNNNN-NN (month-year, sequential, revision)
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional

from sign_types import FILENAME_TYPE_MAP

logger = logging.getLogger("signx-takeoff.drawing_search")

_SMB_TIMEOUT = 3  # seconds -- don't let SMB path checks hang

# Folder listing cache (TTL managed externally; populated on first scan per letter)
_folder_cache: dict[str, list[str]] = {}


def _path_exists_fast(p: Path, timeout: int = _SMB_TIMEOUT) -> bool:
    """Check if a path exists with a timeout. Prevents SMB hangs."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            return pool.submit(p.exists).result(timeout=timeout)
        except (FuturesTimeout, OSError):
            return False

# -- Configuration ------------------------------------------------------------

DRAWINGS_ROOT = Path(os.environ.get("DRAWINGS_ROOT", r"\\ES-FS02\Customers2"))

# Customer name aliases -- maps common short names / abbreviations to
# the canonical folder name on G: drive.  Add entries as needed.
CUSTOMER_ALIASES: dict[str, list[str]] = {
    "cat scale":        ["cat scale company", "catscale", "cat scale co"],
    "thd":              ["the home depot", "home depot"],
    "home depot":       ["the home depot"],
    "dollar general":   ["dollar general corporation", "dg ", "dollar gen"],
    "kfc":              ["kentucky fried chicken", "kfc yum brands"],
    "casey's":          ["caseys general stores", "casey general", "caseys"],
    "mcdonalds":        ["mcdonald's", "mcdonalds corporation", "mcd"],
    "taco bell":        ["taco bell corporation", "tacobell"],
    "walgreens":        ["walgreen co", "walgreen company"],
    "menards":          ["menards inc", "menard inc"],
    "kwik star":        ["kwik trip", "kwikstar", "kwik star inc"],
    "hy-vee":           ["hy vee", "hyvee", "hy-vee inc"],
    "wells fargo":      ["wells fargo bank", "wells fargo & company"],
}

# WO number pattern: MMYY-NNNNN-NN (with optional revision)
WO_PATTERN = re.compile(r"(\d{4})-(\d{4,5})(?:-(\d{2}))?")

# FILENAME_TYPE_MAP imported from sign_types.py (single source of truth)

# Filenames to exclude (not actual sign drawings)
EXCLUDE_PATTERNS = [
    "proposal", "quote", "permit", "contract", "regulation",
    "spec sheet", "skmbt_", "invoice", "receipt", "po ",
    "purchase order", "photo", "survey",
]


@dataclass
class DrawingMatch:
    """A matched drawing file from the G: drive."""
    filename: str
    path: str
    customer_folder: str
    wo_number: Optional[str] = None
    wo_seq: Optional[int] = None
    revision: int = 0
    sign_type_guess: Optional[str] = None
    is_cdr: bool = False
    is_pdf: bool = False
    size_bytes: int = 0


@dataclass
class SearchResult:
    """Results from a drawing search."""
    query: str
    customer_folder: Optional[str] = None
    total_files: int = 0
    drawings: List[DrawingMatch] = field(default_factory=list)
    pdfs: List[DrawingMatch] = field(default_factory=list)
    latest_revisions: List[DrawingMatch] = field(default_factory=list)
    sign_types_found: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _classify_sign_type(filename: str) -> Optional[str]:
    """Guess sign type from filename keywords."""
    lower = filename.lower()
    for keyword, stype in FILENAME_TYPE_MAP.items():
        if keyword in lower:
            return stype
    return None


def _is_drawing(filename: str) -> bool:
    """Filter out non-drawing files."""
    lower = filename.lower()
    for pat in EXCLUDE_PATTERNS:
        if pat in lower:
            return False
    return True


def _parse_wo(filename: str) -> tuple:
    """Extract WO number components from filename."""
    m = WO_PATTERN.search(filename)
    if m:
        mmyy = m.group(1)
        seq = int(m.group(2))
        rev = int(m.group(3)) if m.group(3) else 0
        return f"{mmyy}-{m.group(2)}", seq, rev
    return None, None, 0


def _strip_suffixes(name: str) -> str:
    """Strip common corporate suffixes for matching."""
    for suffix in (" inc", " llc", " corp", " co", " company", " corporation",
                    " enterprises", " industries", " group", " services"):
        if name.endswith(suffix):
            name = name[: -len(suffix)].rstrip()
    return name


def _list_letter_folders(letter_dir: Path) -> list[str]:
    """List folder names under a letter dir, with caching. Uses os.scandir for SMB speed."""
    key = str(letter_dir)
    if key in _folder_cache:
        return _folder_cache[key]
    names: list[str] = []
    try:
        for entry in os.scandir(str(letter_dir)):
            if entry.is_dir(follow_symlinks=False):
                names.append(entry.name)
    except (PermissionError, OSError):
        pass
    _folder_cache[key] = names
    return names


def _resolve_letter_dir(name: str) -> Optional[Path]:
    """Find the letter directory for a given name."""
    first = name[0].upper()
    letter_dir = DRAWINGS_ROOT / first
    if _path_exists_fast(letter_dir):
        return letter_dir
    if name[0].isdigit():
        for d in ["0-9", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            candidate = DRAWINGS_ROOT / d
            if _path_exists_fast(candidate):
                return candidate
    return None


def _score_folder(query_lower: str, query_stripped: str, query_words: list[str],
                  folder_name: str) -> float:
    """Score a folder name against the query. Higher = better match."""
    fl = folder_name.lower()
    fs = _strip_suffixes(fl)

    # Exact match (with or without suffixes)
    if fl == query_lower or fs == query_stripped:
        return 1000.0

    # "starts with" match — very strong signal
    if fl.startswith(query_lower) or fl.startswith(query_stripped):
        return 500.0 + len(query_lower)

    # Word-based scoring
    score = 0.0
    for word in query_words:
        if len(word) >= 2 and word in fl:
            score += len(word) * 3
    # First word bonus
    if query_words and query_words[0] in fl:
        score += 20.0

    # Fuzzy ratio as tiebreaker / catch-all
    ratio = SequenceMatcher(None, query_stripped, fs).ratio()
    score += ratio * 40.0  # 0-40 range

    return score


def find_customer_folder(customer_name: str) -> Optional[Path]:
    """Find the best-matching customer folder on G: drive.

    Uses a multi-strategy approach:
    1. Exact match (fast path)
    2. Alias expansion (CAT Scale → CAT SCALE COMPANY)
    3. Word-based scoring + SequenceMatcher fuzzy ratio
    4. Searches multiple letter dirs if aliases start with different letters
    """
    if not _path_exists_fast(DRAWINGS_ROOT):
        return None

    name = customer_name.strip()
    if not name:
        return None

    name_lower = name.lower()
    name_stripped = _strip_suffixes(name_lower)
    name_words = name_lower.split()

    # Build candidate queries: original name + all aliases
    queries = [name_lower]
    for alias_key, alias_values in CUSTOMER_ALIASES.items():
        if name_lower == alias_key or name_stripped == alias_key:
            queries.extend(alias_values)
        else:
            for av in alias_values:
                if name_lower == av or name_stripped == av:
                    queries.append(alias_key)
                    queries.extend(v for v in alias_values if v != av)
                    break

    # Deduplicate and determine which letter dirs to scan
    queries = list(dict.fromkeys(queries))  # preserve order, dedupe
    letter_dirs_to_scan: dict[str, Path] = {}
    for q in queries:
        if not q:
            continue
        ld = _resolve_letter_dir(q)
        if ld:
            letter_dirs_to_scan[str(ld)] = ld

    if not letter_dirs_to_scan:
        return None

    # Score all folders across all letter dirs
    best_match: Optional[Path] = None
    best_score = 0.0

    for ld in letter_dirs_to_scan.values():
        folder_names = _list_letter_folders(ld)
        for fname in folder_names:
            # Score against every query variant
            top_score = 0.0
            for q in queries:
                q_stripped = _strip_suffixes(q)
                q_words = q.split()
                s = _score_folder(q, q_stripped, q_words, fname)
                if s > top_score:
                    top_score = s
            if top_score > best_score:
                best_score = top_score
                best_match = ld / fname

    # Exact/starts-with matches (score >= 500) always pass.
    # Fuzzy matches need score >= 25 (roughly: first word matched + decent ratio).
    if best_score >= 25.0 and best_match:
        logger.debug("Drawing search: '%s' → '%s' (score=%.1f)", customer_name, best_match.name, best_score)
        return best_match
    return None


def clear_folder_cache():
    """Clear the folder listing cache (call if G: drive contents change)."""
    _folder_cache.clear()


def search_drawings(
    customer_name: str,
    sign_type_filter: Optional[str] = None,
    wo_number: Optional[str] = None,
    max_results: int = 50,
    max_depth: int = 3,
) -> SearchResult:
    """Search G: drive for drawings matching a customer and optional filters.

    Args:
        customer_name: Customer name to search for
        sign_type_filter: Optional sign type to filter by (monument, pylon, etc.)
        wo_number: Optional specific WO number to find
        max_results: Maximum drawings to return
        max_depth: How deep to recurse into subfolders
    """
    result = SearchResult(query=customer_name)

    if not _path_exists_fast(DRAWINGS_ROOT):
        result.warnings.append(f"Drawing root not accessible: {DRAWINGS_ROOT}")
        return result

    # Find the customer folder
    folder = find_customer_folder(customer_name)
    if not folder:
        result.warnings.append(f"No matching folder found for '{customer_name}' on G: drive")
        return result

    result.customer_folder = str(folder)

    # Scan for drawing files
    all_matches = []
    sign_types_seen = set()

    def scan_dir(dirpath: Path, depth: int):
        if depth > max_depth:
            return
        try:
            for entry in os.scandir(str(dirpath)):
                if entry.is_dir(follow_symlinks=False):
                    scan_dir(Path(entry.path), depth + 1)
                elif entry.is_file(follow_symlinks=False):
                    result.total_files += 1
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext not in (".pdf", ".cdr", ".ai", ".eps", ".dxf", ".dwg"):
                        continue
                    if not _is_drawing(entry.name):
                        continue

                    wo, wo_seq, rev = _parse_wo(entry.name)
                    stype = _classify_sign_type(entry.name)

                    # Apply filters
                    if wo_number and wo and wo_number not in wo:
                        continue
                    if sign_type_filter and stype and stype != sign_type_filter:
                        continue

                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = 0

                    match = DrawingMatch(
                        filename=entry.name,
                        path=entry.path,
                        customer_folder=folder.name,
                        wo_number=wo,
                        wo_seq=wo_seq,
                        revision=rev,
                        sign_type_guess=stype,
                        is_cdr=(ext == ".cdr"),
                        is_pdf=(ext == ".pdf"),
                        size_bytes=size,
                    )
                    all_matches.append(match)
                    if stype:
                        sign_types_seen.add(stype)
        except PermissionError:
            pass

    scan_dir(folder, 0)

    # Sort by WO sequence (newest first), then revision (highest first)
    all_matches.sort(
        key=lambda m: (m.wo_seq or 0, m.revision),
        reverse=True,
    )

    result.drawings = all_matches[:max_results]
    result.pdfs = [m for m in all_matches if m.is_pdf][:max_results]
    result.sign_types_found = sorted(sign_types_seen)

    # Find latest revision per WO number
    latest_by_wo = {}
    for m in all_matches:
        if m.wo_number and m.is_pdf:
            if m.wo_number not in latest_by_wo or m.revision > latest_by_wo[m.wo_number].revision:
                latest_by_wo[m.wo_number] = m
    result.latest_revisions = sorted(
        latest_by_wo.values(),
        key=lambda m: m.wo_seq or 0,
        reverse=True,
    )

    return result


def search_for_bid(
    customer_name: str,
    sign_type: Optional[str] = None,
    sq_ft: Optional[float] = None,
) -> SearchResult:
    """High-level search optimized for bid pipeline integration.

    Maps Notion sign types to filename search types.
    """
    # Map Notion sign types to filename classification
    type_map = {
        "EMC_POLE": "pylon",
        "EMC_MONUMENT": "monument",
        "EMC_RETROFIT": "cabinet",
        "EMC": "pylon",
        "CHANNEL_LETTERS": "channel_letter",
        "CHANNEL_LOGO": "channel_letter",
        "MONUMENT_BASE": "monument",
        "MONUMENT_MANUAL_READER": "monument",
        "CABINET_ILLUMINATED": "cabinet",
        "INFO_PANEL": "directional",
        "REMOVAL": "removal",
        "STRUCTURAL_BASE": None,
        "MASONRY_SUB": None,
    }
    filter_type = type_map.get(sign_type) if sign_type else None

    return search_drawings(
        customer_name=customer_name,
        sign_type_filter=filter_type,
        max_results=25,
    )
