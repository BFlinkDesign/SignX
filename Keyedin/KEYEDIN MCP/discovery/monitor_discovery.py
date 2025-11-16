#!/usr/bin/env python3
"""
Monitor KeyedIn Discovery Progress

Watches the discovery process and reports status.
"""

import json
import time
from pathlib import Path
from datetime import datetime

def monitor_discovery(output_dir="../KeyedIn_System_Map"):
    """Monitor discovery progress"""
    output_path = Path(output_dir)
    discovery_data_path = output_path / "discovery_data"
    screenshots_path = discovery_data_path / "screenshots"
    raw_discovery_file = discovery_data_path / "raw_discovery.json"
    
    print("=" * 70)
    print("KeyedIn Discovery Progress Monitor")
    print("=" * 70)
    print(f"Monitoring: {output_path.absolute()}")
    print()
    
    last_count = 0
    start_time = datetime.now()
    
    while True:
        # Check for screenshots (indicates progress)
        if screenshots_path.exists():
            screenshots = list(screenshots_path.glob("*.png"))
            screenshot_count = len(screenshots)
            
            if screenshot_count > last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Screenshots: {screenshot_count}")
                if screenshots:
                    latest = max(screenshots, key=lambda p: p.stat().st_mtime)
                    print(f"  Latest: {latest.name}")
                last_count = screenshot_count
        
        # Check if discovery is complete
        if raw_discovery_file.exists():
            try:
                with open(raw_discovery_file, 'r') as f:
                    data = json.load(f)
                
                stats = data.get('statistics', {})
                print()
                print("=" * 70)
                print("DISCOVERY COMPLETE!")
                print("=" * 70)
                print(f"Duration: {datetime.now() - start_time}")
                print(f"Endpoints discovered: {stats.get('total_endpoints', 0)}")
                print(f"Forms discovered: {stats.get('total_forms', 0)}")
                print(f"Entities discovered: {stats.get('total_entities', 0)}")
                print(f"URLs visited: {stats.get('urls_visited', 0)}")
                print()
                print(f"Results saved to: {output_path.absolute()}")
                break
            except json.JSONDecodeError:
                # File exists but not complete yet
                pass
        
        time.sleep(10)  # Check every 10 seconds

if __name__ == "__main__":
    try:
        monitor_discovery()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


