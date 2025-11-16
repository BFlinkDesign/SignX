#!/usr/bin/env python3
"""
KeyedIn Data Extractor - Enhanced Version
Extracts actual data from discovered reports
"""

import requests
import json
import logging
import time
import re
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)

class KeyedInDataExtractor:
    """Extract data from KeyedIn Informer reports"""
    
    def __init__(self, session_file: str):
        """Initialize with session credentials"""
        with open(session_file, 'r') as f:
            self.session = json.load(f)
        
        self.base_url = self.session['base_url']
        self.auth_token = self.session['authToken']
        self.client_id = self.session['clientId']
        self.cookies = self.session['cookies']
        
        self.headers = {
            'Content-Type': 'text/x-gwt-rpc; charset=utf-8',
            'X-GWT-Permutation': 'B2F77E3E03FB2CC3CC1DC61B1DA6CD6F',
            'X-GWT-Module-Base': f'{self.base_url}gwt/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{self.base_url}',
        }
        
        # API endpoints
        self.view_service_url = f'{self.base_url}gwt/viewService'
        
        logging.info(f"Loaded session for user: {self.cookies.get('user', 'Unknown')}")
    
    def _make_gwt_request(self, service_url: str, payload: str) -> Tuple[int, str]:
        """Make a GWT RPC request"""
        response = requests.post(
            service_url,
            data=payload,
            headers=self.headers,
            cookies=self.cookies,
            verify=True
        )
        return response.status_code, response.text
    
    def get_report_list(self) -> List[Dict]:
        """Get list of all available reports"""
        payload = (
            '7|0|9|'
            f'{self.base_url}gwt/|'
            'CB33CA3A1E1166A04FCA7E70FCC91B93|'
            'com.entrinsik.gwt.data.client.ViewService|'
            'getAvailableViews|'
            'com.entrinsik.gwt.data.shared.Category/1632067396|'
            'java.lang.String/2004016611|'
            f'{self.client_id}|'
            f'{self.auth_token}|'
            'PUBLIC|'
            '1|2|3|4|3|5|6|7|8|6|9|'
        )
        
        status, response = self._make_gwt_request(self.view_service_url, payload)
        
        if status != 200:
            logging.error(f"Failed to get report list: {status}")
            return []
        
        # Parse response to extract report info
        reports = self._parse_report_list(response)
        logging.info(f"✓ Found {len(reports)} reports")
        return reports
    
    def _parse_report_list(self, response: str) -> List[Dict]:
        """Parse GWT RPC response to extract report information"""
        reports = []
        
        # Look for ViewToken patterns (UUID format)
        view_tokens = re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', response)
        
        # Split response into chunks
        parts = response.split('|')
        
        current_report = {}
        for i, part in enumerate(parts):
            # Look for potential report names (typically longer strings)
            if len(part) > 20 and part not in view_tokens:
                if 'Report' in part or 'Listing' in part or 'Detail' in part:
                    current_report['name'] = part
            
            # Associate with ViewTokens
            if part in view_tokens and current_report:
                current_report['view_token'] = part
                reports.append(current_report.copy())
                current_report = {}
        
        # Deduplicate by view_token
        seen = set()
        unique_reports = []
        for report in reports:
            if 'view_token' in report and report['view_token'] not in seen:
                seen.add(report['view_token'])
                unique_reports.append(report)
        
        return unique_reports
    
    def get_report_data(self, view_token: str, start_row: int = 0, num_rows: int = 1000) -> Optional[List[Dict]]:
        """Extract data from a specific report"""
        logging.info(f"Extracting data for view token: {view_token}")
        
        # Build getData request
        payload = (
            '7|0|12|'
            f'{self.base_url}gwt/|'
            'CB33CA3A1E1166A04FCA7E70FCC91B93|'
            'com.entrinsik.gwt.data.client.ViewService|'
            'getData|'
            'com.entrinsik.gwt.data.shared.ViewToken/3242268112|'
            'java.lang.String/2004016611|'
            f'{self.client_id}|'
            f'{self.auth_token}|'
            f'{view_token}|'
            'J|'
            f'{start_row}|'
            f'{num_rows}|'
            '1|2|3|4|3|5|6|7|8|6|9|10|11|12|'
        )
        
        status, response = self._make_gwt_request(self.view_service_url, payload)
        
        if status != 200:
            logging.error(f"Failed to get data: {status}")
            return None
        
        # Parse the data response
        data = self._parse_data_response(response)
        return data
    
    def _parse_data_response(self, response: str) -> List[Dict]:
        """Parse GWT RPC data response into structured records"""
        # This is the complex part - GWT RPC serialization format
        # Response format: //EX[version,flags,payload]
        
        if response.startswith('//EX'):
            # Error response
            logging.error(f"Error in response: {response[:200]}")
            return []
        
        if response.startswith('//OK'):
            # Success response
            logging.info("✓ Received data response")
            
            # Extract the payload after //OK
            payload = response[4:]
            
            # Parse the serialized data
            # Format typically: [numFields, field1, field2, ..., numRows, row1field1, row1field2, ...]
            parts = payload.split('|')
            
            # Look for data structure markers
            # This is highly dependent on the actual response format
            # May need adjustment based on actual responses
            
            records = []
            
            # Try to identify column headers and data rows
            # GWT responses often have a structure like:
            # [...headers...][...data rows...]
            
            # For now, return raw parsed data for inspection
            logging.info(f"Response has {len(parts)} parts")
            
            # You'll need to examine actual responses to build proper parser
            return [{'raw_data': payload[:500]}]  # Return snippet for inspection
        
        return []
    
    def extract_report(self, report: Dict, output_dir: Path) -> bool:
        """Extract a single report to CSV"""
        view_token = report.get('view_token')
        report_name = report.get('name', view_token)
        
        if not view_token:
            logging.warning(f"No view token for report: {report_name}")
            return False
        
        logging.info(f"\n{'='*80}")
        logging.info(f"Extracting: {report_name}")
        logging.info(f"View Token: {view_token}")
        
        # Get data
        data = self.get_report_data(view_token)
        
        if not data:
            logging.warning(f"No data returned for {report_name}")
            return False
        
        # Save to CSV
        safe_name = re.sub(r'[^\w\-_]', '_', report_name)
        csv_file = output_dir / f"{safe_name}.csv"
        
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            
            logging.info(f"✓ Saved {len(data)} rows to: {csv_file.name}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save CSV: {e}")
            return False
    
    def extract_all_reports(self, output_dir: Path, limit: Optional[int] = None):
        """Extract all discovered reports"""
        reports = self.get_report_list()
        
        if not reports:
            logging.error("No reports found!")
            return
        
        logging.info(f"\n{'='*80}")
        logging.info(f"Found {len(reports)} reports to extract")
        
        if limit:
            reports = reports[:limit]
            logging.info(f"Limiting to first {limit} reports")
        
        success_count = 0
        fail_count = 0
        
        for i, report in enumerate(reports, 1):
            logging.info(f"\n[{i}/{len(reports)}]")
            
            if self.extract_report(report, output_dir):
                success_count += 1
            else:
                fail_count += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        logging.info(f"\n{'='*80}")
        logging.info(f"EXTRACTION COMPLETE")
        logging.info(f"{'='*80}")
        logging.info(f"✓ Success: {success_count}")
        logging.info(f"✗ Failed: {fail_count}")
        logging.info(f"Output directory: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='Extract data from KeyedIn Informer')
    parser.add_argument('--session-file', required=True, help='Path to session JSON file')
    parser.add_argument('--output-dir', help='Output directory (default: keyedin_data_TIMESTAMP)')
    parser.add_argument('--limit', type=int, help='Limit number of reports to extract (for testing)')
    parser.add_argument('--report', help='Extract specific report by view token')
    
    args = parser.parse_args()
    
    # Create output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'keyedin_data_{timestamp}')
    
    output_dir.mkdir(exist_ok=True)
    
    # Initialize extractor
    extractor = KeyedInDataExtractor(args.session_file)
    
    logging.info("="*80)
    logging.info("KEYEDIN DATA EXTRACTION")
    logging.info("="*80)
    logging.info(f"Output: {output_dir}")
    logging.info("")
    
    # Extract data
    if args.report:
        # Extract single report
        report = {'view_token': args.report, 'name': args.report}
        extractor.extract_report(report, output_dir)
    else:
        # Extract all reports
        extractor.extract_all_reports(output_dir, limit=args.limit)

if __name__ == '__main__':
    main()
