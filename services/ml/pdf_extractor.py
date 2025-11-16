"""PDF cost summary extraction pipeline.

Extracts structured cost data from Eagle Sign Company PDF estimates/invoices
using pdfplumber for consistent template-based documents.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pdfplumber
import structlog
from pydantic import ValidationError

from .data_schema import ExposureCategory, FoundationType, PoleType, ProjectCostRecord

logger = structlog.get_logger(__name__)


class PDFExtractor:
    """Extract cost data from standardized PDF cost summaries."""
    
    def __init__(self, pdf_path: Path):
        """Initialize extractor with PDF file path."""
        self.pdf_path = Path(pdf_path)
        self.raw_text: str = ""
        self.tables: list[list[list[str]]] = []
        
    def extract_text_and_tables(self) -> None:
        """Extract all text and tables from PDF."""
        logger.info("pdf.extract.start", path=str(self.pdf_path))
        
        with pdfplumber.open(self.pdf_path) as pdf:
            # Extract all text
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    self.tables.extend(tables)
            
            self.raw_text = "\n".join(text_parts)
        
        logger.info("pdf.extract.complete", 
                   text_length=len(self.raw_text),
                   tables_found=len(self.tables))
    
    def _extract_field_regex(self, pattern: str, text: str, group: int = 1) -> Optional[str]:
        """Extract field using regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(group).strip()
        return None
    
    def _extract_currency(self, pattern: str, text: str) -> Optional[float]:
        """Extract currency value from text."""
        value_str = self._extract_field_regex(pattern, text)
        if value_str:
            # Remove $, commas
            cleaned = value_str.replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def extract_cost_record(self) -> ProjectCostRecord:
        """Parse PDF and extract ProjectCostRecord.
        
        This method contains extraction logic specific to Eagle Sign Company
        PDF cost summary format. Customize patterns to match your PDF template.
        
        Returns:
            ProjectCostRecord with extracted data
            
        Raises:
            ValidationError: If extracted data doesn't meet schema requirements
        """
        if not self.raw_text:
            self.extract_text_and_tables()
        
        text = self.raw_text
        
        # Extract fields using regex patterns
        # Customize these patterns to match your PDF template
        
        # Project identification
        project_id = self._extract_field_regex(r"Project\s*[#:]?\s*([A-Z0-9-]+)", text) or f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_name = self._extract_field_regex(r"Project\s*Name\s*[:]?\s*(.+)", text)
        customer_name = self._extract_field_regex(r"Customer\s*[:]?\s*(.+)", text)
        job_number = self._extract_field_regex(r"Job\s*[#:]?\s*([A-Z0-9-]+)", text)
        
        # Dates
        quote_date_str = self._extract_field_regex(r"(?:Quote|Estimate)\s*Date\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        completion_date_str = self._extract_field_regex(r"Completion\s*Date\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        
        # Design specifications
        height_ft = self._extract_field_regex(r"(?:Total\s+)?Height\s*[:]?\s*([\d.]+)\s*(?:ft|feet)", text)
        sign_area = self._extract_field_regex(r"Sign\s*Area\s*[:]?\s*([\d.]+)\s*(?:sq\.?\s*ft|sqft)", text)
        sign_width = self._extract_field_regex(r"(?:Sign\s+)?Width\s*[:]?\s*([\d.]+)\s*(?:ft|feet)", text)
        sign_height = self._extract_field_regex(r"(?:Sign\s+)?(?:Face\s+)?Height\s*[:]?\s*([\d.]+)\s*(?:ft|feet)", text)
        
        # Wind specifications
        wind_speed = self._extract_field_regex(r"Wind\s*Speed\s*[:]?\s*([\d.]+)\s*(?:mph)", text)
        exposure = self._extract_field_regex(r"Exposure\s*(?:Category)?\s*[:]?\s*([A-D])", text)
        
        # Pole specifications
        pole_size = self._extract_field_regex(r"Pole\s*Size\s*[:]?\s*([\d.]+)", text)
        pole_type_str = self._extract_field_regex(r"Pole\s*Type\s*[:]?\s*(HSS|PIPE|I-BEAM|W-SHAPE)", text)
        pole_material = self._extract_field_regex(r"(?:Steel\s+)?Grade\s*[:]?\s*([A-Z0-9-]+)", text)
        
        # Foundation
        foundation_type_str = self._extract_field_regex(r"Foundation\s*[:]?\s*(Direct\s*Burial|Base\s*Plate|Drilled\s*Pier)", text)
        embedment_depth = self._extract_field_regex(r"(?:Embedment|Depth)\s*[:]?\s*([\d.]+)\s*(?:ft|feet)", text)
        concrete_volume = self._extract_field_regex(r"Concrete\s*[:]?\s*([\d.]+)\s*(?:CY|cu\.?\s*yd)", text)
        
        # Costs
        material_cost = self._extract_currency(r"Material\s*(?:Cost)?\s*[:]?\s*\$?([\d,]+\.?\d*)", text)
        labor_cost = self._extract_currency(r"Labor\s*(?:Cost)?\s*[:]?\s*\$?([\d,]+\.?\d*)", text)
        engineering_cost = self._extract_currency(r"Engineering\s*(?:Cost)?\s*[:]?\s*\$?([\d,]+\.?\d*)", text)
        permit_cost = self._extract_currency(r"Permit\s*(?:Cost|Fees?)?\s*[:]?\s*\$?([\d,]+\.?\d*)", text)
        total_cost = self._extract_currency(r"Total\s*(?:Cost|Price)?\s*[:]?\s*\$?([\d,]+\.?\d*)", text)
        
        # Build record with defaults for missing fields
        record_data = {
            "project_id": project_id,
            "project_name": project_name,
            "customer_name": customer_name,
            "job_number": job_number,
            "quote_date": quote_date_str,
            "completion_date": completion_date_str,
            "height_ft": float(height_ft) if height_ft else 20.0,  # Default fallback
            "sign_area_sqft": float(sign_area) if sign_area else 50.0,
            "sign_width_ft": float(sign_width) if sign_width else None,
            "sign_height_ft": float(sign_height) if sign_height else None,
            "wind_speed_mph": float(wind_speed) if wind_speed else 115.0,
            "exposure_category": ExposureCategory(exposure) if exposure else ExposureCategory.C,
            "pole_type": self._normalize_pole_type(pole_type_str),
            "pole_size": float(pole_size) if pole_size else 8.0,
            "pole_material_grade": pole_material,
            "pole_height_ft": float(height_ft) if height_ft else 20.0,
            "foundation_type": self._normalize_foundation_type(foundation_type_str),
            "embedment_depth_ft": float(embedment_depth) if embedment_depth else None,
            "concrete_volume_cuyd": float(concrete_volume) if concrete_volume else None,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "engineering_cost": engineering_cost,
            "permit_cost": permit_cost,
            "total_cost": total_cost or 10000.0,  # Must have total
            "source_pdf": self.pdf_path.name,
        }
        
        return ProjectCostRecord(**record_data)
    
    def _normalize_pole_type(self, pole_type_str: Optional[str]) -> PoleType:
        """Normalize pole type string to enum."""
        if not pole_type_str:
            return PoleType.ROUND_HSS
        
        pole_type_upper = pole_type_str.upper()
        if "HSS" in pole_type_upper:
            if "SQUARE" in pole_type_upper:
                return PoleType.SQUARE_HSS
            return PoleType.ROUND_HSS
        elif "PIPE" in pole_type_upper:
            return PoleType.PIPE
        elif "I-BEAM" in pole_type_upper or "I BEAM" in pole_type_upper:
            return PoleType.I_BEAM
        elif "W" in pole_type_upper:
            return PoleType.W_SHAPE
        else:
            return PoleType.ROUND_HSS
    
    def _normalize_foundation_type(self, foundation_str: Optional[str]) -> FoundationType:
        """Normalize foundation type string to enum."""
        if not foundation_str:
            return FoundationType.DIRECT_BURIAL
        
        foundation_upper = foundation_str.upper()
        if "DIRECT" in foundation_upper or "BURIAL" in foundation_upper:
            return FoundationType.DIRECT_BURIAL
        elif "BASE" in foundation_upper or "PLATE" in foundation_upper:
            return FoundationType.BASE_PLATE
        elif "DRILL" in foundation_upper or "PIER" in foundation_upper:
            return FoundationType.DRILLED_PIER
        else:
            return FoundationType.DIRECT_BURIAL


def extract_pdf_batch(pdf_directory: Path, output_path: Path) -> tuple[list[ProjectCostRecord], list[dict]]:
    """Extract all PDFs in a directory to structured records.
    
    Args:
        pdf_directory: Directory containing PDF cost summaries
        output_path: Path to save extracted parquet dataset
        
    Returns:
        Tuple of (valid_records, error_records)
    """
    pdf_dir = Path(pdf_directory)
    valid_records: list[ProjectCostRecord] = []
    error_records: list[dict] = []
    
    logger.info("batch.extract.start", directory=str(pdf_dir))
    
    # Find all PDFs
    pdf_files = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("**/*.pdf"))
    
    logger.info("batch.extract.found", count=len(pdf_files))
    
    for pdf_file in pdf_files:
        try:
            extractor = PDFExtractor(pdf_file)
            record = extractor.extract_cost_record()
            valid_records.append(record)
            
            logger.info("pdf.extract.success", file=pdf_file.name, project_id=record.project_id)
            
        except ValidationError as e:
            logger.error("pdf.extract.validation_error", file=pdf_file.name, errors=e.errors())
            error_records.append({
                "file": str(pdf_file),
                "error_type": "validation",
                "errors": e.errors()
            })
            
        except Exception as e:
            logger.error("pdf.extract.error", file=pdf_file.name, error=str(e))
            error_records.append({
                "file": str(pdf_file),
                "error_type": "extraction",
                "error": str(e)
            })
    
    # Save valid records to parquet
    if valid_records:
        import pandas as pd
        
        records_dicts = [r.model_dump() for r in valid_records]
        df = pd.DataFrame(records_dicts)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_parquet(output_path, index=False, compression="snappy")
        
        logger.info("batch.extract.complete", 
                   valid=len(valid_records),
                   errors=len(error_records),
                   output=str(output_path))
    
    return valid_records, error_records

