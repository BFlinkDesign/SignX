@echo off
title KeyedIn Complete Setup - Windows 11
cd /d "%USERPROFILE%\Desktop"
mkdir KeyedIn-Automation 2>nul
cd KeyedIn-Automation

echo Creating Python script...
(
echo import os
echo import sys
echo import subprocess
echo import getpass
echo from datetime import datetime
echo.
echo print("KeyedIn Automation Installer"^)
echo print("=" * 40^)
echo.
echo # Install playwright if needed
echo try:
echo     import playwright
echo except:
echo     print("Installing playwright..."^)
echo     subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"]^)
echo     subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"]^)
echo.
echo from playwright.sync_api import sync_playwright
echo.
echo url = "https://eaglesign.keyedinsign.com/cgi-bin/mvt.exe/LOGIN.START"
echo username = input("Enter KeyedIn username: "^)
echo password = getpass.getpass("Enter KeyedIn password: "^)
echo.
echo print("Opening KeyedIn..."^)
echo.
echo with sync_playwright(^) as p:
echo     browser = p.chromium.launch(headless=False^)
echo     page = browser.new_page(^)
echo     page.goto(url^)
echo     
echo     # Try to login
echo     try:
echo         page.fill('input[type="text"]', username^)
echo         page.fill('input[type="password"]', password^)
echo         page.click('input[type="submit"]'^)
echo         print("Login attempted!"^)
echo     except:
echo         print("Could not find login fields"^)
echo     
echo     input("Press Enter to close..."^)
echo     browser.close(^)
) > keyedin_auto.py

echo.
echo Running automation...
python keyedin_auto.py
pause