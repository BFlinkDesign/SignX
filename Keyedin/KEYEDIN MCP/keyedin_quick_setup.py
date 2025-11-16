#!/usr/bin/env python3
"""
Quick MCP Test - Run this NOW to validate KeyedIn connection
"""

import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

async def test_keyedin_now():
    """Immediate test of KeyedIn access"""
    
    print("🦅 Eagle KeyedIn Quick Test\n")
    
    # Check credentials
    username = os.getenv('KEYEDIN_USERNAME')
    password = os.getenv('KEYEDIN_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: Edit .env file first!")
        print("   Add your KeyedIn username and password")
        return
    
    print(f"✓ Found credentials for: {username}")
    
    # Test browser connection
    print("\nTesting browser connection...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        page = await browser.new_page()
        
        try:
            # Go to KeyedIn
            print("Navigating to KeyedIn...")
            await page.goto("http://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START")
            await page.wait_for_timeout(2000)
            
            # Try login
            print("Attempting login...")
            await page.fill('#USERNAME', username)
            await page.fill('#PASSWORD', password)
            await page.click('#btnLogin')
            await page.wait_for_timeout(3000)
            
            # Check result
            content = await page.content()
            
            if 'Welcome,' in content:
                print("\n✅ SUCCESS! Logged into KeyedIn")
                print("\nVisible sections:")
                
                # Find all links
                links = await page.query_selector_all('a')
                sections = []
                for link in links[:20]:  # First 20 links
                    text = await link.text_content()
                    if text and len(text) > 3:
                        sections.append(text.strip())
                
                for section in sections[:10]:
                    print(f"  - {section}")
                
                # Try to navigate to Job Cost
                print("\nTesting navigation to Job Cost...")
                try:
                    await page.click('a:has-text("Job Cost")')
                    await page.wait_for_timeout(2000)
                    print("✅ Successfully navigated to Job Cost")
                except:
                    print("⚠️  Could not auto-navigate - may need manual selection")
                
            else:
                print("\n❌ Login failed - check credentials")
                if 'LICENSE QUOTA' in content:
                    print("   Reason: Too many users logged in")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            
        finally:
            print("\nPress Enter to close browser...")
            input()
            await browser.close()

if __name__ == "__main__":
    # Create .env if missing
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("KEYEDIN_USERNAME=\nKEYEDIN_PASSWORD=\n")
        print("Created .env file - add your credentials and run again")
    else:
        asyncio.run(test_keyedin_now())