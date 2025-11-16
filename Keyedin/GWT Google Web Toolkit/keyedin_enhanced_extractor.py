#!/usr/bin/env python3
"""
KeyedIn Complete Data Extractor - Enhanced with Data Extraction
Uses proper GWT RPC protocol based on reverse engineering
"""

import json
import requests
import time
import csv
import re
from datetime import datetime
from pathlib import Path
import logging
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class GWTRPCParser:
    """Parser for GWT RPC responses"""

    @staticmethod
    def parse_string_table(response):
        """Extract the string table from GWT RPC response"""
        if not response.startswith('//OK['):
            return []
        strings = re.findall(r'"([^"]*)"', response)
        return strings
    
    @staticmethod
    def parse_data_response(response):
        """Parse GWT RPC data response into structured records"""
        if not response.startswith('//OK'):
            return None, []
        
        # Extract all strings (potential column names and data values)
        strings = GWTRPCParser.parse_string_table(response)
        
        # The response format typically has:
        # - String table at the beginning
        # - Column definitions
        # - Data rows
        
        return strings, response

class KeyedInExtractor:
    def __init__(self, session_file='keyedin_session.json'):
        """Initialize extractor with session data"""

        logging.info("=" * 80)
        logging.info("KEYEDIN DATA EXTRACTOR - ENHANCED")
        logging.info("=" * 80)

        # Load session
        with open(session_file, 'r') as f:
            session_data = json.load(f)

        self.base_url = session_data['base_url']
        self.auth_token = session_data['authToken']
        self.client_id = session_data['clientId']
        self.cookies = session_data['cookies']

        logging.info(f"Loaded session for user: {self.cookies.get('user', 'Unknown')}")

        # Setup session
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)

        # GWT RPC headers
        self.gwt_headers = {
            'Content-Type': 'text/x-gwt-rpc; charset=UTF-8',
            'X-GWT-Module-Base': f'{self.base_url}informer/',
            'X-GWT-Permutation': '6823F3E0DFFF554BC1A7951AA98B182D',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': f'{self.base_url}?locale=en_US'
        }

        # Output setup
        self.output_dir = Path('keyedin_extraction_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.output_dir.mkdir(exist_ok=True)

        logging.info(f"Output directory: {self.output_dir.absolute()}")
        
        # Store discovered report tokens
        self.report_tokens = {}

    def build_url(self, service):
        """Build RPC URL with authentication"""
        return f"{self.base_url}informer/rpc/protected/{service}?authToken={self.auth_token}&clientId={self.client_id}"

    def discover_reports(self):
        """Discover all available reports with their ViewTokens"""
        logging.info("")
        logging.info("=" * 80)
        logging.info("DISCOVERING REPORTS")
        logging.info("=" * 80)

        url = self.build_url('ViewRPCService')

        # Payload for report discovery
        payload = '7|0|22|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|600437df-77ae-4aca-8f93-45b022255489|com.entrinsik.gwt.data.shared.LoadOptions/4020437150|java.util.HashMap/1797211028|com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl/346417575|java.util.ArrayList/4159755760|com.entrinsik.gwt.data.shared.criteria.Operator/2483661797|com.entrinsik.gwt.data.shared.criteria.impl.ValueExpressionImpl/3874770769|name|com.entrinsik.gwt.data.shared.criteria.Quantifier/3325804167|com.entrinsik.gwt.data.shared.values.StringValue/2414534542|**|com.entrinsik.informer.core.domain.report.ReportSearchOptions/1133289605|en_US|com.entrinsik.gwt.data.shared.Order/1651361273|com.entrinsik.gwt.data.shared.values.NullValue/2880996259|1|2|3|4|2|5|6|5|1|7|8|6|1|9|10|0|11|12|2|11|12|1|11|12|0|13|9|13|8|14|1|13|2|15|16|0|17|18|-13|0|19|12|0|0|0|0|0|25|20|12|1|21|1|15|1|0|22|0|0|'

        try:
            response = self.session.post(url, data=payload, headers=self.gwt_headers)

            if response.status_code == 200:
                logging.info(f"✓ Report discovery successful ({len(response.text)} bytes)")

                # Parse response
                strings = GWTRPCParser.parse_string_table(response.text)
                
                # Extract ViewTokens (UUID format)
                view_tokens = [s for s in strings if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', s)]
                
                # Extract report names
                report_names = [s for s in strings if len(s) > 5 and not s.startswith('com.') and not s.startswith('java.')]
                exclude = {'KeyedInSign', 'System Administrator', 'ADMIN', 'en_US', 'true', 'false'}
                report_names = [r for r in report_names if r not in exclude]

                # Try to associate names with tokens
                # Simple heuristic: tokens and names appear in order
                for token in view_tokens:
                    # Find the nearest report name before this token in the strings list
                    token_idx = strings.index(token)
                    for i in range(token_idx - 1, -1, -1):
                        if strings[i] in report_names and strings[i] not in self.report_tokens:
                            self.report_tokens[strings[i]] = token
                            break
                
                # Save any unmatched tokens with generic names
                for i, token in enumerate(view_tokens):
                    if token not in self.report_tokens.values():
                        self.report_tokens[f"Report_{i+1}_{token[:8]}"] = token

                logging.info(f"✓ Found {len(self.report_tokens)} reports with ViewTokens")

                # Save report list
                report_list_file = self.output_dir / 'discovered_reports.txt'
                with open(report_list_file, 'w', encoding='utf-8') as f:
                    for name, token in sorted(self.report_tokens.items()):
                        f.write(f"{name}\n  ViewToken: {token}\n\n")

                logging.info(f"✓ Report list saved to: {report_list_file}")

                return self.report_tokens
            else:
                logging.error(f"✗ Discovery failed: HTTP {response.status_code}")
                return {}

        except Exception as e:
            logging.error(f"✗ Discovery error: {e}")
            return {}

    def extract_report_data(self, report_name, view_token, max_rows=10000):
        """Extract data from a specific report"""
        logging.info(f"\n{'='*80}")
        logging.info(f"Extracting: {report_name}")
        logging.info(f"ViewToken: {view_token}")
        
        url = self.build_url('ViewRPCService')
        
        # Build getData payload for this specific report
        # Format: getData with ViewToken, start row, and num rows
        payload = f'7|0|22|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|{view_token}|com.entrinsik.gwt.data.shared.LoadOptions/4020437150|java.util.HashMap/1797211028|com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl/346417575|java.util.ArrayList/4159755760|com.entrinsik.gwt.data.shared.criteria.Operator/2483661797|com.entrinsik.gwt.data.shared.criteria.impl.ValueExpressionImpl/3874770769|name|com.entrinsik.gwt.data.shared.criteria.Quantifier/3325804167|com.entrinsik.gwt.data.shared.values.StringValue/2414534542|**|com.entrinsik.informer.core.domain.report.ReportSearchOptions/1133289605|en_US|com.entrinsik.gwt.data.shared.Order/1651361273|com.entrinsik.gwt.data.shared.values.NullValue/2880996259|1|2|3|4|2|5|6|5|1|7|8|6|1|9|10|0|11|12|0|11|12|0|11|12|0|13|9|13|8|14|1|13|2|15|16|0|17|18|0|0|19|12|0|0|0|0|0|0|20|12|1|21|1|15|1|0|22|0|0|'
        
        try:
            response = self.session.post(url, data=payload, headers=self.gwt_headers)
            
            if response.status_code == 200:
                logging.info(f"✓ Data response received ({len(response.text)} bytes)")
                
                # Save raw response for analysis
                raw_file = self.output_dir / f"{report_name[:50]}_raw.txt"
                with open(raw_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                logging.info(f"✓ Raw response saved to: {raw_file.name}")
                
                # Parse the response
                strings, raw = GWTRPCParser.parse_data_response(response.text)
                
                if strings:
                    logging.info(f"✓ Extracted {len(strings)} strings from response")
                    
                    # Save parsed strings for analysis
                    parsed_file = self.output_dir / f"{report_name[:50]}_parsed.txt"
                    with open(parsed_file, 'w', encoding='utf-8') as f:
                        for i, s in enumerate(strings):
                            f.write(f"{i:4d}: {s}\n")
                    
                    logging.info(f"✓ Parsed data saved to: {parsed_file.name}")
                    return True
                else:
                    logging.warning("✗ No data could be parsed")
                    return False
            else:
                logging.error(f"✗ Failed to get data: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"✗ Extraction error: {e}")
            return False

    def extract_all_reports(self, limit=None):
        """Extract data from all discovered reports"""
        if not self.report_tokens:
            logging.error("No reports to extract!")
            return
        
        reports_list = list(self.report_tokens.items())
        
        if limit:
            reports_list = reports_list[:limit]
            logging.info(f"\nLimiting extraction to first {limit} reports")
        
        success = 0
        failed = 0
        
        for i, (name, token) in enumerate(reports_list, 1):
            logging.info(f"\n[{i}/{len(reports_list)}]")
            
            if self.extract_report_data(name, token):
                success += 1
            else:
                failed += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        logging.info(f"\n{'='*80}")
        logging.info("DATA EXTRACTION COMPLETE")
        logging.info(f"{'='*80}")
        logging.info(f"✓ Success: {success}")
        logging.info(f"✗ Failed: {failed}")

    def test_api_connection(self):
        """Test basic API connectivity"""
        logging.info("")
        logging.info("=" * 80)
        logging.info("TESTING API CONNECTION")
        logging.info("=" * 80)

        url = self.build_url('ViewRPCService')
        test_payload = '7|0|4|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getDynamicExportConfigs|1|2|3|4|0|'

        try:
            response = self.session.post(url, data=test_payload, headers=self.gwt_headers)
            logging.info(f"Status Code: {response.status_code}")
            logging.info(f"Response Preview: {response.text[:200]}")

            if response.status_code == 200:
                if response.text.startswith('//OK'):
                    logging.info("✓ API connection successful!")
                    return True
                elif 'IncompatibleRemoteServiceException' in response.text:
                    logging.info("✓ Authentication works (payload format needs adjustment)")
                    return True
            
            logging.error("✗ API connection failed")
            return False

        except Exception as e:
            logging.error(f"✗ Connection error: {e}")
            return False

    def run(self, extract_data=False, limit=None):
        """Main extraction process"""
        start_time = datetime.now()
        logging.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Test connection
        if not self.test_api_connection():
            logging.error("Cannot proceed without API connection")
            return

        # Discover reports
        reports = self.discover_reports()
        
        if not reports:
            logging.error("No reports discovered!")
            return

        # Extract data if requested
        if extract_data:
            self.extract_all_reports(limit=limit)

        # Summary
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        logging.info("")
        logging.info("=" * 80)
        logging.info("EXTRACTION COMPLETE")
        logging.info("=" * 80)
        logging.info(f"Duration: {elapsed:.1f} seconds")
        logging.info(f"Output: {self.output_dir.absolute()}")
        logging.info(f"✓ Discovered {len(reports)} reports")
        if extract_data:
            logging.info("✓ Data extraction attempted")
        logging.info("")
        logging.info("Check the output directory for:")
        logging.info("  - discovered_reports.txt (list of all reports)")
        logging.info("  - *_raw.txt (raw API responses)")
        logging.info("  - *_parsed.txt (parsed string tables)")
        logging.info("  - extraction.log (complete log)")
        logging.info("=" * 80)

def main():
    parser = argparse.ArgumentParser(description='Extract data from KeyedIn')
    parser.add_argument('--session-file', default='keyedin_session.json',
                       help='Session file with authentication')
    parser.add_argument('--extract-data', action='store_true',
                       help='Extract actual data from reports (not just discover)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of reports to extract (for testing)')

    args = parser.parse_args()

    extractor = KeyedInExtractor(args.session_file)
    extractor.run(extract_data=args.extract_data, limit=args.limit)

if __name__ == '__main__':
    main()