"""
Section catalog for AISC 360-22 member design.

Loads from data/standards/aisc_shapes.json if present;
falls back to the hardcoded catalog below.

Families:
  pipe        – Round pipe (A53 Gr B, Fy=35 ksi)
  W           – Wide-flange (A992, Fy=50 ksi)
  HSS_square  – Square HSS (A500 Gr C, Fy=46 ksi)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section dataclass
# ---------------------------------------------------------------------------

@dataclass
class Section:
    family: str
    designation: str
    weight_plf: float          # weight per linear foot (lb/ft)
    A_in2: float = 0.0
    d_in: float = 0.0
    bf_in: float = 0.0
    tf_in: float = 0.0
    tw_in: float = 0.0
    Ix_in4: float = 0.0
    Iy_in4: float = 0.0
    Sx_in3: float = 0.0
    Sy_in3: float = 0.0
    Zx_in3: float = 0.0
    Zy_in3: float = 0.0
    rx_in: float = 0.0
    ry_in: float = 0.0
    J_in4: float = 0.0
    Cw_in6: float = 0.0
    Fy_ksi: float = 50.0
    Fu_ksi: float = 65.0

    # ------------------------------------------------------------------
    # Backward-compatibility shims
    # ------------------------------------------------------------------
    @property
    def weight_lbf(self) -> float:
        """Alias kept for legacy callers (was the primary field name)."""
        return self.weight_plf

    @property
    def fy_psi(self) -> float:
        """Legacy callers expect stress in psi."""
        return self.Fy_ksi * 1000.0


# ---------------------------------------------------------------------------
# Hardcoded fallback catalog
# ---------------------------------------------------------------------------

def _pipe(desig: str, weight: float, OD: float, tw: float,
          A: float, Ix: float, Sx: float, Zx: float,
          rx: float, J: float, Fy: float = 35.0, Fu: float = 60.0) -> Section:
    """Helper: pipes are symmetric so Iy=Ix, Sy=Sx, Zy=Zx, ry=rx."""
    return Section(
        family="pipe",
        designation=desig,
        weight_plf=weight,
        A_in2=A,
        d_in=OD,
        bf_in=0.0,
        tf_in=0.0,
        tw_in=tw,
        Ix_in4=Ix,
        Iy_in4=Ix,
        Sx_in3=Sx,
        Sy_in3=Sx,
        Zx_in3=Zx,
        Zy_in3=Zx,
        rx_in=rx,
        ry_in=rx,
        J_in4=J,
        Cw_in6=0.0,
        Fy_ksi=Fy,
        Fu_ksi=Fu,
    )


def _w(desig: str, weight: float,
       A: float, d: float, bf: float, tf: float, tw: float,
       Ix: float, Sx: float, Zx: float,
       Iy: float, Sy: float, Zy: float,
       rx: float, ry: float,
       J: float, Cw: float = 0.0,
       Fy: float = 50.0, Fu: float = 65.0) -> Section:
    return Section(
        family="W",
        designation=desig,
        weight_plf=weight,
        A_in2=A,
        d_in=d,
        bf_in=bf,
        tf_in=tf,
        tw_in=tw,
        Ix_in4=Ix,
        Iy_in4=Iy,
        Sx_in3=Sx,
        Sy_in3=Sy,
        Zx_in3=Zx,
        Zy_in3=Zy,
        rx_in=rx,
        ry_in=ry,
        J_in4=J,
        Cw_in6=Cw,
        Fy_ksi=Fy,
        Fu_ksi=Fu,
    )


def _hss_sq(desig: str, weight: float,
            d: float, tw: float,
            A: float, Ix: float, Sx: float, Zx: float,
            J: float,
            Fy: float = 46.0, Fu: float = 62.0) -> Section:
    """Square HSS – symmetric: bf=d, tf=tw, Iy=Ix, etc."""
    rx = (Ix / A) ** 0.5 if A > 0 else 0.0
    return Section(
        family="HSS_square",
        designation=desig,
        weight_plf=weight,
        A_in2=A,
        d_in=d,
        bf_in=d,
        tf_in=tw,
        tw_in=tw,
        Ix_in4=Ix,
        Iy_in4=Ix,
        Sx_in3=Sx,
        Sy_in3=Sx,
        Zx_in3=Zx,
        Zy_in3=Zx,
        rx_in=rx,
        ry_in=rx,
        J_in4=J,
        Cw_in6=0.0,
        Fy_ksi=Fy,
        Fu_ksi=Fu,
    )


# fmt: off
_HARDCODED_CATALOG: List[Section] = [
    # ----------------------------------------------------------------
    # Pipe – Schedule 40, ASTM A53 Gr B, Fy=35 ksi
    # Source: AISC Steel Construction Manual, Table 1-14
    # ----------------------------------------------------------------
    _pipe("Pipe3STD",  7.58,  OD=3.500, tw=0.216, A=2.23, Ix=3.02,  Sx=1.72,  Zx=2.39,  rx=1.16, J=6.03),
    _pipe("Pipe4STD",  10.79, OD=4.500, tw=0.237, A=3.17, Ix=7.23,  Sx=3.21,  Zx=4.31,  rx=1.51, J=14.5),
    _pipe("Pipe5STD",  14.62, OD=5.563, tw=0.258, A=4.30, Ix=15.2,  Sx=5.45,  Zx=7.31,  rx=1.88, J=30.3),
    _pipe("Pipe6STD",  18.97, OD=6.625, tw=0.280, A=5.58, Ix=28.1,  Sx=8.50,  Zx=11.3,  rx=2.25, J=56.3),
    _pipe("Pipe8STD",  28.55, OD=8.625, tw=0.322, A=8.40, Ix=72.5,  Sx=16.8,  Zx=22.2,  rx=2.94, J=145.0),
    _pipe("Pipe10STD", 40.48, OD=10.75, tw=0.365, A=11.9, Ix=161.0, Sx=29.9,  Zx=39.4,  rx=3.67, J=321.0),
    _pipe("Pipe12STD", 49.56, OD=12.75, tw=0.375, A=14.6, Ix=279.0, Sx=43.8,  Zx=57.5,  rx=4.38, J=559.0),

    # ----------------------------------------------------------------
    # W-shapes – ASTM A992, Fy=50 ksi
    # Source: AISC Steel Construction Manual, 16th Ed., Table 1-1
    # ----------------------------------------------------------------
    _w("W8x18",  18.0, A=5.26,  d=8.14,  bf=5.250,  tf=0.330, tw=0.230,
       Ix=61.9,  Sx=15.2, Zx=17.0,  Iy=7.97,  Sy=3.04,  Zy=4.66,
       rx=3.43,  ry=1.23, J=0.172, Cw=555.0),
    _w("W8x31",  31.0, A=9.13,  d=8.00,  bf=7.995,  tf=0.435, tw=0.285,
       Ix=110.0, Sx=27.5, Zx=30.4,  Iy=37.1,  Sy=9.27,  Zy=14.1,
       rx=3.47,  ry=2.02, J=0.536, Cw=1550.0),
    _w("W10x22", 22.0, A=6.49,  d=10.17, bf=5.750,  tf=0.360, tw=0.240,
       Ix=118.0, Sx=23.2, Zx=26.0,  Iy=11.4,  Sy=3.97,  Zy=6.10,
       rx=4.27,  ry=1.33, J=0.239, Cw=1550.0),
    _w("W12x26", 26.0, A=7.65,  d=12.22, bf=6.490,  tf=0.380, tw=0.230,
       Ix=204.0, Sx=33.4, Zx=37.2,  Iy=17.3,  Sy=5.34,  Zy=8.17,
       rx=5.17,  ry=1.51, J=0.300, Cw=3160.0),
    _w("W14x22", 22.0, A=6.49,  d=13.74, bf=5.000,  tf=0.335, tw=0.230,
       Ix=199.0, Sx=29.0, Zx=33.2,  Iy=7.00,  Sy=2.80,  Zy=4.39,
       rx=5.54,  ry=1.04, J=0.208, Cw=2110.0),

    # ----------------------------------------------------------------
    # HSS Square – ASTM A500 Gr C, Fy=46 ksi
    # Source: AISC Steel Construction Manual, 16th Ed., Table 1-12
    # ----------------------------------------------------------------
    _hss_sq("HSS4x4x3/16",  9.42, d=4.0, tw=0.174, A=2.58, Ix=5.36,  Sx=2.68,  Zx=3.16,  J=8.63),
    _hss_sq("HSS4x4x1/4",  12.21, d=4.0, tw=0.233, A=3.37, Ix=6.73,  Sx=3.37,  Zx=4.01,  J=11.0),
    _hss_sq("HSS6x6x1/4",  19.02, d=6.0, tw=0.233, A=5.24, Ix=28.6,  Sx=9.53,  Zx=10.9,  J=44.1),
    _hss_sq("HSS6x6x3/8",  27.48, d=6.0, tw=0.349, A=7.58, Ix=39.4,  Sx=13.1,  Zx=15.5,  J=62.1),
    _hss_sq("HSS8x8x1/4",  25.82, d=8.0, tw=0.233, A=7.10, Ix=70.7,  Sx=17.7,  Zx=20.1,  J=108.0),
    _hss_sq("HSS8x8x3/8",  37.69, d=8.0, tw=0.349, A=10.4, Ix=100.0, Sx=24.9,  Zx=29.0,  J=154.0),
    _hss_sq("HSS8x8x1/2",  48.85, d=8.0, tw=0.465, A=13.5, Ix=124.0, Sx=30.9,  Zx=36.6,  J=194.0),
]
# fmt: on


# ---------------------------------------------------------------------------
# JSON loader
# ---------------------------------------------------------------------------

def _map_json_family(raw_family: str) -> str:
    """Normalise family names from the JSON file to internal names."""
    f = raw_family.upper()
    if f == "W":
        return "W"
    if f in ("PIPE", "ROUND_HSS"):
        return "pipe"
    if f in ("HSS_SQUARE", "SQUARE_HSS", "HSS"):
        return "HSS_square"
    return raw_family.lower()


def load_from_json(path: str | Path) -> List[Section]:
    """
    Load sections from a JSON file with structure:
        {"families": {"W": [{...}, ...], "pipe": [{...}, ...], ...}}

    Each entry is expected to carry keys matching Section fields
    (e.g. "W_plf" or "weight_plf", "A_in2", "Ix_in4", …).
    Missing keys default to 0.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    sections: List[Section] = []
    families_data = data.get("families", {})

    for raw_family, entries in families_data.items():
        family = _map_json_family(raw_family)
        # Pick default Fy/Fu by family
        if family == "pipe":
            default_fy, default_fu = 35.0, 60.0
        elif family == "W":
            default_fy, default_fu = 50.0, 65.0
        else:
            default_fy, default_fu = 46.0, 62.0

        for e in entries:
            desig = str(e.get("designation", e.get("label", "?")))
            weight = float(e.get("W_plf", e.get("weight_plf", e.get("W", 0.0))))
            sec = Section(
                family=family,
                designation=desig,
                weight_plf=weight,
                A_in2=float(e.get("A_in2", e.get("A", 0.0))),
                d_in=float(e.get("d_in", e.get("d", 0.0))),
                bf_in=float(e.get("bf_in", e.get("bf", 0.0))),
                tf_in=float(e.get("tf_in", e.get("tf", 0.0))),
                tw_in=float(e.get("tw_in", e.get("tw", 0.0))),
                Ix_in4=float(e.get("Ix_in4", e.get("Ix", 0.0))),
                Iy_in4=float(e.get("Iy_in4", e.get("Iy", 0.0))),
                Sx_in3=float(e.get("Sx_in3", e.get("Sx", 0.0))),
                Sy_in3=float(e.get("Sy_in3", e.get("Sy", 0.0))),
                Zx_in3=float(e.get("Zx_in3", e.get("Zx", 0.0))),
                Zy_in3=float(e.get("Zy_in3", e.get("Zy", 0.0))),
                rx_in=float(e.get("rx_in", e.get("rx", 0.0))),
                ry_in=float(e.get("ry_in", e.get("ry", 0.0))),
                J_in4=float(e.get("J_in4", e.get("J", 0.0))),
                Cw_in6=float(e.get("Cw_in6", e.get("Cw", 0.0))),
                Fy_ksi=float(e.get("Fy_ksi", e.get("Fy", default_fy))),
                Fu_ksi=float(e.get("Fu_ksi", e.get("Fu", default_fu))),
            )
            sections.append(sec)

    logger.info("Loaded %d sections from %s", len(sections), path)
    return sections


# ---------------------------------------------------------------------------
# Public catalog API
# ---------------------------------------------------------------------------

#: Resolved once at first call; reset to None to force reload.
_CATALOG_CACHE: Optional[List[Section]] = None


def load_catalog(families: Optional[Iterable[str]] = None) -> List[Section]:
    """
    Return the full section catalog, filtered to ``families`` if supplied.

    Tries to load from ``data/standards/aisc_shapes.json`` (relative to this
    file's package root), then falls back to the hardcoded catalog.
    """
    global _CATALOG_CACHE

    if _CATALOG_CACHE is None:
        json_path = (
            Path(__file__).parent.parent  # apex_signcalc/ -> signcalc-service/
            / "data" / "standards" / "aisc_shapes.json"
        )
        if json_path.exists():
            try:
                _CATALOG_CACHE = load_from_json(json_path)
                logger.info("Section catalog loaded from JSON (%d sections)", len(_CATALOG_CACHE))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load aisc_shapes.json (%s); using hardcoded catalog.", exc)
                _CATALOG_CACHE = list(_HARDCODED_CATALOG)
        else:
            logger.debug("aisc_shapes.json not found; using hardcoded catalog.")
            _CATALOG_CACHE = list(_HARDCODED_CATALOG)

    catalog = _CATALOG_CACHE
    if families is not None:
        family_set = {f.lower() for f in families}
        catalog = [s for s in catalog if s.family.lower() in family_set]

    return catalog


def get_section(designation: str) -> Optional[Section]:
    """Return the first section whose designation matches (case-insensitive)."""
    desig_lower = designation.strip().lower()
    for sec in load_catalog():
        if sec.designation.lower() == desig_lower:
            return sec
    return None


def filter_sections(
    family: Optional[str] = None,
    min_Ix: Optional[float] = None,
    max_weight: Optional[float] = None,
) -> List[Section]:
    """
    Filter catalog by one or more criteria.

    Parameters
    ----------
    family:     match ``Section.family`` (case-insensitive)
    min_Ix:     minimum moment of inertia Ix (in^4)
    max_weight: maximum weight per linear foot (lb/ft)
    """
    catalog = load_catalog()
    if family is not None:
        fam_lower = family.lower()
        catalog = [s for s in catalog if s.family.lower() == fam_lower]
    if min_Ix is not None:
        catalog = [s for s in catalog if s.Ix_in4 >= min_Ix]
    if max_weight is not None:
        catalog = [s for s in catalog if s.weight_plf <= max_weight]
    return catalog


# ---------------------------------------------------------------------------
# Backward-compatible entry point
# ---------------------------------------------------------------------------

def catalogs_for_order(order: Iterable[str]) -> List[Section]:
    """
    Return sections for the requested families, sorted by ascending weight.

    Legacy callers pass family names like ``"pipe"``, ``"W"``, or ``"tube"``
    (old name for HSS_square).  The name ``"tube"`` is mapped to
    ``"HSS_square"`` automatically.
    """
    order_list = list(order)
    # Map old family names to current names
    family_map = {
        "tube": "HSS_square",
        "hss": "HSS_square",
        "hss_square": "HSS_square",
        "pipe": "pipe",
        "w": "W",
    }
    resolved = [family_map.get(f.lower(), f) for f in order_list]

    catalog = load_catalog()
    result: List[Section] = [s for s in catalog if s.family in resolved]
    return sorted(result, key=lambda s: s.weight_plf)
