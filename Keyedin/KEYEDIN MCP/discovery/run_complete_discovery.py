#!/usr/bin/env python3
"""
KeyedIn Complete System Discovery - Main Execution Script

This script orchestrates the complete discovery process and report generation.

Usage:
    # Full discovery (runs 2-4 hours)
    python run_complete_discovery.py --full
    
    # Quick targeted discovery (specific sections only)
    python run_complete_discovery.py --quick
    
    # Generate reports from existing discovery data
    python run_complete_discovery.py --reports-only
"""

import asyncio
import os
import sys
from pathlib import Path
import argparse
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from keyedin_architecture_mapper import KeyedInArchitectureMapper
from report_generators import generate_all_reports


def load_credentials():
    """Load KeyedIn credentials from environment or .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not installed, using environment variables only")
    
    base_url = os.getenv('KEYEDIN_BASE_URL')
    username = os.getenv('KEYEDIN_USERNAME')
    password = os.getenv('KEYEDIN_PASSWORD')
    
    if not all([base_url, username, password]):
        print("ERROR: Missing credentials!")
        print("Please set environment variables or create .env file with:")
        print("  KEYEDIN_BASE_URL=https://your-keyedin-url.com")
        print("  KEYEDIN_USERNAME=your_username")
        print("  KEYEDIN_PASSWORD=your_password")
        sys.exit(1)
    
    return base_url, username, password


async def run_full_discovery(output_dir: str = "KeyedIn_System_Map"):
    """Execute complete system discovery"""
    
    print("=" * 70)
    print("KeyedIn Complete System Discovery")
    print("=" * 70)
    print()
    
    base_url, username, password = load_credentials()
    
    print(f"Base URL: {base_url}")
    print(f"Username: {username}")
    print(f"Output Directory: {output_dir}")
    print()
    
    print("Starting full discovery process...")
    print("This will take 2-4 hours to complete.")
    print()
    
    start_time = datetime.now()
    
    # Initialize mapper
    mapper = KeyedInArchitectureMapper(base_url, output_dir)
    
    # Run discovery
    await mapper.run_full_discovery(username, password)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print()
    print("=" * 70)
    print(f"Discovery completed in {duration}")
    print("=" * 70)
    print()
    
    # Generate reports
    print("Generating comprehensive reports...")
    discovery_file = Path(output_dir) / 'discovery_data' / 'raw_discovery.json'
    
    if discovery_file.exists():
        generate_all_reports(str(discovery_file), output_dir)
    else:
        print(f"Warning: Discovery file not found at {discovery_file}")
    
    print()
    print("[OK] Complete system map generated!")
    print()
    print(f"[>>] Output location: {output_dir}/")
    print()
    print("Key deliverables:")
    print(f"  - {output_dir}/TECHNICAL_ARCHITECTURE.md")
    print(f"  - {output_dir}/API_FEASIBILITY_REPORT.md")
    print(f"  - {output_dir}/discovery_data/raw_discovery.json")
    print(f"  - {output_dir}/discovery_data/screenshots/ (visual documentation)")
    print()


async def run_quick_discovery(output_dir: str = "KeyedIn_System_Map"):
    """Execute targeted discovery of high-priority sections only"""
    
    print("=" * 70)
    print("KeyedIn Quick Discovery (High-Priority Sections)")
    print("=" * 70)
    print()
    
    base_url, username, password = load_credentials()
    
    # Priority sections for quick analysis
    priority_sections = [
        "Work Orders",
        "CRM",
        "Project Management",
        "Inventory and Parts",
        "Job Cost"
    ]
    
    print(f"Targeting {len(priority_sections)} high-priority sections:")
    for section in priority_sections:
        print(f"  - {section}")
    print()
    
    start_time = datetime.now()
    
    mapper = KeyedInArchitectureMapper(base_url, output_dir)
    await mapper.initialize_browser()
    
    if not await mapper.login(username, password):
        print("ERROR: Login failed!")
        return
    
    # Discover navigation
    await mapper.discover_navigation_structure()
    
    # Explore priority sections
    for section in priority_sections:
        print(f"\nExploring: {section}")
        try:
            await mapper.explore_section(section, depth=2)
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Save results
    await mapper.save_discovery_results()
    
    # Close browser
    if mapper.browser:
        await mapper.browser.close()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print()
    print(f"[OK] Quick discovery completed in {duration}")
    
    # Generate reports
    print("\nGenerating reports...")
    discovery_file = Path(output_dir) / 'discovery_data' / 'raw_discovery.json'
    generate_all_reports(str(discovery_file), output_dir)
    
    print(f"\n[>>] Results saved to: {output_dir}/")


def generate_reports_only(output_dir: str = "KeyedIn_System_Map"):
    """Generate reports from existing discovery data"""
    
    print("=" * 70)
    print("Generating Reports from Existing Discovery Data")
    print("=" * 70)
    print()
    
    discovery_file = Path(output_dir) / 'discovery_data' / 'raw_discovery.json'
    
    if not discovery_file.exists():
        print(f"ERROR: Discovery file not found at {discovery_file}")
        print("Please run discovery first with --full or --quick")
        return
    
    print(f"Using discovery data: {discovery_file}")
    print()
    
    generate_all_reports(str(discovery_file), output_dir)
    
    print()
    print(f"[OK] Reports generated in: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description='KeyedIn Complete System Discovery',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full discovery (2-4 hours)
  python run_complete_discovery.py --full

  # Quick discovery (30-60 minutes, priority sections only)
  python run_complete_discovery.py --quick

  # Generate reports from existing data
  python run_complete_discovery.py --reports-only

  # Specify custom output directory
  python run_complete_discovery.py --full --output my_custom_dir
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--full', action='store_true',
                       help='Run complete deep-dive discovery (2-4 hours)')
    group.add_argument('--quick', action='store_true',
                       help='Run targeted discovery of priority sections (30-60 min)')
    group.add_argument('--reports-only', action='store_true',
                       help='Generate reports from existing discovery data')
    
    parser.add_argument('--output', default='KeyedIn_System_Map',
                        help='Output directory (default: KeyedIn_System_Map)')
    
    args = parser.parse_args()
    
    if args.full:
        asyncio.run(run_full_discovery(args.output))
    elif args.quick:
        asyncio.run(run_quick_discovery(args.output))
    elif args.reports_only:
        generate_reports_only(args.output)


if __name__ == '__main__':
    main()
