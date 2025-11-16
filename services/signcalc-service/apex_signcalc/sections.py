from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import logging

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None


@dataclass
class Section:
    family: str
    designation: str
    weight_lbf: float
    Sx_in3: float
    Ix_in4: float
    fy_psi: float


def load_pipe_catalog() -> List[Section]:
    return [
        Section("pipe", "Pipe 3.5x0.216", 10.8, 5.94, 10.4, 36000.0),
        Section("pipe", "Pipe 4.5x0.237", 13.5, 9.13, 20.5, 36000.0),
        Section("pipe", "Pipe 6.625x0.280", 20.2, 23.2, 76.8, 36000.0),
    ]


def load_w_catalog() -> List[Section]:
    sections = [
        Section("W", "W6x15", 15.0, 15.8, 47.6, 50000.0),
        Section("W", "W8x18", 18.0, 21.2, 84.8, 50000.0),
    ]
    # Try loading from AISC Excel
    if pd is not None:
        aisc_path = Path(__file__).parent.parent.parent.parent / "info" / "aisc-shapes-database-v16.0_a1085.xlsx"
        if aisc_path.exists():
            try:
                df = pd.read_excel(aisc_path, sheet_name="W-shapes", usecols=["AISC_Manual_Label", "W", "Sx", "Ix", "Fy"])
                for _, row in df.head(10).iterrows():
                    label = str(row["AISC_Manual_Label"]).strip()
                    w = float(row["W"]) if pd.notna(row["W"]) else 0.0
                    sx = float(row["Sx"]) if pd.notna(row["Sx"]) else 0.0
                    ix = float(row["Ix"]) if pd.notna(row["Ix"]) else 0.0
                    fy = float(row["Fy"]) if pd.notna(row["Fy"]) else 50000.0
                    if w > 0 and sx > 0:
                        sections.append(Section("W", label, w, sx, ix, fy))
            except Exception as e:
                logger.warning("Exception in sections.py: %s", str(e))
                pass  # fallback to hardcoded
    return sections[:50] if len(sections) > 50 else sections


def load_tube_catalog() -> List[Section]:
    sections = [
        Section("tube", "HSS 4x4x3/16", 10.9, 6.25, 12.5, 46000.0),
        Section("tube", "HSS 6x6x1/4", 21.7, 19.1, 57.2, 46000.0),
    ]
    # Try loading from AISC Excel
    if pd is not None:
        aisc_path = Path(__file__).parent.parent.parent.parent / "info" / "aisc-shapes-database-v16.0_a1085.xlsx"
        if aisc_path.exists():
            try:
                for sheet in ["Rectangular HSS", "Square HSS"]:
                    try:
                        df = pd.read_excel(aisc_path, sheet_name=sheet, usecols=["AISC_Manual_Label", "W", "Sx", "Ix", "Fy"])
                        for _, row in df.head(20).iterrows():
                            label = str(row["AISC_Manual_Label"]).strip()
                            w = float(row["W"]) if pd.notna(row["W"]) else 0.0
                            sx = float(row["Sx"]) if pd.notna(row["Sx"]) else 0.0
                            ix = float(row["Ix"]) if pd.notna(row["Ix"]) else 0.0
                            fy = float(row["Fy"]) if pd.notna(row["Fy"]) else 46000.0
                            if w > 0 and sx > 0:
                                sections.append(Section("tube", label, w, sx, ix, fy))
                    except Exception as e:
                        logger.warning("Exception in sections.py: %s", str(e))
                        continue
            except Exception as e:
                logger.warning("Exception in sections.py: %s", str(e))
                pass  # fallback to hardcoded
    return sections[:100] if len(sections) > 100 else sections


def catalogs_for_order(order: Iterable[str]) -> List[Section]:
    order_list = list(order)
    cat: List[Section] = []
    for fam in order_list:
        if fam == "pipe":
            cat.extend(load_pipe_catalog())
        elif fam == "W":
            cat.extend(load_w_catalog())
        elif fam == "tube":
            cat.extend(load_tube_catalog())
    # ascending by weight
    return sorted(cat, key=lambda s: s.weight_lbf)


