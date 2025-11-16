"""Data quality validation for extracted cost records."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
import structlog

from .data_schema import DataQualityReport, ProjectCostRecord

logger = structlog.get_logger(__name__)


class DataValidator:
    """Validate and generate quality reports for cost datasets."""
    
    def __init__(self, df: pd.DataFrame):
        """Initialize validator with DataFrame."""
        self.df = df
        self.warnings: list[str] = []
        self.errors: list[str] = []
    
    def validate(self) -> DataQualityReport:
        """Run all validation checks and generate quality report."""
        logger.info("validation.start", records=len(self.df))
        
        # Check completeness
        missing_fields = self._check_completeness()
        
        # Check for outliers
        outliers = self._detect_outliers()
        
        # Check date ranges
        date_range = self._check_date_range()
        
        # Check cost ranges
        cost_range = self._check_cost_range()
        
        # Calculate completeness percentage
        total_cells = len(self.df) * len(self.df.columns)
        non_null_cells = self.df.count().sum()
        completeness = (non_null_cells / total_cells) * 100 if total_cells > 0 else 0
        
        # Count valid records (those with all required fields)
        required_fields = ["project_id", "height_ft", "sign_area_sqft", "wind_speed_mph", "total_cost"]
        valid_mask = self.df[required_fields].notna().all(axis=1)
        valid_count = valid_mask.sum()
        
        report = DataQualityReport(
            total_records=len(self.df),
            valid_records=int(valid_count),
            invalid_records=len(self.df) - int(valid_count),
            completeness_percent=round(completeness, 2),
            missing_fields=missing_fields,
            outliers=outliers,
            date_range=date_range,
            cost_range=cost_range,
            warnings=self.warnings,
            errors=self.errors,
        )
        
        logger.info("validation.complete",
                   valid=report.valid_records,
                   invalid=report.invalid_records,
                   completeness=report.completeness_percent)
        
        return report
    
    def _check_completeness(self) -> dict[str, int]:
        """Check for missing values in each field."""
        missing = {}
        for col in self.df.columns:
            null_count = self.df[col].isna().sum()
            if null_count > 0:
                missing[col] = int(null_count)
                
                # Warn on critical fields
                if col in ["total_cost", "height_ft", "sign_area_sqft", "wind_speed_mph"]:
                    self.warnings.append(f"Missing {null_count} values in critical field '{col}'")
        
        return missing
    
    def _detect_outliers(self) -> dict[str, list[str]]:
        """Detect outliers using IQR method."""
        outliers = defaultdict(list)
        
        # Numeric columns to check
        numeric_cols = ["height_ft", "sign_area_sqft", "wind_speed_mph", "pole_size", "total_cost"]
        
        for col in numeric_cols:
            if col not in self.df.columns:
                continue
            
            # Skip if too many nulls
            if self.df[col].isna().sum() > len(self.df) * 0.5:
                continue
            
            values = self.df[col].dropna()
            
            if len(values) < 4:
                continue
            
            # IQR method
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            # Find outliers
            outlier_mask = (values < lower_bound) | (values > upper_bound)
            outlier_indices = values[outlier_mask].index
            
            if len(outlier_indices) > 0:
                outlier_projects = self.df.loc[outlier_indices, "project_id"].tolist()
                outliers[col] = outlier_projects
                
                self.warnings.append(
                    f"Found {len(outlier_indices)} outliers in '{col}': {outlier_projects[:3]}"
                )
        
        return dict(outliers)
    
    def _check_date_range(self) -> tuple[Any, Any]:
        """Check date range of projects."""
        if "quote_date" in self.df.columns:
            valid_dates = pd.to_datetime(self.df["quote_date"], errors="coerce").dropna()
            if len(valid_dates) > 0:
                min_date = valid_dates.min()
                max_date = valid_dates.max()
                return (min_date.date() if hasattr(min_date, 'date') else min_date,
                       max_date.date() if hasattr(max_date, 'date') else max_date)
        
        return (None, None)
    
    def _check_cost_range(self) -> tuple[float, float]:
        """Check cost range and detect anomalies."""
        if "total_cost" not in self.df.columns:
            return (0.0, 0.0)
        
        costs = self.df["total_cost"].dropna()
        
        if len(costs) == 0:
            return (0.0, 0.0)
        
        min_cost = float(costs.min())
        max_cost = float(costs.max())
        
        # Sanity checks
        if min_cost < 100:
            self.warnings.append(f"Suspiciously low cost found: ${min_cost:.2f}")
        
        if max_cost > 100000:
            self.warnings.append(f"Very high cost found: ${max_cost:,.2f}")
        
        return (min_cost, max_cost)
    
    def generate_summary_statistics(self) -> pd.DataFrame:
        """Generate summary statistics for numeric columns."""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        summary = self.df[numeric_cols].describe()
        return summary

