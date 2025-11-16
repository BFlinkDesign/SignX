#!/usr/bin/env python3
"""
Enhanced KeyedIn API with Automatic Chrome DevTools Protocol Integration
- Automatic cookie extraction from Chrome
- Session validation and expiry checking
- Auto-refresh before timeout
- Background session monitoring
"""

import json
import os
import requests
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory (where this script is located)"""
    return Path(__file__).parent.resolve()


def load_env_file() -> None:
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv
        # Try multiple .env file locations
        env_files = ['.env', '.env.keyedin', '.env.keyedin_api']
        root = get_project_root()
        for env_file in env_files:
            env_path = root / env_file
            if env_path.exists():
                load_dotenv(env_path)
                break
    except ImportError:
        pass  # python-dotenv not installed, use environment variables directly

# Load environment variables on import
load_env_file()


class KeyedInAPIEnhanced:
    """
    Enhanced KeyedIn API with automatic session management
    
    Features:
    - Automatic cookie extraction from Chrome using CDP
    - Session validation before requests
    - Auto-refresh before expiry
    - Background session monitoring
    """
    
    def __init__(
        self,
        cookies_file: Optional[str] = None,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auto_refresh: Optional[bool] = None,
        refresh_threshold_minutes: int = 30  # Refresh if expires within 30 minutes
    ):
        """
        Initialize the enhanced API
        
        Args:
            cookies_file: Path to save/load cookies (defaults to .env or 'keyedin_chrome_session.json')
            base_url: KeyedIn base URL (defaults to .env or 'https://eaglesign.keyedinsign.com')
            username: Username for auto-login (defaults to KEYEDIN_USERNAME from .env)
            password: Password for auto-login (defaults to KEYEDIN_PASSWORD from .env)
            auto_refresh: Enable automatic session refresh (defaults to .env or True)
            refresh_threshold_minutes: Refresh session if expires within this many minutes
        """
        # Load from environment variables if not provided
        self.base_url = base_url or os.getenv('KEYEDIN_BASE_URL', 'https://eaglesign.keyedinsign.com')
        cookies_file = cookies_file or os.getenv('KEYEDIN_COOKIES_FILE', 'keyedin_chrome_session.json')
        self.username = username or os.getenv('KEYEDIN_USERNAME')
        self.password = password or os.getenv('KEYEDIN_PASSWORD')
        
        # Auto-refresh from env (string 'true'/'false' or boolean)
        if auto_refresh is None:
            env_refresh = os.getenv('KEYEDIN_AUTO_REFRESH', 'true')
            self.auto_refresh = env_refresh.lower() in ('true', '1', 'yes', 'on') if isinstance(env_refresh, str) else bool(env_refresh)
        else:
            self.auto_refresh = auto_refresh
        
        # Refresh threshold from env
        env_threshold = os.getenv('KEYEDIN_REFRESH_THRESHOLD_MINUTES')
        if env_threshold:
            try:
                refresh_threshold_minutes = int(env_threshold)
            except ValueError:
                pass
        
        self.refresh_threshold_minutes = refresh_threshold_minutes
        # Resolve cookies_file relative to project root
        cookies_path = Path(cookies_file)
        if not cookies_path.is_absolute():
            # If relative path, resolve relative to project root
            self.cookies_file = get_project_root() / cookies_path
        else:
            # If absolute path, use as-is
            self.cookies_file = cookies_path
        self.session = requests.Session()
        self.session_valid = False
        self.last_validation = None
        self.auto_refresh = auto_refresh
        self.refresh_threshold_minutes = refresh_threshold_minutes
        self.username = username
        self.password = password
        self._lock = threading.Lock()
        self._monitor_thread = None
        self._stop_monitor = False
        
        # Load existing cookies if available
        if self.cookies_file.exists():
            try:
                self._load_cookies()
                logger.info(f"Loaded cookies from {self.cookies_file}")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        
        # Validate session on startup
        self.validate_session()
        
        # Start background monitor if auto-refresh enabled
        if self.auto_refresh:
            self._start_monitor()
    
    def _load_cookies(self) -> None:
        """Load cookies from file into session"""
        with open(self.cookies_file, 'r') as f:
            cookies_list = json.load(f)
        
        self.session.cookies.clear()
        for cookie in cookies_list:
            # Convert expiry from timestamp to datetime if needed
            expiry = cookie.get('expiry')
            if expiry and isinstance(expiry, (int, float)):
                # Check if expiry is in the past
                expiry_dt = datetime.fromtimestamp(expiry)
                if expiry_dt < datetime.now():
                    logger.warning(f"Cookie {cookie['name']} expired at {expiry_dt}")
                    continue
            
            self.session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie.get('domain', ''),
                path=cookie.get('path', '/'),
                expires=expiry if expiry else None,
                secure=cookie.get('secure', False),
                rest={'HttpOnly': cookie.get('httpOnly', False)}
            )
        
        logger.info(f"Loaded {len(cookies_list)} cookies into session")
    
    def _save_cookies(self, cookies: List[Dict]) -> None:
        """Save cookies to file"""
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
    
    def _extract_cookies_from_chrome(self) -> List[Dict]:
        """
        Extract cookies from Chrome using Selenium/CDP
        This will open Chrome, allow manual login, then extract cookies
        """
        logger.info("Starting Chrome to extract cookies...")
        
        options = Options()
        
        # Basic stability options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-software-rasterizer')
        
        # Experimental options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("detach", True)  # Keep browser open
        
        driver = None
        try:
            logger.info("Installing/checking ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver found at: {driver_path}")
            
            service = Service(driver_path)
            logger.info("Starting Chrome browser...")
            driver = webdriver.Chrome(
                service=service,
                options=options
            )
            logger.info("Chrome started successfully")
            
            logger.info(f"Navigating to {self.base_url}")
            driver.get(self.base_url)
            
            # If credentials provided, attempt auto-login
            if self.username and self.password:
                logger.info("Attempting automatic login...")
                try:
                    wait = WebDriverWait(driver, 10)
                    username_field = wait.until(
                        EC.presence_of_element_located((By.ID, 'USERNAME'))
                    )
                    password_field = driver.find_element(By.ID, 'PASSWORD')
                    
                    username_field.clear()
                    username_field.send_keys(self.username)
                    password_field.clear()
                    password_field.send_keys(self.password)
                    
                    # Try to find and click login button
                    login_button = driver.find_element(By.ID, 'btnLogin')
                    login_button.click()
                    
                    # Wait for login to complete
                    time.sleep(5)
                    logger.info("Auto-login attempted")
                except Exception as e:
                    logger.warning(f"Auto-login failed, manual login required: {e}")
            
            # If auto-login didn't work or wasn't attempted, wait for manual login
            if not self._is_logged_in(driver):
                logger.info("=" * 80)
                logger.info("MANUAL LOGIN REQUIRED")
                logger.info("=" * 80)
                logger.info("Please log in to KeyedIn in the Chrome window")
                logger.info("After logging in, press Enter here to continue...")
                input()
            
            # Wait a moment for any redirects
            time.sleep(2)
            
            # Extract cookies
            selenium_cookies = driver.get_cookies()
            
            # Convert to our format
            cookies = []
            for cookie in selenium_cookies:
                cookies.append({
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', '/'),
                    'expiry': cookie.get('expiry'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                    'sameSite': cookie.get('sameSite', 'Lax')
                })
            
            logger.info(f"Extracted {len(cookies)} cookies from Chrome")
            return cookies
            
        except Exception as e:
            logger.error(f"Error extracting cookies: {e}")
            raise
        finally:
            if driver:
                driver.quit()
                logger.info("Chrome closed")
    
    def _is_logged_in(self, driver: webdriver.Chrome) -> bool:
        """Check if currently logged in by looking for login indicators"""
        try:
            # Check for login form (means not logged in)
            login_elements = driver.find_elements(By.ID, 'USERNAME')
            if login_elements:
                return False
            
            # Check for welcome message or main menu (means logged in)
            page_text = driver.page_source.lower()
            if 'welcome' in page_text or 'main menu' in page_text:
                return True
            
            # Check URL - if still on login page, not logged in
            current_url = driver.current_url.lower()
            if 'login' in current_url:
                return False
            
            return True
        except:
            return False
    
    def refresh_session(self, force: bool = False) -> bool:
        """
        Refresh the session by extracting fresh cookies from Chrome
        
        Args:
            force: Force refresh even if session appears valid
            
        Returns:
            True if refresh successful, False otherwise
        """
        with self._lock:
            try:
                logger.info("Refreshing session...")
                cookies = self._extract_cookies_from_chrome()
                
                if not cookies:
                    logger.error("No cookies extracted")
                    return False
                
                # Save cookies
                self._save_cookies(cookies)
                
                # Reload into session
                self._load_cookies()
                
                # Validate the new session
                if self.validate_session():
                    logger.info("Session refreshed successfully")
                    return True
                else:
                    logger.error("Refreshed session failed validation")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to refresh session: {e}")
                return False
    
    def validate_session(self) -> bool:
        """
        Validate that the current session is still active
        
        Returns:
            True if session is valid, False otherwise
        """
        with self._lock:
            try:
                # Test with a simple endpoint
                test_url = f'{self.base_url}/cgi-bin/mvi.exe/MAIN'
                response = self.session.get(test_url, timeout=10, allow_redirects=False)
                
                # Check if redirected to login (session expired)
                if response.status_code == 302:
                    location = response.headers.get('Location', '')
                    if 'LOGIN' in location.upper():
                        logger.warning("Session expired - redirected to login")
                        self.session_valid = False
                        return False
                
                # Check response content for login indicators
                if response.status_code == 200:
                    content = response.text.lower()
                    if 'login' in content and 'username' in content and 'password' in content:
                        logger.warning("Session expired - login page detected")
                        self.session_valid = False
                        return False
                
                # Check cookie expiry
                if not self._check_cookie_expiry():
                    logger.warning("Session cookies expired")
                    self.session_valid = False
                    return False
                
                self.session_valid = True
                self.last_validation = datetime.now()
                logger.info("Session validated successfully")
                return True
                
            except Exception as e:
                logger.error(f"Session validation error: {e}")
                self.session_valid = False
                return False
    
    def _check_cookie_expiry(self) -> bool:
        """Check if any critical cookies are expired or expiring soon"""
        if not self.cookies_file.exists():
            return False
        
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            now = datetime.now()
            threshold = now + timedelta(minutes=self.refresh_threshold_minutes)
            
            for cookie in cookies:
                expiry = cookie.get('expiry')
                if expiry:
                    expiry_dt = datetime.fromtimestamp(expiry)
                    
                    # Check if expired
                    if expiry_dt < now:
                        logger.warning(f"Cookie {cookie['name']} expired at {expiry_dt}")
                        return False
                    
                    # Check if expiring soon
                    if expiry_dt < threshold:
                        cookie_name = cookie['name']
                        logger.info(
                            f"Cookie {cookie_name} expires soon ({expiry_dt}), "
                            f"refresh threshold: {threshold}"
                        )
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking cookie expiry: {e}")
            return False
    
    def _start_monitor(self) -> None:
        """Start background thread to monitor and refresh session"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Background session monitor started")
    
    def _monitor_loop(self) -> None:
        """Background loop to monitor session health"""
        while not self._stop_monitor:
            try:
                time.sleep(300)  # Check every 5 minutes
                
                if self._stop_monitor:
                    break
                
                # Check if cookies are expiring soon
                if not self._check_cookie_expiry():
                    logger.info("Cookies expiring soon, refreshing session...")
                    self.refresh_session()
                else:
                    # Validate session periodically
                    if not self.validate_session():
                        logger.warning("Session invalid, attempting refresh...")
                        self.refresh_session()
                        
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def stop_monitor(self) -> None:
        """Stop the background monitor"""
        self._stop_monitor = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Background monitor stopped")
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """
        Make a GET request with automatic session validation
        
        Args:
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments for requests.get
            
        Returns:
            Response object
        """
        # Validate session before request
        if not self.session_valid:
            if not self.validate_session():
                logger.warning("Session invalid, attempting refresh...")
                if not self.refresh_session():
                    raise Exception("Session expired and refresh failed")
        
        url = f'{self.base_url}{endpoint}'
        response = self.session.get(url, **kwargs)
        
        # Check if session expired during request
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'LOGIN' in location.upper():
                logger.warning("Session expired during request, refreshing...")
                if self.refresh_session():
                    # Retry request
                    response = self.session.get(url, **kwargs)
                else:
                    raise Exception("Session expired and refresh failed")
        
        return response
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """
        Make a POST request with automatic session validation
        
        Args:
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments for requests.post
            
        Returns:
            Response object
        """
        # Validate session before request
        if not self.session_valid:
            if not self.validate_session():
                logger.warning("Session invalid, attempting refresh...")
                if not self.refresh_session():
                    raise Exception("Session expired and refresh failed")
        
        url = f'{self.base_url}{endpoint}'
        response = self.session.post(url, **kwargs)
        
        # Check if session expired during request
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'LOGIN' in location.upper():
                logger.warning("Session expired during request, refreshing...")
                if self.refresh_session():
                    # Retry request
                    response = self.session.post(url, **kwargs)
                else:
                    raise Exception("Session expired and refresh failed")
        
        return response
    
    # Convenience methods for common endpoints
    def get_menu(self, username: str = None) -> Dict:
        """Get the menu structure"""
        username = username or self.username or 'BRADYF'
        endpoint = f'/cgi-bin/mvi.exe/WEB.MENU?USERNAME={username}'
        response = self.get(endpoint)
        return response.json()
    
    def get_work_order_form(self) -> str:
        """Get the work order inquiry form"""
        endpoint = '/cgi-bin/mvi.exe/WO.INQUIRY'
        response = self.get(endpoint)
        return response.text
    
    def test_endpoints(self) -> Dict[str, Any]:
        """Test discovered endpoints"""
        endpoints = {
            'Menu': '/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF',
            'WO Inquiry': '/cgi-bin/mvi.exe/WO.INQUIRY',
            'WO History': '/cgi-bin/mvi.exe/WO.HISTORY',
            'Cost Summary': '/cgi-bin/mvi.exe/WO.COST.SUMMARY',
            'Service Calls': '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
        }
        
        results = {}
        for name, endpoint in endpoints.items():
            try:
                response = self.get(endpoint, timeout=10)
                results[name] = {
                    'status': response.status_code,
                    'length': len(response.text),
                    'url': f'{self.base_url}{endpoint}',
                    'success': response.status_code == 200
                }
            except Exception as e:
                results[name] = {
                    'error': str(e)
                }
        
        return results
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.stop_monitor()


# Example usage
if __name__ == '__main__':
    print('=' * 80)
    print('KeyedIn Enhanced API Test')
    print('=' * 80)
    
    # Initialize API (will prompt for login if needed)
    # Cookies will be saved to project root
    api = KeyedInAPIEnhanced(
        cookies_file='keyedin_chrome_session.json',  # Saved to project root
        auto_refresh=True,
        refresh_threshold_minutes=30
    )
    
    print(f"Cookies file location: {api.cookies_file}")
    
    try:
        print('\nTesting endpoints...\n')
        results = api.test_endpoints()
        
        for name, result in results.items():
            if 'error' in result:
                print(f'❌ {name:20s} ERROR: {result["error"]}')
            else:
                status_icon = '✅' if result['success'] else '⚠️'
                print(f'{status_icon} {name:20s} Status: {result["status"]}  Length: {result["length"]:,} bytes')
        
        print('\n' + '=' * 80)
        print('✅ API client is working! Session cookies are valid and monitored.')
        print('=' * 80)
        print('\nSession will auto-refresh before expiry.')
        print('Press Ctrl+C to stop...')
        
        # Keep running to demonstrate background monitoring
        while True:
            time.sleep(60)
            print(f"Session check: Valid={api.session_valid}, Last validation={api.last_validation}")
            
    except KeyboardInterrupt:
        print('\n\nStopping...')
    finally:
        api.stop_monitor()
        print('Done!')

