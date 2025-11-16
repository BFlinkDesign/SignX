#!/usr/bin/env python3
"""
Chrome/ChromeDriver Troubleshooting Script
Helps diagnose Chrome session creation issues
"""

import sys
import subprocess
from pathlib import Path

def check_chrome_installed():
    """Check if Chrome is installed"""
    print("=" * 80)
    print("Checking Chrome Installation")
    print("=" * 80)
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(
            Path.home().name
        )
    ]
    
    found = False
    for path in chrome_paths:
        if Path(path).exists():
            print(f"[OK] Chrome found at: {path}")
            found = True
            
            # Try to get version
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"  Version: {result.stdout.strip()}")
            except:
                pass
    
    if not found:
        print("[FAIL] Chrome not found in common locations")
        print("  Please install Google Chrome from: https://www.google.com/chrome/")
    
    return found

def check_chromedriver():
    """Check ChromeDriver installation"""
    print("\n" + "=" * 80)
    print("Checking ChromeDriver")
    print("=" * 80)
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("✓ webdriver-manager installed")
        
        try:
            driver_path = ChromeDriverManager().install()
            print(f"[OK] ChromeDriver found at: {driver_path}")
            return True
        except Exception as e:
            print(f"[FAIL] ChromeDriver installation failed: {e}")
            return False
    except ImportError:
        print("[FAIL] webdriver-manager not installed")
        print("  Install with: pip install webdriver-manager")
        return False

def check_running_chrome():
    """Check if Chrome is already running"""
    print("\n" + "=" * 80)
    print("Checking Running Chrome Processes")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "chrome.exe" in result.stdout:
            print("[WARN] Chrome is currently running")
            print("  Try closing all Chrome windows and running again")
            return True
        else:
            print("[OK] No Chrome processes running")
            return False
    except Exception as e:
        print(f"[FAIL] Could not check Chrome processes: {e}")
        return False

def check_selenium():
    """Check Selenium installation"""
    print("\n" + "=" * 80)
    print("Checking Selenium")
    print("=" * 80)
    
    try:
        import selenium
        print(f"[OK] Selenium installed (version: {selenium.__version__})")
        return True
    except ImportError:
        print("[FAIL] Selenium not installed")
        print("  Install with: pip install selenium")
        return False

def test_chrome_startup():
    """Try to start Chrome with Selenium"""
    print("\n" + "=" * 80)
    print("Testing Chrome Startup")
    print("=" * 80)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless')  # Run headless for test
        
        print("Attempting to start Chrome...")
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        print("[OK] Chrome started successfully!")
        
        driver.quit()
        print("[OK] Chrome closed successfully")
        return True
        
    except Exception as e:
        print(f"[FAIL] Chrome startup failed: {e}")
        print("\nError details:")
        print(f"  {type(e).__name__}: {str(e)}")
        return False

def main():
    """Run all checks"""
    print("\n" + "=" * 80)
    print("Chrome/ChromeDriver Troubleshooting")
    print("=" * 80)
    
    checks = [
        ("Chrome Installation", check_chrome_installed),
        ("ChromeDriver", check_chromedriver),
        ("Running Chrome", check_running_chrome),
        ("Selenium", check_selenium),
        ("Chrome Startup Test", test_chrome_startup)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] Error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("[SUCCESS] All checks passed!")
        print("Chrome should work with the extractor now.")
    else:
        print("[WARNING] Some checks failed.")
        print("\nCommon fixes:")
        print("1. Close all Chrome windows")
        print("2. Update Chrome: chrome://settings/help")
        print("3. Reinstall ChromeDriver: pip install --upgrade webdriver-manager")
        print("4. Check antivirus isn't blocking Chrome")
    print("=" * 80)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

