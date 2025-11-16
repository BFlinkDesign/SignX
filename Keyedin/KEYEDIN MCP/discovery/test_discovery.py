#!/usr/bin/env python3
"""
Test KeyedIn Discovery System

Quick test to verify login and basic functionality before running full discovery.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from keyedin_architecture_mapper import KeyedInArchitectureMapper
from dotenv import load_dotenv

async def test_login():
    """Test login functionality"""
    
    print("=" * 70)
    print("KeyedIn Discovery System - Login Test")
    print("=" * 70)
    print()
    
    # Load credentials
    load_dotenv(Path(__file__).parent.parent / '.env')
    
    base_url = os.getenv('KEYEDIN_BASE_URL')
    username = os.getenv('KEYEDIN_USERNAME')
    password = os.getenv('KEYEDIN_PASSWORD')
    
    if not all([base_url, username, password]):
        print("[ERROR] Missing credentials in .env file!")
        print("Required:")
        print("  KEYEDIN_BASE_URL=http://eaglesign.keyedinsign.com")
        print("  KEYEDIN_USERNAME=your_username")
        print("  KEYEDIN_PASSWORD=your_password")
        return False
    
    print(f"Base URL: {base_url}")
    print(f"Username: {username}")
    print()
    
    # Initialize mapper
    mapper = KeyedInArchitectureMapper(base_url, "test_output")
    
    try:
        print("[1/3] Initializing browser...")
        await mapper.initialize_browser()
        print("[OK] Browser initialized")
        print()
        
        print("[2/3] Attempting login...")
        print("(Watch for browser window - may need to handle prompts)")
        success = await mapper.login(username, password)
        
        if success:
            print("[OK] Login successful!")
            print()
            
            print("[3/3] Testing navigation discovery...")
            await mapper.discover_navigation_structure()
            nav_count = len(mapper.navigation_tree)
            print(f"[OK] Discovered {nav_count} navigation items")
            print()
            
            # Show some discovered links
            if mapper.navigation_tree:
                print("Sample navigation items:")
                for node in mapper.navigation_tree[:5]:
                    print(f"  - {node.label}")
            print()
            
            print("=" * 70)
            print("TEST PASSED - System ready for full discovery!")
            print("=" * 70)
            print()
            print("Run full discovery with:")
            print("  python run_complete_discovery.py --full --output ..\\KeyedIn_System_Map")
            print()
            
            return True
        else:
            print("[FAILED] Login unsuccessful")
            print()
            print("Possible issues:")
            print("  1. Incorrect credentials in .env file")
            print("  2. KeyedIn not accessible (VPN/network)")
            print("  3. License quota exceeded (too many users)")
            print("  4. Browser prompts need interaction")
            print()
            print("Try:")
            print("  - Verify credentials")
            print("  - Check KeyedIn access in regular browser")
            print("  - Run during business hours")
            print()
            return False
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if mapper.browser:
            await mapper.browser.close()

def main():
    try:
        result = asyncio.run(test_login())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()


