"""
project_files.py — Full project file scanner for G: drive.

Unlike drawing_search.py (which filters for sign drawings only), this module
finds and classifies ALL project files: drawings, proposals, permits, photos,
contracts, invoices, specs — everything needed for a complete project dossier.

Each file gets:
  - document_type classification (drawing, proposal, permit, photo, etc.)
  - WO number extraction (strongest link key)
  - sign type guess (from filename keywords)
  - confidence score for project relevance
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from sign_types import FILENAME_TYPE_MAP as SIGN_TYPE_MAP

logger = logging.getLogger(__name__)

_SMB_TIMEOUT = 3  # seconds — don't let SMB path checks hang
_CACHE_TTL = 300  # 5 minutes — re-scan after this many seconds


def _path_exists_fast(p: Path, timeout: int = _SMB_TIMEOUT) -> bool:
    """Check if a path exists with a timeout. Prevents SMB hangs."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            return pool.submit(p.exists).result(timeout=timeout)
        except (FuturesTimeout, OSError):
            return False


# ── In-Memory Cache ──────────────────────────────────────────────────────────
# Full scan results cached per customer. Background refresh keeps data fresh
# without blocking API responses. First request triggers a full scan in a
# background thread; subsequent requests serve from cache instantly.

_cache: dict[str, tuple[float, "DossierFiles"]] = {}  # key -> (timestamp, result)
_cache_lock = threading.Lock()
_bg_scans: set[str] = set()  # customers currently being scanned in background
_bg_lock = threading.Lock()

# ── Configuration ────────────────────────────────────────────────────────────

DRAWINGS_ROOT = Path(os.environ.get("DRAWINGS_ROOT", r"\\ES-FS02\Customers2"))

# WO number pattern: MMYY-NNNNN-NN (with optional revision)
WO_PATTERN = re.compile(r"(\d{4})-(\d{4,5})(?:-(\d{2}))?")

# ── Document Type Classification ─────────────────────────────────────────────
# Keywords in filename → document type. First match wins.

DOC_TYPE_RULES: list[tuple[str, list[str]]] = [
    # Proposals and quotes
    ("proposal", ["proposal", "quote ", "quotation", "pricing", "bid "]),
    # Permits
    ("permit", ["permit", "variance", "zoning", "municipal", "city of"]),
    # Contracts and POs
    ("contract", ["contract", "agreement", "purchase order", "po ", "signed"]),
    # Photos and surveys
    ("photo", ["photo", "image", "img_", "img-", "dsc_", "dsc-", "pic_", "pic-",
               "camera", "iphone", "samsung", "snapshot"]),
    ("survey", ["survey", "site visit", "field", "existing"]),
    # Invoices and billing
    ("invoice", ["invoice", "receipt", "billing", "payment"]),
    # Spec sheets
    ("spec", ["spec sheet", "specification", "data sheet", "technical",
              "product data", "cut sheet"]),
    # Regulatory
    ("regulation", ["regulation", "code", "ordinance", "requirement"]),
    # Correspondence
    ("correspondence", ["letter ", "memo", "email", "fax"]),
    # Scanner artifacts (skip these in relevance scoring)
    ("scan_artifact", ["skmbt_", "scan_", "scanned"]),
]

# SIGN_TYPE_MAP imported from sign_types.py (single source of truth)

# Design file extensions (these are sign design source files)
DESIGN_EXTENSIONS = {".cdr", ".ai", ".eps", ".dxf", ".dwg", ".svg"}
# Document extensions
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".rtf"}
# Image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp", ".heic"}
# All extensions we care about
ALL_EXTENSIONS = DESIGN_EXTENSIONS | DOC_EXTENSIONS | IMAGE_EXTENSIONS

# Document type display labels and icons
DOC_TYPE_LABELS = {
    "drawing":        "Sign Drawing",
    "drawing_pdf":    "Drawing PDF",
    "proposal":       "Proposal/Quote",
    "permit":         "Permit",
    "contract":       "Contract/PO",
    "photo":          "Photo",
    "survey":         "Site Survey",
    "invoice":        "Invoice",
    "spec":           "Spec Sheet",
    "regulation":     "Regulation",
    "correspondence": "Correspondence",
    "scan_artifact":  "Scan",
    "unknown":        "Document",
}

# What a COMPLETE project dossier should have
DOSSIER_CHECKLIST = [
    ("drawing",     "Sign drawings (CDR/AI/PDF)"),
    ("proposal",    "Proposal or quote"),
    ("contract",    "Signed contract or PO"),
    ("permit",      "Permit (if required)"),
    ("photo",       "Site photos"),
]


@dataclass
class ProjectFile:
    """A classified file from the project folder."""
    filename: str
    path: str
    customer_folder: str
    doc_type: str               # drawing, proposal, permit, photo, etc.
    doc_type_label: str         # Human-readable label
    wo_number: Optional[str] = None
    wo_seq: Optional[int] = None
    revision: int = 0
    sign_type: Optional[str] = None
    ext: str = ""
    size_bytes: int = 0
    modified: Optional[str] = None  # ISO timestamp
    subfolder: str = ""         # Relative path within customer folder
    relevance: float = 1.0     # 0-1 confidence this belongs to the project


@dataclass
class DossierFiles:
    """Complete file scan results for a project dossier."""
    query: str
    customer_folder: Optional[str] = None
    total_files_scanned: int = 0
    files: list[ProjectFile] = field(default_factory=list)
    by_type: dict[str, list[ProjectFile]] = field(default_factory=dict)
    sign_types_found: list[str] = field(default_factory=list)
    wo_numbers_found: list[str] = field(default_factory=list)
    # Completeness checklist
    checklist: list[dict] = field(default_factory=list)
    completeness_pct: float = 0.0
    warnings: list[str] = field(default_factory=list)


def _classify_doc_type(filename: str, ext: str) -> str:
    """Classify a file into a document type based on filename and extension."""
    lower = filename.lower()

    # Design files are always drawings
    if ext in DESIGN_EXTENSIONS:
        return "drawing"

    # Check keyword rules
    for doc_type, keywords in DOC_TYPE_RULES:
        for kw in keywords:
            if kw in lower:
                return doc_type

    # Images without photo keywords — could be drawings or photos
    if ext in IMAGE_EXTENSIONS:
        # If it has a WO number, probably a drawing render/proof
        if WO_PATTERN.search(filename):
            return "drawing_pdf"
        return "photo"

    # PDFs without classification keywords
    if ext == ".pdf":
        # If it has sign type keywords, it's a drawing PDF
        for kw in SIGN_TYPE_MAP:
            if kw in lower:
                return "drawing_pdf"
        # If it has a WO number, likely a drawing
        if WO_PATTERN.search(filename):
            return "drawing_pdf"
        return "unknown"

    return "unknown"


def _classify_sign_type(filename: str) -> Optional[str]:
    """Guess sign type from filename keywords."""
    lower = filename.lower()
    for keyword, stype in SIGN_TYPE_MAP.items():
        if keyword in lower:
            return stype
    return None


def _parse_wo(filename: str) -> tuple:
    """Extract WO number components from filename."""
    m = WO_PATTERN.search(filename)
    if m:
        mmyy = m.group(1)
        seq = int(m.group(2))
        rev = int(m.group(3)) if m.group(3) else 0
        return f"{mmyy}-{m.group(2)}", seq, rev
    return None, None, 0


def _score_relevance(pfile: ProjectFile, target_wo: Optional[str] = None,
                     target_sign_type: Optional[str] = None) -> float:
    """Score how relevant this file is to the target project (0-1)."""
    score = 0.5  # Base: it's in the customer folder

    # WO match is the strongest signal
    if target_wo and pfile.wo_number:
        if target_wo in pfile.wo_number or pfile.wo_number in target_wo:
            score = 1.0
        else:
            score -= 0.1  # Different WO = slightly less relevant

    # Sign type match
    if target_sign_type and pfile.sign_type:
        if pfile.sign_type == target_sign_type:
            score = min(score + 0.2, 1.0)
        else:
            score -= 0.05

    # Design files are always highly relevant
    if pfile.doc_type in ("drawing", "drawing_pdf"):
        score = min(score + 0.15, 1.0)

    # Scan artifacts are low relevance
    if pfile.doc_type == "scan_artifact":
        score = max(score - 0.3, 0.1)

    return round(max(0.0, min(1.0, score)), 2)


def find_customer_folder(customer_name: str) -> Optional[Path]:
    """Find the best-matching customer folder on G: drive.

    Uses word-based fuzzy matching with first-word bonus.
    Returns None if no confident match found.
    """
    if not _path_exists_fast(DRAWINGS_ROOT):
        return None

    name = customer_name.strip()
    if not name:
        return None

    first_letter = name[0].upper()

    # Try letter folder first
    letter_dir = DRAWINGS_ROOT / first_letter
    if not _path_exists_fast(letter_dir):
        if name[0].isdigit():
            for d in ["0-9", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                if (DRAWINGS_ROOT / d).exists():
                    letter_dir = DRAWINGS_ROOT / d
                    break
        if not _path_exists_fast(letter_dir):
            return None

    name_lower = name.lower()
    # Strip common suffixes for better matching
    for suffix in [" inc", " inc.", " llc", " corp", " co.", " co", " ltd"]:
        if name_lower.endswith(suffix):
            name_lower = name_lower[: -len(suffix)].strip()
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

            # Check with suffix stripping on folder too
            folder_stripped = folder_lower
            for suffix in [" inc", " inc.", " llc", " corp", " co.", " co", " ltd"]:
                if folder_stripped.endswith(suffix):
                    folder_stripped = folder_stripped[: -len(suffix)].strip()

            if folder_stripped == name_lower:
                return folder

            # Word-based scoring
            score = 0
            for word in name_words:
                if len(word) >= 3 and word in folder_lower:
                    score += len(word)

            # First word match bonus (most important — "Casey's" in "Casey's General Stores")
            if name_words and len(name_words[0]) >= 3 and name_words[0] in folder_lower:
                score += 10

            # Penalize if folder has totally different first word
            folder_words = folder_stripped.split()
            if folder_words and name_words:
                if folder_words[0] != name_words[0] and name_words[0] not in folder_lower:
                    score = max(0, score - 5)

            if score > best_score:
                best_score = score
                best_match = folder
    except PermissionError:
        pass

    if best_score >= 10:
        return best_match
    return None


def _full_scan(
    customer_name: str,
    folder: Path,
    wo_number: Optional[str] = None,
    sign_type: Optional[str] = None,
    max_depth: int = 3,
    max_files: int = 200,
) -> DossierFiles:
    """Internal: full recursive scan (runs in background thread for cache)."""
    result = DossierFiles(query=customer_name)
    result.customer_folder = str(folder)

    all_files: list[ProjectFile] = []
    sign_types_seen: set[str] = set()
    wo_numbers_seen: set[str] = set()

    def scan_dir(dirpath: Path, depth: int, rel_path: str):
        if depth > max_depth:
            return
        try:
            for entry in os.scandir(str(dirpath)):
                if entry.is_dir(follow_symlinks=False):
                    subrel = f"{rel_path}/{entry.name}" if rel_path else entry.name
                    scan_dir(Path(entry.path), depth + 1, subrel)
                elif entry.is_file(follow_symlinks=False):
                    result.total_files_scanned += 1
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext not in ALL_EXTENSIONS:
                        continue

                    wo, wo_seq, rev = _parse_wo(entry.name)
                    stype = _classify_sign_type(entry.name)
                    doc_type = _classify_doc_type(entry.name, ext)

                    try:
                        stat = entry.stat()
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    except OSError:
                        size = 0
                        mtime = None

                    pf = ProjectFile(
                        filename=entry.name,
                        path=entry.path,
                        customer_folder=folder.name,
                        doc_type=doc_type,
                        doc_type_label=DOC_TYPE_LABELS.get(doc_type, "Document"),
                        wo_number=wo,
                        wo_seq=wo_seq,
                        revision=rev,
                        sign_type=stype,
                        ext=ext,
                        size_bytes=size,
                        modified=mtime,
                        subfolder=rel_path,
                    )
                    pf.relevance = _score_relevance(pf, wo_number, sign_type)

                    all_files.append(pf)
                    if stype:
                        sign_types_seen.add(stype)
                    if wo:
                        wo_numbers_seen.add(wo)
        except PermissionError:
            pass

    scan_dir(folder, 0, "")

    # Sort: highest relevance first, then newest first (by WO seq)
    all_files.sort(key=lambda f: (f.relevance, f.wo_seq or 0), reverse=True)

    result.files = all_files[:max_files]
    result.sign_types_found = sorted(sign_types_seen)
    result.wo_numbers_found = sorted(wo_numbers_seen, reverse=True)

    # Group by document type
    by_type: dict[str, list[ProjectFile]] = {}
    for pf in result.files:
        by_type.setdefault(pf.doc_type, []).append(pf)
    result.by_type = by_type

    # Completeness checklist
    found_types = set(by_type.keys())
    checklist = []
    found_count = 0
    for dtype, label in DOSSIER_CHECKLIST:
        found = dtype in found_types or (
            dtype == "drawing" and "drawing_pdf" in found_types
        )
        count = len(by_type.get(dtype, [])) + (
            len(by_type.get("drawing_pdf", [])) if dtype == "drawing" else 0
        )
        checklist.append({
            "type": dtype,
            "label": label,
            "found": found,
            "count": count,
        })
        if found:
            found_count += 1

    result.checklist = checklist
    result.completeness_pct = round(
        (found_count / len(DOSSIER_CHECKLIST)) * 100, 0
    ) if DOSSIER_CHECKLIST else 0

    return result


def _bg_refresh(cache_key: str, customer_name: str, folder: Path,
                wo_number: Optional[str], sign_type: Optional[str],
                max_depth: int, max_files: int):
    """Background thread: full scan → cache update."""
    try:
        result = _full_scan(customer_name, folder, wo_number, sign_type,
                            max_depth, max_files)
        with _cache_lock:
            _cache[cache_key] = (_time.monotonic(), result)
        logger.info("Cache refreshed for '%s': %d files in %d scanned",
                     customer_name, len(result.files), result.total_files_scanned)
    except Exception:
        logger.exception("Background scan failed for '%s'", customer_name)
    finally:
        with _bg_lock:
            _bg_scans.discard(cache_key)


def scan_project_files(
    customer_name: str,
    wo_number: Optional[str] = None,
    sign_type: Optional[str] = None,
    max_depth: int = 3,
    max_files: int = 200,
) -> DossierFiles:
    """Scan G: drive for ALL project files, classified by document type.

    Uses a 5-minute in-memory cache. First call for a customer triggers a
    full background scan and returns immediately with a "loading" result.
    Subsequent calls serve from cache instantly while background refresh
    keeps data fresh.

    Args:
        customer_name: Customer name to find folder for
        wo_number: Optional WO number to boost relevance scoring
        sign_type: Optional sign type to boost relevance scoring
        max_depth: How deep to recurse into subfolders
        max_files: Maximum files to return
    """
    result = DossierFiles(query=customer_name)

    # Fast path: check cache BEFORE any SMB/network calls
    norm_key = f"{customer_name.strip().lower()}|{wo_number or ''}|{sign_type or ''}"
    with _cache_lock:
        if norm_key in _cache:
            ts, cached = _cache[norm_key]
            age = _time.monotonic() - ts
            if age < _CACHE_TTL:
                return cached  # instant cache hit — zero network I/O
            # Stale but usable — return immediately, refresh in background
            # (need folder for bg refresh, but don't block on it)
            folder_str = cached.customer_folder
            if folder_str:
                _trigger_bg_scan(norm_key, customer_name, Path(folder_str),
                                 wo_number, sign_type, max_depth, max_files)
            return cached

    # Cache miss — must do network calls
    if not _path_exists_fast(DRAWINGS_ROOT):
        result.warnings.append(f"G: drive not accessible: {DRAWINGS_ROOT}")
        return result

    folder = find_customer_folder(customer_name)
    if not folder:
        result.warnings.append(
            f"No matching folder found for '{customer_name}' on G: drive"
        )
        return result

    # Synchronous full scan for first request — user gets COMPLETE results
    full_result = _full_scan(customer_name, folder, wo_number, sign_type,
                             max_depth, max_files)

    # Store in cache for subsequent requests
    with _cache_lock:
        _cache[norm_key] = (_time.monotonic(), full_result)

    return full_result


def _trigger_bg_scan(cache_key: str, customer_name: str, folder: Path,
                     wo_number: Optional[str], sign_type: Optional[str],
                     max_depth: int, max_files: int):
    """Launch a background scan if one isn't already running."""
    with _bg_lock:
        if cache_key in _bg_scans:
            return  # already scanning
        _bg_scans.add(cache_key)
    t = threading.Thread(
        target=_bg_refresh,
        args=(cache_key, customer_name, folder, wo_number, sign_type,
              max_depth, max_files),
        daemon=True,
    )
    t.start()
