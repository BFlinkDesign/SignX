"""
Drawing Search — Searches G: drive (//ES-FS02/Customers2) for sign drawings.

Matches customer names to folder structure, finds PDFs with WO numbers,
classifies sign type from filename, returns latest revisions.

WO format: MMYY-NNNNN-NN (month-year, sequential, revision)
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_SMB_TIMEOUT = 3  # seconds — don't let SMB path checks hang


def _path_exists_fast(p: Path, timeout: int = _SMB_TIMEOUT) -> bool:
    """Check if a path exists with a timeout. Prevents SMB hangs."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            return pool.submit(p.exists).result(timeout=timeout)
        except (FuturesTimeout, OSError):
            return False

# ── Configuration ────────────────────────────────────────────────────────────

DRAWINGS_ROOT = Path(os.environ.get("DRAWINGS_ROOT", r"\\ES-FS02\Customers2"))

# WO number pattern: MMYY-NNNNN-NN (with optional revision)
WO_PATTERN = re.compile(r"(\d{4})-(\d{4,5})(?:-(\d{2}))?")

# Sign type keywords found in filenames → estimator type
FILENAME_TYPE_MAP = {
    "monument":         "monument",
    "mon face":         "monument",
    "mon ":             "monument",
    "pylon":            "pylon",
    "pole sign":        "pylon",
    "pole face":        "pylon",
    "channel let":      "channel_letter",
    "channel lit":      "channel_letter",
    "letters":          "channel_letter",
    "emc":              "pylon",
    "emcenter":         "pylon",
    "electronic":       "pylon",
    "awning":           "awning",
    "canopy":           "awning",
    "cabinet":          "cabinet",
    "lightbox":         "cabinet",
    "light box":        "cabinet",
    "dimensional":      "dimensional",
    "gemini":           "dimensional",
    "flat cut":         "dimensional",
    "directional":      "directional",
    "wayfinding":       "directional",
    "info panel":       "directional",
    "removal":          "removal",
    "remove":           "removal",
}

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


def find_customer_folder(customer_name: str) -> Optional[Path]:
    """Find the best-matching customer folder on G: drive.

    Searches by first letter, then fuzzy-matches folder names.
    """
    if not _path_exists_fast(DRAWINGS_ROOT):
        return None

    # Normalize: strip common suffixes, get first letter
    name = customer_name.strip()
    if not name:
        return None

    first_letter = name[0].upper()

    # Try letter folder first
    letter_dir = DRAWINGS_ROOT / first_letter
    if not _path_exists_fast(letter_dir):
        # Try numeric folders
        if name[0].isdigit():
            for d in ["0-9", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                if (DRAWINGS_ROOT / d).exists():
                    letter_dir = DRAWINGS_ROOT / d
                    break
        if not _path_exists_fast(letter_dir):
            return None

    # Search for matching folder
    name_lower = name.lower()
    name_words = name_lower.split()

    best_match = None
    best_score = 0

    try:
        for folder in letter_dir.iterdir():
            if not folder.is_dir():
                continue
            folder_lower = folder.name.lower()

            # Exact match
            if folder_lower == name_lower:
                return folder

            # Word-based scoring
            score = 0
            for word in name_words:
                if len(word) >= 3 and word in folder_lower:
                    score += len(word)

            # First word match bonus (most important)
            if name_words and name_words[0] in folder_lower:
                score += 10

            if score > best_score:
                best_score = score
                best_match = folder
    except PermissionError:
        pass

    # Require minimum match quality
    if best_score >= 10:
        return best_match
    return None


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
