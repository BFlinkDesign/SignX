"""PDF parser for extracting cost data from PDF summaries."""
import os
import re
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

import pdfplumber
import pandas as pd


class CostPDFParser:
    """Parse cost summary PDFs and extract structured data."""
    
    def __init__(self, input_dir: str = "./data/raw", output_dir: str = "./data/processed"):
        """Initialize parser with input/output directories."""
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Parse a single PDF and extract cost data.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary with extracted cost data
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract all text
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                # Extract tables
                tables = []
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                # Parse extracted data
                cost_data = self._extract_cost_data(full_text, tables)
                cost_data["source_file"] = pdf_path.name
                cost_data["parsed_at"] = datetime.utcnow().isoformat()
                
                return cost_data
        
        except Exception as e:
            print(f"Error parsing {pdf_path}: {e}")
            return {
                "source_file": pdf_path.name,
                "error": str(e),
                "parsed_at": datetime.utcnow().isoformat()
            }
    
    def _extract_cost_data(self, text: str, tables: List) -> Dict[str, Any]:
        """
        Extract cost data from text and tables.
        
        This is a template method. Customize based on your PDF format.
        """
        cost_data = {
            "total_cost": None,
            "labor_cost": None,
            "material_cost": None,
            "equipment_cost": None,
            "overhead_cost": None,
            "tax": None,
            "shipping": None,
            "drivers": {},
            "raw_text": text[:500]  # Store sample of raw text
        }
        
        # Extract total cost (look for common patterns)
        total_patterns = [
            r"total[:\s]+\$?([\d,]+\.?\d*)",
            r"grand total[:\s]+\$?([\d,]+\.?\d*)",
            r"project cost[:\s]+\$?([\d,]+\.?\d*)",
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cost_data["total_cost"] = self._parse_currency(match.group(1))
                break
        
        # Extract labor cost
        labor_match = re.search(r"labor[:\s]+\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
        if labor_match:
            cost_data["labor_cost"] = self._parse_currency(labor_match.group(1))
        
        # Extract material cost
        material_match = re.search(r"material[s]?[:\s]+\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
        if material_match:
            cost_data["material_cost"] = self._parse_currency(material_match.group(1))
        
        # Extract equipment cost
        equipment_match = re.search(r"equipment[:\s]+\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
        if equipment_match:
            cost_data["equipment_cost"] = self._parse_currency(equipment_match.group(1))
        
        # Extract tax
        tax_match = re.search(r"tax[:\s]+\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
        if tax_match:
            cost_data["tax"] = self._parse_currency(tax_match.group(1))
        
        # Extract common drivers (customize for your domain)
        # Height
        height_match = re.search(r"height[:\s]+([\d.]+)\s*(ft|feet)", text, re.IGNORECASE)
        if height_match:
            cost_data["drivers"]["sign_height_ft"] = float(height_match.group(1))
        
        # Area
        area_match = re.search(r"area[:\s]+([\d.]+)\s*(sq\.?\s*ft|sqft)", text, re.IGNORECASE)
        if area_match:
            cost_data["drivers"]["sign_area_sqft"] = float(area_match.group(1))
        
        # Wind speed
        wind_match = re.search(r"wind[:\s]+([\d]+)\s*mph", text, re.IGNORECASE)
        if wind_match:
            cost_data["drivers"]["wind_speed_mph"] = int(wind_match.group(1))
        
        # Foundation type
        if "drilled pier" in text.lower():
            cost_data["drivers"]["foundation_type"] = "drilled_pier"
        elif "spread footing" in text.lower():
            cost_data["drivers"]["foundation_type"] = "spread_footing"
        elif "mono column" in text.lower():
            cost_data["drivers"]["foundation_type"] = "mono_column"
        
        # Parse tables for additional data
        if tables:
            cost_data["tables"] = self._parse_tables(tables)
        
        return cost_data
    
    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float."""
        cleaned = value.replace(",", "").replace("$", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _parse_tables(self, tables: List) -> List[Dict]:
        """Parse extracted tables into structured format."""
        parsed_tables = []
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Assume first row is headers
            headers = table[0]
            rows = table[1:]
            
            # Convert to list of dicts
            table_data = []
            for row in rows:
                if len(row) == len(headers):
                    row_dict = dict(zip(headers, row))
                    table_data.append(row_dict)
            
            if table_data:
                parsed_tables.append(table_data)
        
        return parsed_tables
    
    def process_directory(self) -> pd.DataFrame:
        """
        Process all PDFs in input directory.
        
        Returns:
            DataFrame of extracted cost records
        """
        pdf_files = list(self.input_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {self.input_dir}")
            return pd.DataFrame()
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        results = []
        for pdf_file in pdf_files:
            print(f"Processing {pdf_file.name}...")
            cost_data = self.parse_pdf(pdf_file)
            results.append(cost_data)
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Save to CSV for review
        output_csv = self.output_dir / f"extracted_costs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_csv, index=False)
        print(f"Saved extracted data to {output_csv}")
        
        # Also save as Parquet for efficient storage
        output_parquet = self.output_dir / f"extracted_costs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        df.to_parquet(output_parquet, index=False)
        print(f"Saved extracted data to {output_parquet}")
        
        return df


def main():
    """CLI entry point for PDF parsing."""
    parser = CostPDFParser()
    df = parser.process_directory()
    print(f"\n✅ Processed {len(df)} PDFs")
    print(f"\nSample of extracted data:")
    print(df.head())


if __name__ == "__main__":
    main()

