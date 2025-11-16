"""Parquet writer for data lake storage."""
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class ParquetWriter:
    """Write cost data to Parquet files for efficient storage and querying."""
    
    def __init__(self, base_path: str = "./data/processed"):
        """Initialize writer with base path."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def write_cost_records(
        self,
        records: List[Dict[str, Any]],
        partition_by: str = "year_month"
    ) -> str:
        """
        Write cost records to partitioned Parquet files.
        
        Args:
            records: List of cost record dictionaries
            partition_by: Partition strategy ('year_month', 'year', 'none')
        
        Returns:
            Path to written file(s)
        """
        if not records:
            raise ValueError("No records to write")
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Ensure datetime columns
        if 'cost_date' in df.columns:
            df['cost_date'] = pd.to_datetime(df['cost_date'])
        
        # Add partition columns
        if partition_by == "year_month" and 'cost_date' in df.columns:
            df['year'] = df['cost_date'].dt.year
            df['month'] = df['cost_date'].dt.month
            partition_cols = ['year', 'month']
        elif partition_by == "year" and 'cost_date' in df.columns:
            df['year'] = df['cost_date'].dt.year
            partition_cols = ['year']
        else:
            partition_cols = None
        
        # Generate output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if partition_cols:
            # Write partitioned
            output_dir = self.base_path / "cost_records_partitioned"
            pq.write_to_dataset(
                pa.Table.from_pandas(df),
                root_path=str(output_dir),
                partition_cols=partition_cols,
                existing_data_behavior='overwrite_or_ignore'
            )
            return str(output_dir)
        else:
            # Write single file
            output_file = self.base_path / f"cost_records_{timestamp}.parquet"
            df.to_parquet(output_file, compression='snappy', index=False)
            return str(output_file)
    
    def read_cost_records(
        self,
        filters: List[tuple] | None = None,
        columns: List[str] | None = None
    ) -> pd.DataFrame:
        """
        Read cost records from Parquet files with optional filters.
        
        Args:
            filters: PyArrow filters (e.g., [('year', '=', 2024)])
            columns: Columns to read (None = all)
        
        Returns:
            DataFrame of cost records
        """
        partitioned_path = self.base_path / "cost_records_partitioned"
        
        if partitioned_path.exists():
            # Read partitioned dataset
            dataset = pq.ParquetDataset(partitioned_path, filters=filters)
            return dataset.read(columns=columns).to_pandas()
        else:
            # Read all single files
            parquet_files = list(self.base_path.glob("cost_records_*.parquet"))
            if not parquet_files:
                return pd.DataFrame()
            
            dfs = []
            for file in parquet_files:
                df = pd.read_parquet(file, columns=columns)
                if filters:
                    # Apply basic filters manually for non-partitioned data
                    for col, op, val in filters:
                        if op == '=':
                            df = df[df[col] == val]
                        elif op == '>':
                            df = df[df[col] > val]
                        elif op == '<':
                            df = df[df[col] < val]
                dfs.append(df)
            
            return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    def append_records(self, records: List[Dict[str, Any]]) -> str:
        """Append new records to existing dataset."""
        return self.write_cost_records(records, partition_by="year_month")

