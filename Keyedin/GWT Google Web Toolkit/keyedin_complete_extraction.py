"""
KeyedIn Complete Data Extraction System
=========================================
Extracts ALL data from KeyedIn Informer before migration.

This script:
1. Discovers all available reports/views in Informer
2. Extracts complete data from each source
3. Saves in multiple formats (CSV, JSON, SQLite)
4. Tracks progress and handles errors
5. Creates complete backup of all historical data

Usage:
    python keyedin_complete_extraction.py --session-file cookies.json
"""

import requests
import json
import csv
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging
from dataclasses import dataclass, asdict
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'extraction_{datetime.now():%Y%m%d_%H%M%S}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

@dataclass
class ExtractionProgress:
    """Track extraction progress"""
    total_reports: int = 0
    completed_reports: int = 0
    total_records: int = 0
    failed_reports: List[str] = None
    start_time: datetime = None
    
    def __post_init__(self):
        if self.failed_reports is None:
            self.failed_reports = []
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def to_dict(self):
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat(),
            'elapsed_minutes': (datetime.now() - self.start_time).total_seconds() / 60
        }


class KeyedInExtractor:
    """Complete KeyedIn data extraction system"""
    
    def __init__(self, base_url: str, session_cookies: Dict[str, str], output_dir: str = "keyedin_backup"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.cookies.update(session_cookies)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "csv").mkdir(exist_ok=True)
        (self.output_dir / "json").mkdir(exist_ok=True)
        (self.output_dir / "metadata").mkdir(exist_ok=True)
        
        # Initialize SQLite database for consolidated storage
        self.db_path = self.output_dir / "keyedin_complete.db"
        self.conn = sqlite3.connect(str(self.db_path))
        
        self.progress = ExtractionProgress()
        
        logging.info(f"KeyedIn Extractor initialized")
        logging.info(f"Output directory: {self.output_dir.absolute()}")
        logging.info(f"Database: {self.db_path.absolute()}")
    
    def discover_all_reports(self) -> List[Dict[str, Any]]:
        """
        Discover all available reports in Informer
        Uses MetadataRPCService to get complete report catalog
        """
        logging.info("=" * 80)
        logging.info("PHASE 1: DISCOVERING ALL REPORTS")
        logging.info("=" * 80)
        
        metadata_url = f"{self.base_url}/informer/rpc/protected/MetadataRPCService"
        
        # Request all report metadata
        # This payload structure is typical for GWT RPC - may need adjustment
        payload = {
            "method": "getAllReports",
            "params": []
        }
        
        try:
            response = self.session.post(metadata_url, json=payload, timeout=30)
            response.raise_for_status()
            
            reports = response.json()
            self.progress.total_reports = len(reports)
            
            logging.info(f"✓ Discovered {len(reports)} reports")
            
            # Save report catalog
            catalog_path = self.output_dir / "metadata" / "report_catalog.json"
            with open(catalog_path, 'w') as f:
                json.dump(reports, f, indent=2)
            
            logging.info(f"✓ Saved report catalog to {catalog_path}")
            
            return reports
            
        except Exception as e:
            logging.error(f"✗ Failed to discover reports: {e}")
            # Fallback: Use known report categories
            return self._get_fallback_report_list()
    
    def _get_fallback_report_list(self) -> List[Dict[str, Any]]:
        """
        Fallback report list based on common KeyedIn modules
        If metadata service fails, we'll try common report paths
        """
        logging.warning("Using fallback report list - manual discovery")
        
        common_reports = [
            {"id": "work_orders", "name": "Work Orders", "path": "/Production/WorkOrders"},
            {"id": "work_order_history", "name": "Work Order History", "path": "/Production/History"},
            {"id": "quotes", "name": "Quotes", "path": "/Sales/Quotes"},
            {"id": "customers", "name": "Customers", "path": "/Sales/Customers"},
            {"id": "projects", "name": "Projects", "path": "/Projects/All"},
            {"id": "inventory", "name": "Inventory", "path": "/Inventory/Current"},
            {"id": "invoices", "name": "Invoices", "path": "/Accounting/Invoices"},
            {"id": "purchase_orders", "name": "Purchase Orders", "path": "/Purchasing/POs"},
            {"id": "employees", "name": "Employees", "path": "/HR/Employees"},
            {"id": "timesheets", "name": "Timesheets", "path": "/HR/Timesheets"},
            {"id": "vendors", "name": "Vendors", "path": "/Purchasing/Vendors"},
            {"id": "parts", "name": "Parts", "path": "/Inventory/Parts"},
            {"id": "service_calls", "name": "Service Calls", "path": "/Service/Calls"},
            {"id": "equipment", "name": "Equipment", "path": "/Assets/Equipment"},
        ]
        
        self.progress.total_reports = len(common_reports)
        return common_reports
    
    def extract_report_data(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all data from a single report
        Returns dict with metadata and data records
        """
        report_id = report.get('id', 'unknown')
        report_name = report.get('name', report_id)
        
        logging.info(f"\n--- Extracting: {report_name} ---")
        
        report_url = f"{self.base_url}/informer/rpc/protected/ReportRPCService"
        
        all_records = []
        page = 0
        page_size = 1000  # Adjust based on KeyedIn limits
        
        while True:
            try:
                # Request report data with pagination
                payload = {
                    "method": "getReportData",
                    "params": {
                        "reportId": report_id,
                        "offset": page * page_size,
                        "limit": page_size
                    }
                }
                
                response = self.session.post(report_url, json=payload, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                records = data.get('records', [])
                
                if not records:
                    break
                
                all_records.extend(records)
                page += 1
                
                logging.info(f"  Page {page}: {len(records)} records (Total: {len(all_records)})")
                
                # Rate limiting - be nice to the server
                time.sleep(0.5)
                
                # Check if we got less than page_size (indicates last page)
                if len(records) < page_size:
                    break
                    
            except Exception as e:
                logging.error(f"  ✗ Error on page {page}: {e}")
                break
        
        result = {
            'report_id': report_id,
            'report_name': report_name,
            'record_count': len(all_records),
            'records': all_records,
            'extracted_at': datetime.now().isoformat()
        }
        
        logging.info(f"✓ Extracted {len(all_records)} total records from {report_name}")
        
        return result
    
    def save_report_data(self, report_data: Dict[str, Any]):
        """Save report data in multiple formats"""
        report_id = report_data['report_id']
        report_name = report_data['report_name']
        records = report_data['records']
        
        if not records:
            logging.warning(f"  ! No records to save for {report_name}")
            return
        
        safe_name = "".join(c for c in report_id if c.isalnum() or c in ('_', '-')).lower()
        
        # 1. Save as JSON
        json_path = self.output_dir / "json" / f"{safe_name}.json"
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        logging.info(f"  ✓ Saved JSON: {json_path}")
        
        # 2. Save as CSV
        if records:
            csv_path = self.output_dir / "csv" / f"{safe_name}.csv"
            keys = records[0].keys()
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(records)
            
            logging.info(f"  ✓ Saved CSV: {csv_path}")
        
        # 3. Save to SQLite
        self._save_to_sqlite(safe_name, records)
        logging.info(f"  ✓ Saved to SQLite: {safe_name} table")
    
    def _save_to_sqlite(self, table_name: str, records: List[Dict[str, Any]]):
        """Save records to SQLite database"""
        if not records:
            return
        
        # Create table dynamically based on first record
        columns = records[0].keys()
        
        # Drop table if exists (fresh extraction)
        self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create table
        col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
        create_sql = f"CREATE TABLE {table_name} ({col_defs})"
        self.conn.execute(create_sql)
        
        # Insert records
        placeholders = ", ".join(["?" for _ in columns])
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        
        for record in records:
            values = [str(record.get(col, '')) for col in columns]
            self.conn.execute(insert_sql, values)
        
        self.conn.commit()
    
    def extract_all(self):
        """
        Main extraction workflow:
        1. Discover all reports
        2. Extract data from each
        3. Save in multiple formats
        4. Generate summary
        """
        logging.info("=" * 80)
        logging.info("KEYEDIN COMPLETE DATA EXTRACTION")
        logging.info("=" * 80)
        logging.info(f"Started: {datetime.now()}")
        logging.info("")
        
        # Discover reports
        reports = self.discover_all_reports()
        
        if not reports:
            logging.error("No reports discovered. Cannot proceed.")
            return
        
        logging.info("\n" + "=" * 80)
        logging.info("PHASE 2: EXTRACTING ALL DATA")
        logging.info("=" * 80)
        
        # Extract each report
        for i, report in enumerate(reports, 1):
            report_name = report.get('name', report.get('id', 'Unknown'))
            
            logging.info(f"\n[{i}/{len(reports)}] Processing: {report_name}")
            
            try:
                report_data = self.extract_report_data(report)
                self.save_report_data(report_data)
                
                self.progress.completed_reports += 1
                self.progress.total_records += report_data['record_count']
                
            except Exception as e:
                logging.error(f"✗ Failed to extract {report_name}: {e}")
                self.progress.failed_reports.append(report_name)
        
        # Generate summary
        self._generate_summary()
        
        logging.info("\n" + "=" * 80)
        logging.info("EXTRACTION COMPLETE")
        logging.info("=" * 80)
    
    def _generate_summary(self):
        """Generate extraction summary report"""
        summary = {
            'extraction_date': datetime.now().isoformat(),
            'progress': self.progress.to_dict(),
            'output_directory': str(self.output_dir.absolute()),
            'database_file': str(self.db_path.absolute()),
            'database_size_mb': self.db_path.stat().st_size / (1024 * 1024)
        }
        
        summary_path = self.output_dir / "EXTRACTION_SUMMARY.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Also print to console
        print("\n" + "=" * 80)
        print("EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Total Reports: {self.progress.total_reports}")
        print(f"Successfully Extracted: {self.progress.completed_reports}")
        print(f"Failed: {len(self.progress.failed_reports)}")
        print(f"Total Records: {self.progress.total_records:,}")
        print(f"Database Size: {summary['database_size_mb']:.2f} MB")
        print(f"Elapsed Time: {summary['progress']['elapsed_minutes']:.1f} minutes")
        print(f"\nOutput Location: {self.output_dir.absolute()}")
        print("=" * 80)
        
        if self.progress.failed_reports:
            print("\nFailed Reports:")
            for report in self.progress.failed_reports:
                print(f"  - {report}")
    
    def close(self):
        """Clean up resources"""
        self.conn.close()
        logging.info("Database connection closed")


def load_session_cookies(cookies_file: str) -> Dict[str, str]:
    """Load session cookies from JSON file"""
    with open(cookies_file, 'r') as f:
        cookies = json.load(f)
    
    # Convert list of cookie dicts to simple name:value dict
    if isinstance(cookies, list):
        return {c['name']: c['value'] for c in cookies}
    return cookies


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract complete KeyedIn data')
    parser.add_argument('--base-url', 
                       default='https://eaglesign.keyedinsign.com:8443/eaglesign',
                       help='KeyedIn base URL')
    parser.add_argument('--session-file', 
                       default='session_cookies.json',
                       help='JSON file with session cookies')
    parser.add_argument('--output-dir',
                       default='keyedin_backup',
                       help='Output directory for extracted data')
    
    args = parser.parse_args()
    
    # Load session cookies
    cookies = load_session_cookies(args.session_file)
    
    # Create extractor
    extractor = KeyedInExtractor(
        base_url=args.base_url,
        session_cookies=cookies,
        output_dir=args.output_dir
    )
    
    try:
        # Run complete extraction
        extractor.extract_all()
    finally:
        extractor.close()
    
    print("\n✓ Extraction complete! Check the output directory for your data.")
    print(f"  Location: {Path(args.output_dir).absolute()}")


if __name__ == "__main__":
    main()
