"""
KeyedIn SQL Server Direct Extraction
=====================================
FASTEST method - extracts all data directly from SQL Server database.

Prerequisites:
    1. Get SQL Server instance name from IT
    2. Ensure you have read access to KeyedIn database
    3. Install: pip install pyodbc pandas

Usage:
    python keyedin_sql_extraction.py --server "SERVER\INSTANCE" --database "KeyedIn"
"""

import pyodbc
import pandas as pd
import sqlite3
import json
from pathlib import Path
from datetime import datetime
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'sql_extraction_{datetime.now():%Y%m%d_%H%M%S}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)


class SQLServerExtractor:
    """Extract complete KeyedIn database from SQL Server"""
    
    def __init__(self, server: str, database: str, output_dir: str = "keyedin_backup_sql"):
        self.server = server
        self.database = database
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "csv").mkdir(exist_ok=True)
        (self.output_dir / "json").mkdir(exist_ok=True)
        
        # SQLite database for consolidated storage
        self.db_path = self.output_dir / "keyedin_complete.db"
        self.sqlite_conn = sqlite3.connect(str(self.db_path))
        
        self.conn = None
        
    def connect(self):
        """Connect to SQL Server using Windows Authentication"""
        logging.info(f"Connecting to SQL Server: {self.server}")
        logging.info(f"Database: {self.database}")
        
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={self.server};"
            f"Database={self.database};"
            f"Trusted_Connection=yes;"
        )
        
        try:
            self.conn = pyodbc.connect(connection_string, timeout=10)
            logging.info("✓ Connected to SQL Server")
            return True
        except Exception as e:
            logging.error(f"✗ Connection failed: {e}")
            logging.info("\nTroubleshooting:")
            logging.info("  1. Verify server name with IT department")
            logging.info("  2. Check network connectivity: ping SERVER-NAME")
            logging.info("  3. Ensure you have read permissions on the database")
            logging.info("  4. Try alternative driver: ODBC Driver 18 for SQL Server")
            return False
    
    def discover_all_tables(self):
        """Get list of all tables in database"""
        logging.info("\n" + "=" * 80)
        logging.info("DISCOVERING ALL TABLES")
        logging.info("=" * 80)
        
        query = """
        SELECT 
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        
        df = pd.read_sql(query, self.conn)
        logging.info(f"✓ Found {len(df)} tables")
        
        # Save table list
        table_list_path = self.output_dir / "table_catalog.csv"
        df.to_csv(table_list_path, index=False)
        logging.info(f"✓ Saved table catalog to {table_list_path}")
        
        return df
    
    def get_table_row_count(self, schema: str, table: str) -> int:
        """Get approximate row count for a table"""
        try:
            query = f"SELECT COUNT(*) as cnt FROM [{schema}].[{table}]"
            result = pd.read_sql(query, self.conn)
            return result['cnt'].iloc[0]
        except Exception as e:
            logging.warning(f"Could not count rows in {schema}.{table}: {e}")
            return 0
    
    def extract_table(self, schema: str, table: str):
        """Extract all data from a single table"""
        full_table_name = f"{schema}.{table}"
        safe_name = f"{schema}_{table}".lower()
        
        logging.info(f"\nExtracting: {full_table_name}")
        
        try:
            # Get row count first
            row_count = self.get_table_row_count(schema, table)
            logging.info(f"  Rows: {row_count:,}")
            
            if row_count == 0:
                logging.info("  ! Empty table, skipping")
                return
            
            # Extract data
            query = f"SELECT * FROM [{schema}].[{table}]"
            df = pd.read_sql(query, self.conn)
            
            # Save as CSV
            csv_path = self.output_dir / "csv" / f"{safe_name}.csv"
            df.to_csv(csv_path, index=False)
            logging.info(f"  ✓ Saved CSV: {csv_path}")
            
            # Save as JSON (only for smaller tables)
            if len(df) < 10000:
                json_path = self.output_dir / "json" / f"{safe_name}.json"
                df.to_json(json_path, orient='records', indent=2)
                logging.info(f"  ✓ Saved JSON: {json_path}")
            
            # Save to SQLite
            df.to_sql(safe_name, self.sqlite_conn, if_exists='replace', index=False)
            logging.info(f"  ✓ Saved to SQLite: {safe_name}")
            
            return len(df)
            
        except Exception as e:
            logging.error(f"  ✗ Failed to extract {full_table_name}: {e}")
            return 0
    
    def extract_all(self):
        """Extract all tables from database"""
        logging.info("=" * 80)
        logging.info("KEYEDIN SQL SERVER COMPLETE EXTRACTION")
        logging.info("=" * 80)
        logging.info(f"Started: {datetime.now()}")
        logging.info("")
        
        # Connect
        if not self.connect():
            return
        
        # Discover tables
        tables = self.discover_all_tables()
        
        logging.info("\n" + "=" * 80)
        logging.info("EXTRACTING ALL TABLES")
        logging.info("=" * 80)
        
        total_records = 0
        completed_tables = 0
        failed_tables = []
        
        # Extract each table
        for idx, row in tables.iterrows():
            schema = row['TABLE_SCHEMA']
            table = row['TABLE_NAME']
            
            logging.info(f"\n[{idx + 1}/{len(tables)}] {schema}.{table}")
            
            try:
                records = self.extract_table(schema, table)
                if records:
                    total_records += records
                    completed_tables += 1
            except Exception as e:
                logging.error(f"Failed: {e}")
                failed_tables.append(f"{schema}.{table}")
        
        # Generate summary
        self._generate_summary(len(tables), completed_tables, total_records, failed_tables)
        
        logging.info("\n" + "=" * 80)
        logging.info("EXTRACTION COMPLETE")
        logging.info("=" * 80)
    
    def _generate_summary(self, total_tables, completed, total_records, failed):
        """Generate extraction summary"""
        summary = {
            'extraction_date': datetime.now().isoformat(),
            'source_server': self.server,
            'source_database': self.database,
            'total_tables': total_tables,
            'completed_tables': completed,
            'failed_tables': len(failed),
            'total_records': total_records,
            'output_directory': str(self.output_dir.absolute()),
            'database_file': str(self.db_path.absolute()),
            'database_size_mb': self.db_path.stat().st_size / (1024 * 1024)
        }
        
        summary_path = self.output_dir / "SQL_EXTRACTION_SUMMARY.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\n" + "=" * 80)
        print("SQL EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Total Tables: {total_tables}")
        print(f"Successfully Extracted: {completed}")
        print(f"Failed: {len(failed)}")
        print(f"Total Records: {total_records:,}")
        print(f"Database Size: {summary['database_size_mb']:.2f} MB")
        print(f"\nOutput Location: {self.output_dir.absolute()}")
        print("=" * 80)
        
        if failed:
            print("\nFailed Tables:")
            for table in failed:
                print(f"  - {table}")
    
    def close(self):
        """Clean up connections"""
        if self.conn:
            self.conn.close()
        self.sqlite_conn.close()


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract KeyedIn data from SQL Server')
    parser.add_argument('--server', required=True,
                       help='SQL Server instance (e.g., SERVER\\INSTANCE)')
    parser.add_argument('--database', default='KeyedIn',
                       help='Database name (default: KeyedIn)')
    parser.add_argument('--output-dir', default='keyedin_backup_sql',
                       help='Output directory')
    
    args = parser.parse_args()
    
    extractor = SQLServerExtractor(
        server=args.server,
        database=args.database,
        output_dir=args.output_dir
    )
    
    try:
        extractor.extract_all()
    finally:
        extractor.close()
    
    print("\n✓ SQL extraction complete!")
    print(f"  Location: {Path(args.output_dir).absolute()}")


if __name__ == "__main__":
    main()
