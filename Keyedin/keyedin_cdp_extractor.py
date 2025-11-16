#!/usr/bin/env python3
"""
Chrome DevTools Protocol (CDP) Cookie Extractor for KeyedIn
Automatically extracts cookies and network requests from Chrome
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_env_file() -> None:
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv
        # Try multiple .env file locations
        env_files = ['.env', '.env.keyedin', '.env.keyedin_api']
        root = Path(__file__).parent
        for env_file in env_files:
            env_path = root / env_file
            if env_path.exists():
                load_dotenv(env_path)
                break
    except ImportError:
        pass  # python-dotenv not installed

# Load environment variables on import
load_env_file()


def get_project_root() -> Path:
    """Get the project root directory (where this script is located)"""
    return Path(__file__).parent.resolve()


class KeyedInCDPExtractor:
    """
    Extract cookies and network data from Chrome using CDP
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        # Load from environment variables if not provided
        self.base_url = base_url or os.getenv('KEYEDIN_BASE_URL', 'https://eaglesign.keyedinsign.com')
        self.username = username or os.getenv('KEYEDIN_USERNAME')
        self.password = password or os.getenv('KEYEDIN_PASSWORD')
        self.driver = None
        self.captured_requests = []
    
    def extract_session(
        self,
        output_file: str = 'keyedin_chrome_session.json',
        capture_network: bool = True
    ) -> Dict:
        """
        Extract session cookies and optionally network requests
        
        Args:
            output_file: File to save cookies
            capture_network: Also capture network requests
            
        Returns:
            Dictionary with cookies and network data
        """
        logger.info("Starting Chrome with CDP...")
        
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
        
        # Enable performance logging for network capture
        if capture_network:
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # Try to get ChromeDriver with better error handling
        try:
            logger.info("Installing/checking ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver found at: {driver_path}")
            
            # Create service with verbose logging for troubleshooting
            service = Service(driver_path)
            
            logger.info("Starting Chrome browser...")
            self.driver = webdriver.Chrome(
                service=service,
                options=options
            )
            logger.info("Chrome started successfully")
            
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(2)
            
            # Attempt auto-login if credentials provided
            if self.username and self.password:
                if self._attempt_login():
                    logger.info("Auto-login successful")
                else:
                    logger.info("Auto-login failed, manual login required")
                    self._wait_for_manual_login()
            else:
                self._wait_for_manual_login()
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Extract cookies
            logger.info("Extracting cookies...")
            cookies = self._extract_cookies()
            
            # Extract network requests if requested
            network_data = None
            if capture_network:
                logger.info("Capturing network requests...")
                network_data = self._extract_network_requests()
            
            # Save cookies - resolve path relative to project root
            output_path = Path(output_file)
            if not output_path.is_absolute():
                # If relative path, resolve relative to project root
                output_path = get_project_root() / output_path
            else:
                # If absolute path, use as-is
                output_path = output_path
            
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} cookies to {output_path}")
            
            # Save network data if captured
            if network_data:
                network_file = output_path.parent / f"{output_path.stem}_network.json"
                with open(network_file, 'w') as f:
                    json.dump(network_data, f, indent=2)
                logger.info(f"Saved network data to {network_file}")
            
            return {
                'cookies': cookies,
                'network': network_data,
                'url': self.driver.current_url,
                'title': self.driver.title
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during extraction: {error_msg}")
            
            # Provide helpful troubleshooting information
            logger.error("\n" + "=" * 80)
            logger.error("TROUBLESHOOTING")
            logger.error("=" * 80)
            logger.error("Common causes:")
            logger.error("1. Chrome browser not installed or not in PATH")
            logger.error("2. ChromeDriver version mismatch with Chrome browser")
            logger.error("3. Chrome already running with incompatible flags")
            logger.error("4. Antivirus/security software blocking Chrome")
            logger.error("\nTry these solutions:")
            logger.error("1. Close all Chrome windows and try again")
            logger.error("2. Update Chrome browser to latest version")
            logger.error("3. Run: python -c 'from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()'")
            logger.error("4. Check Chrome version: chrome://version/")
            logger.error("=" * 80)
            
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Chrome closed")
    
    def _attempt_login(self) -> bool:
        """Attempt automatic login"""
        try:
            logger.info(f"Attempting auto-login for user: {self.username}")
            
            # Wait for page to load
            time.sleep(2)
            
            # Try multiple selectors for username field
            username_field = None
            for selector in [By.ID, By.NAME, By.CSS_SELECTOR]:
                try:
                    if selector == By.ID:
                        username_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'USERNAME'))
                        )
                    elif selector == By.NAME:
                        username_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.NAME, 'USERNAME'))
                        )
                    else:
                        username_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="USERNAME"], input[id="USERNAME"]'))
                        )
                    break
                except:
                    continue
            
            if not username_field:
                logger.warning("Could not find username field")
                return False
            
            # Find password field
            password_field = self.driver.find_element(By.ID, 'PASSWORD')
            
            # Clear and fill fields
            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(0.5)
            
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.5)
            
            # Find and click login button
            login_button = None
            for selector in [By.ID, By.CSS_SELECTOR, By.XPATH]:
                try:
                    if selector == By.ID:
                        login_button = self.driver.find_element(By.ID, 'btnLogin')
                    elif selector == By.CSS_SELECTOR:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
                    else:
                        login_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Login")] | //input[@value="Login"]')
                    break
                except:
                    continue
            
            if not login_button:
                logger.warning("Could not find login button")
                return False
            
            logger.info("Clicking login button...")
            login_button.click()
            
            # Wait for login to complete (check for redirect or welcome message)
            logger.info("Waiting for login to complete...")
            time.sleep(8)  # Give more time for login
            
            # Check if login successful
            is_logged_in = self._is_logged_in()
            if is_logged_in:
                logger.info("Auto-login successful!")
            else:
                logger.warning("Login verification failed - may need manual login")
            
            return is_logged_in
        except Exception as e:
            logger.warning(f"Login attempt failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _wait_for_manual_login(self) -> None:
        """Wait for user to manually log in"""
        logger.info("=" * 80)
        logger.info("MANUAL LOGIN REQUIRED")
        logger.info("=" * 80)
        logger.info("Please log in to KeyedIn in the Chrome window")
        logger.info("After logging in, press Enter here to continue...")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            logger.warning("Input not available in non-interactive mode")
            logger.info("Waiting 30 seconds for you to log in manually...")
            import time
            time.sleep(30)  # Give user time to log in
            logger.info("Continuing with extraction...")
        
        # Verify login
        if not self._is_logged_in():
            logger.warning("Login verification failed, but continuing...")
    
    def _is_logged_in(self) -> bool:
        """Check if currently logged in"""
        try:
            # Check for login form
            login_elements = self.driver.find_elements(By.ID, 'USERNAME')
            if login_elements:
                return False
            
            # Check page content
            page_text = self.driver.page_source.lower()
            current_url = self.driver.current_url.lower()
            
            if 'login' in current_url and 'username' in page_text:
                return False
            
            if 'welcome' in page_text or 'main menu' in page_text:
                return True
            
            return True  # Assume logged in if no login form found
        except:
            return False
    
    def _extract_cookies(self) -> List[Dict]:
        """Extract cookies from current session"""
        selenium_cookies = self.driver.get_cookies()
        
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
        
        return cookies
    
    def _extract_network_requests(self) -> Dict:
        """Extract network requests from performance logs"""
        try:
            logs = self.driver.get_log('performance')
            
            requests = []
            responses = []
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    method = message.get('message', {}).get('method', '')
                    params = message.get('message', {}).get('params', {})
                    
                    if 'Network.requestWillBeSent' in method:
                        request = params.get('request', {})
                        url = request.get('url', '')
                        
                        # Filter for KeyedIn requests
                        if 'eaglesign.keyedinsign.com' in url:
                            requests.append({
                                'timestamp': log.get('timestamp', 0),
                                'method': request.get('method', ''),
                                'url': url,
                                'headers': request.get('headers', {}),
                                'postData': request.get('postData', '')
                            })
                    
                    elif 'Network.responseReceived' in method:
                        response = params.get('response', {})
                        url = response.get('url', '')
                        
                        if 'eaglesign.keyedinsign.com' in url:
                            responses.append({
                                'timestamp': log.get('timestamp', 0),
                                'url': url,
                                'status': response.get('status', 0),
                                'headers': response.get('headers', {})
                            })
                except:
                    continue
            
            # Deduplicate
            unique_requests = {}
            for req in requests:
                url = req['url']
                if url not in unique_requests:
                    unique_requests[url] = req
            
            return {
                'total_requests': len(requests),
                'unique_requests': len(unique_requests),
                'requests': list(unique_requests.values())[:50],  # Limit to 50
                'responses': responses[:50]
            }
        except Exception as e:
            logger.warning(f"Failed to extract network requests: {e}")
            return None


if __name__ == '__main__':
    import sys
    
    print('=' * 80)
    print('KeyedIn CDP Cookie Extractor')
    print('=' * 80)
    
    # Check for credentials in environment or command line
    username = None
    password = None
    
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    
    extractor = KeyedInCDPExtractor(
        username=username,
        password=password
    )
    
    result = extractor.extract_session(
        output_file='keyedin_chrome_session.json',
        capture_network=True
    )
    
    # Get the actual saved path
    output_path = get_project_root() / 'keyedin_chrome_session.json'
    
    print('\n' + '=' * 80)
    print('Extraction Complete!')
    print('=' * 80)
    print(f"Cookies extracted: {len(result['cookies'])}")
    if result['network']:
        print(f"Network requests captured: {result['network']['total_requests']}")
    print(f"Output file: {output_path}")
    print('=' * 80)

