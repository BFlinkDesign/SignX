"""
AISC/ASCE catalog import utilities.

Agent 3: Importing AISC steel sections and ASCE wind load references for material catalog.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from ..db import MaterialCatalog, CodeReference

logger = structlog.get_logger(__name__)


async def import_aisc_sections(db: AsyncSession, sections: list[dict]) -> int:
    """Import AISC steel sections into material_catalog.
    
    Args:
        db: Database session
        sections: List of section dicts with keys: material_id, standard, grade, shape, properties, dimensions, source_table
    
    Returns:
        Number of sections imported
    """
    count = 0
    for section in sections:
        try:
            stmt = insert(MaterialCatalog).values(**section).on_conflict_do_nothing()
            await db.execute(stmt)
            count += 1
        except Exception as e:
            logger.warning("catalog.import_failed", material_id=section.get("material_id"), error=str(e))
    await db.flush()
    logger.info("catalog.imported", standard="AISC", count=count)
    return count


async def import_asce_references(db: AsyncSession, refs: list[dict]) -> int:
    """Import ASCE/AISC code references into code_references.
    
    Args:
        db: Database session
        refs: List of reference dicts with keys: ref_id, code, section, title, formula, application
    
    Returns:
        Number of references imported
    """
    count = 0
    for ref in refs:
        try:
            stmt = insert(CodeReference).values(**ref).on_conflict_do_nothing()
            await db.execute(stmt)
            count += 1
        except Exception as e:
            logger.warning("catalog.ref_import_failed", ref_id=ref.get("ref_id"), error=str(e))
    await db.flush()
    logger.info("catalog.refs_imported", count=count)
    return count


async def lookup_material(db: AsyncSession, standard: str, grade: str, shape: str | None = None) -> MaterialCatalog | None:
    """Lookup material from catalog by standard/grade/shape."""
    query = select(MaterialCatalog).where(
        MaterialCatalog.standard == standard,
        MaterialCatalog.grade == grade,
    )
    if shape:
        query = query.where(MaterialCatalog.shape == shape)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def lookup_code_ref(db: AsyncSession, code: str, section: str) -> CodeReference | None:
    """Lookup code reference by code and section."""
    query = select(CodeReference).where(
        CodeReference.code == code,
        CodeReference.section == section,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

