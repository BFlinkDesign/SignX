"""
KeyedIn Architecture Mapper - Master Discovery Agent

Systematically explores the entire KeyedIn system to create comprehensive
technical and strategic documentation for API development and modernization planning.

Usage:
    python keyedin_architecture_mapper.py --full-discovery
    python keyedin_architecture_mapper.py --section "Work Orders"
    python keyedin_architecture_mapper.py --analyze-only
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict, field
import logging
from collections import defaultdict

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DiscoveredEndpoint:
    """Represents a discovered CGI endpoint"""
    url: str
    method: str = "GET"
    parameters: Dict[str, Any] = field(default_factory=dict)
    section: str = ""
    subsection: str = ""
    purpose: str = ""
    response_type: str = "html"
    requires_auth: bool = True
    tested: bool = False
    notes: str = ""


@dataclass
class DiscoveredForm:
    """Represents a discovered form"""
    form_id: str
    action_url: str
    method: str
    fields: List[Dict[str, Any]] = field(default_factory=list)
    section: str = ""
    purpose: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredEntity:
    """Represents a discovered business entity"""
    entity_name: str
    fields: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    operations: Set[str] = field(default_factory=set)
    table_name: Optional[str] = None
    discovered_in: List[str] = field(default_factory=list)


@dataclass
class NavigationNode:
    """Represents a navigation menu item"""
    label: str
    url: Optional[str]
    parent: Optional[str]
    level: int
    has_children: bool
    section_type: str = ""


class KeyedInArchitectureMapper:
    """
    Master coordinator for KeyedIn system discovery.
    
    Orchestrates specialized collectors to systematically explore
    the entire system and generate comprehensive documentation.
    """
    
    def __init__(self, base_url: str, output_dir: str = "KeyedIn_System_Map"):
        self.base_url = base_url.rstrip('/')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        self.dirs = {
            'discovery_data': self.output_dir / 'discovery_data',
            'screenshots': self.output_dir / 'discovery_data' / 'screenshots',
            'html_captures': self.output_dir / 'discovery_data' / 'html_captures',
            'form_schemas': self.output_dir / 'discovery_data' / 'form_schemas',
            'table_structures': self.output_dir / 'discovery_data' / 'table_structures',
            'code': self.output_dir / 'code',
            'diagrams': self.output_dir / 'diagrams',
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Discovery state
        self.visited_urls: Set[str] = set()
        self.discovered_endpoints: List[DiscoveredEndpoint] = []
        self.discovered_forms: List[DiscoveredForm] = []
        self.discovered_entities: Dict[str, DiscoveredEntity] = {}
        self.navigation_tree: List[NavigationNode] = []
        self.workflow_sequences: List[Dict[str, Any]] = []
        
        # Known main sections from planning document
        self.main_sections = [
            "CRM",
            "Project Management",
            "Estimating and Proposals",
            "Sales Order Entry",
            "Shipping Tracking",
            "Sales Analysis",
            "Purchasing",
            "Inventory and Parts",
            "Job Cost",
            "Material Requirements Planning",
            "Production (Shop Floor Control)",
            "Resource Scheduling",
            "Labor and Payroll Processing",
            "Accounts Payable",
            "Accounts Receivable",
            "Report Administration",
            "Administration",
            "System Management"
        ]
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def initialize_browser(self):
        """Initialize Playwright browser with appropriate settings"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # Set True for unattended operation
            slow_mo=100  # Slight delay for stability
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = await self.context.new_page()
        
        # Set up request/response logging
        self.page.on('request', self._log_request)
        self.page.on('response', self._log_response)
        
        logger.info("Browser initialized successfully")
        
    def _log_request(self, request):
        """Log outgoing requests to discover endpoint patterns"""
        if '/cgi-bin/' in request.url:
            logger.debug(f"Request: {request.method} {request.url}")
            
    def _log_response(self, response):
        """Log responses to understand data formats"""
        if '/cgi-bin/' in response.url:
            logger.debug(f"Response: {response.status} {response.url}")
    
    async def login(self, username: str, password: str) -> bool:
        """
        Authenticate to KeyedIn system
        
        Args:
            username: KeyedIn username
            password: KeyedIn password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Attempting login to KeyedIn")
            await self.page.goto(f"{self.base_url}/cgi-bin/mvi.exe/LOGIN.START")
            
            # Fill login form
            await self.page.fill('#USERNAME', username)
            await self.page.fill('#PASSWORD', password)

            # Submit login - Try multiple approaches
            # Approach 1: Submit the form directly
            try:
                logger.info("Attempting to submit form directly")
                await self.page.evaluate('document.querySelector("form").submit()')
                logger.info("Form submitted directly")
            except Exception as e:
                logger.error(f"Direct form submit failed: {e}")

                # Approach 2: Call validateEntry() JavaScript function
                try:
                    logger.info("Calling validateEntry() JavaScript function")
                    await self.page.evaluate('validateEntry()')
                    logger.info("validateEntry() called")

                    # Wait and check for error messages
                    await self.page.wait_for_timeout(1000)
                    error_msg_visible = await self.page.is_visible('#ERROR_MSG_DISPLAY')
                    if error_msg_visible:
                        error_text = await self.page.inner_text('#ERROR_MSG')
                        logger.error(f"Login error: {error_text}")

                except Exception as e2:
                    logger.error(f"validateEntry() failed: {e2}")

                    # Approach 3: Click the button
                    try:
                        await self.page.click('#btnLogin', timeout=5000)
                        logger.info("Clicked login button as final fallback")
                    except Exception as e3:
                        logger.error(f"Button click also failed: {e3}")
            
            # Wait for navigation and redirect to complete
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            await self.page.wait_for_timeout(2500)  # Wait for redirect to complete

            # Log current URL for debugging
            current_url = self.page.url
            logger.info(f"Current URL after login attempt: {current_url}")

            # Capture screenshot after login attempt
            await self.page.screenshot(path='after_login_attempt.png')
            logger.info("Screenshot saved to after_login_attempt.png")

            # Check if login was successful
            page_content = await self.page.content()

            # Check for any error messages on page
            try:
                error_msg_visible = await self.page.is_visible('#ERROR_MSG_DISPLAY')
                if error_msg_visible:
                    error_text = await self.page.inner_text('#ERROR_MSG')
                    logger.error(f"Login page shows error: {error_text}")
            except:
                pass

            # Check for license quota error
            if "LICENSE QUOTA" in page_content:
                logger.error("Login failed - license quota exceeded")
                return False

            # Check if login was successful by looking for logged-in indicators
            # The URL may still contain "LOGIN" even after successful login
            if "Welcome," in page_content or "Profile" in page_content or "Logout" in page_content:
                logger.info("Login successful - detected logged-in content")
            elif "/LOGIN" not in current_url.upper():
                logger.info("Login successful - redirected away from login page")
            else:
                logger.error("Login failed - still on login page")
                # Log a snippet of the page content for debugging
                logger.error(f"Page content snippet: {page_content[:500]}")
                return False
            
            # Capture initial logged-in state
            await self._capture_screenshot("00_logged_in_home")
            await self._capture_html("00_logged_in_home")
            
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def discover_navigation_structure(self):
        """
        Map the complete navigation structure

        Identifies all menu items, their hierarchy, and targets
        """
        logger.info("Discovering navigation structure")

        try:
            # Parse navigation structure from current page
            html_content = await self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # Save a copy of the main page HTML for debugging
            await self._capture_html("00_main_page_for_nav_discovery")

            # The left sidebar navigation contains the main sections
            # Looking for all links in the page that match the main sections
            nav_links = soup.find_all('a', href=True)

            # Filter for navigation links based on the sections we know exist
            for link in nav_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)

                # Only include links that:
                # 1. Have text content
                # 2. Point to the CGI application (not external links)
                # 3. Are not profile/logout/help links
                if text and '/cgi-bin/' in href and text not in ['Profile', 'Password', 'Help', 'Logout']:
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        url = f"{self.base_url}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        url = f"{self.base_url}/{href}"

                    node = NavigationNode(
                        label=text,
                        url=url,
                        parent=None,
                        level=0,
                        has_children=False,
                    )
                    self.navigation_tree.append(node)
                    logger.debug(f"Found nav link: {text} -> {url}")

            logger.info(f"Discovered {len(self.navigation_tree)} navigation nodes")

            # Save navigation structure
            self._save_json(
                [asdict(node) for node in self.navigation_tree],
                self.dirs['discovery_data'] / 'navigation_structure.json'
            )

        except Exception as e:
            logger.error(f"Error discovering navigation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def explore_section(self, section_name: str, depth: int = 2):
        """
        Deep exploration of a specific section

        Args:
            section_name: Name of section to explore (e.g., "Work Orders")
            depth: How many levels deep to explore (default: 2)
        """
        logger.info(f"Exploring section: {section_name} (depth: {depth})")

        try:
            # Try to click the navigation link using Playwright
            # First, try to find a link with exact text match
            try:
                link = await self.page.query_selector(f'a:has-text("{section_name}")')
                if link:
                    logger.info(f"Found link for section '{section_name}', clicking...")
                    await link.click()
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                else:
                    # Fallback: try finding from navigation tree
                    nav_link = self._find_nav_link(section_name)
                    if not nav_link:
                        logger.warning(f"Could not find navigation link for: {section_name}")
                        return
                    logger.info(f"Navigating to URL: {nav_link}")
                    await self.page.goto(nav_link)
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
            except Exception as e:
                logger.warning(f"Error clicking link for {section_name}: {e}")
                # Fallback to URL navigation
                nav_link = self._find_nav_link(section_name)
                if not nav_link:
                    logger.warning(f"Could not find navigation link for: {section_name}")
                    return
                logger.info(f"Navigating to URL: {nav_link}")
                await self.page.goto(nav_link)
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Capture section state
            screenshot_name = f"section_{self._sanitize_filename(section_name)}"
            await self._capture_screenshot(screenshot_name)
            await self._capture_html(screenshot_name)
            
            # Discover endpoints on this page
            await self._discover_endpoints_on_page(section_name)
            
            # Discover forms on this page
            await self._discover_forms_on_page(section_name)
            
            # Discover data tables
            await self._discover_tables_on_page(section_name)
            
            # Find and explore subsections if depth allows
            if depth > 0:
                subsection_links = await self._find_subsection_links()
                
                for sub_link in subsection_links[:10]:  # Limit to prevent infinite loops
                    try:
                        await self.explore_subsection(
                            section_name, 
                            sub_link['text'], 
                            sub_link['url'],
                            depth - 1
                        )
                    except Exception as e:
                        logger.error(f"Error exploring subsection {sub_link['text']}: {e}")
            
        except Exception as e:
            logger.error(f"Error exploring section {section_name}: {e}")
    
    async def explore_subsection(self, parent_section: str, subsection_name: str, 
                                 url: str, depth: int):
        """Explore a subsection within a main section"""
        logger.info(f"Exploring subsection: {parent_section} > {subsection_name}")
        
        # Prevent revisiting
        if url in self.visited_urls:
            logger.debug(f"Already visited: {url}")
            return
        
        self.visited_urls.add(url)
        
        try:
            await self.page.goto(url)
            await self.page.wait_for_load_state('networkidle')
            
            screenshot_name = f"subsection_{self._sanitize_filename(parent_section)}_{self._sanitize_filename(subsection_name)}"
            await self._capture_screenshot(screenshot_name)
            await self._capture_html(screenshot_name)
            
            # Collect data
            await self._discover_endpoints_on_page(parent_section, subsection_name)
            await self._discover_forms_on_page(parent_section, subsection_name)
            await self._discover_tables_on_page(parent_section, subsection_name)
            
        except Exception as e:
            logger.error(f"Error exploring subsection {subsection_name}: {e}")
    
    async def _discover_endpoints_on_page(self, section: str, subsection: str = ""):
        """Extract all CGI endpoints visible on current page"""
        html_content = await self.page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all links and forms
        links = soup.find_all(['a', 'form'], href=True)
        
        for element in links:
            url = element.get('href') or element.get('action', '')
            
            if '/cgi-bin/' in url:
                # Parse URL and parameters
                full_url = url if url.startswith('http') else f"{self.base_url}{url}"
                
                # Extract parameters from query string
                params = {}
                if '?' in full_url:
                    query_string = full_url.split('?')[1]
                    params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
                
                endpoint = DiscoveredEndpoint(
                    url=full_url.split('?')[0],  # Base URL without params
                    method=element.get('method', 'GET').upper(),
                    parameters=params,
                    section=section,
                    subsection=subsection,
                    purpose=element.get_text(strip=True)[:100] if element.name == 'a' else "Form submission"
                )
                
                # Avoid duplicates
                if not any(e.url == endpoint.url and e.section == endpoint.section 
                          for e in self.discovered_endpoints):
                    self.discovered_endpoints.append(endpoint)
                    logger.debug(f"Discovered endpoint: {endpoint.url}")
    
    async def _discover_forms_on_page(self, section: str, subsection: str = ""):
        """Extract all form structures on current page"""
        html_content = await self.page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        forms = soup.find_all('form')
        
        for idx, form in enumerate(forms):
            form_id = form.get('id') or form.get('name') or f"form_{idx}"
            action = form.get('action', '')
            method = form.get('method', 'GET').upper()
            
            # Extract all input fields
            fields = []
            for input_elem in form.find_all(['input', 'select', 'textarea']):
                field_info = {
                    'name': input_elem.get('name'),
                    'type': input_elem.get('type', 'text'),
                    'id': input_elem.get('id'),
                    'required': input_elem.has_attr('required'),
                    'value': input_elem.get('value'),
                    'placeholder': input_elem.get('placeholder'),
                }
                
                # For select elements, get options
                if input_elem.name == 'select':
                    options = [opt.get('value') for opt in input_elem.find_all('option')]
                    field_info['options'] = options
                
                fields.append(field_info)
            
            discovered_form = DiscoveredForm(
                form_id=form_id,
                action_url=action,
                method=method,
                fields=fields,
                section=section,
                purpose=subsection or "Primary form"
            )
            
            self.discovered_forms.append(discovered_form)
            
            # Save form schema
            schema_file = self.dirs['form_schemas'] / f"{self._sanitize_filename(section)}_{form_id}.json"
            self._save_json(asdict(discovered_form), schema_file)
            
            logger.debug(f"Discovered form: {form_id} with {len(fields)} fields")
    
    async def _discover_tables_on_page(self, section: str, subsection: str = ""):
        """Extract data table structures to understand entities"""
        html_content = await self.page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        tables = soup.find_all('table')
        
        for idx, table in enumerate(tables):
            # Extract headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            if not headers:
                continue
            
            # Try to infer entity name from context
            entity_name = subsection or section
            
            # Create or update entity
            if entity_name not in self.discovered_entities:
                self.discovered_entities[entity_name] = DiscoveredEntity(
                    entity_name=entity_name,
                    discovered_in=[f"{section}/{subsection}"]
                )
            
            entity = self.discovered_entities[entity_name]
            
            # Add fields from headers
            for header in headers:
                if header and not any(f['name'] == header for f in entity.fields):
                    entity.fields.append({
                        'name': header,
                        'type': 'unknown',  # Would need more analysis
                        'source': 'table_header'
                    })
            
            # Save table structure
            table_file = self.dirs['table_structures'] / f"{self._sanitize_filename(section)}_{idx}.json"
            self._save_json({'headers': headers, 'section': section}, table_file)
    
    async def _find_subsection_links(self) -> List[Dict[str, str]]:
        """Find all subsection links on current page"""
        links = []
        
        try:
            # Get all links
            elements = await self.page.query_selector_all('a[href*="/cgi-bin/"]')
            
            for element in elements:
                href = await element.get_attribute('href')
                text = await element.inner_text()
                
                if href and text:
                    links.append({
                        'url': href if href.startswith('http') else f"{self.base_url}{href}",
                        'text': text.strip()
                    })
        except Exception as e:
            logger.error(f"Error finding subsection links: {e}")
        
        return links
    
    def _find_nav_link(self, section_name: str) -> Optional[str]:
        """Find the URL for a specific section from navigation tree"""
        for node in self.navigation_tree:
            if section_name.lower() in node.label.lower():
                return node.url
        return None
    
    async def _capture_screenshot(self, name: str):
        """Capture screenshot of current page"""
        try:
            filepath = self.dirs['screenshots'] / f"{name}.png"
            await self.page.screenshot(path=str(filepath), full_page=True)
            logger.debug(f"Screenshot saved: {filepath}")
        except Exception as e:
            logger.error(f"Error capturing screenshot {name}: {e}")
    
    async def _capture_html(self, name: str):
        """Capture HTML content of current page"""
        try:
            html_content = await self.page.content()
            filepath = self.dirs['html_captures'] / f"{name}.html"
            filepath.write_text(html_content, encoding='utf-8')
            logger.debug(f"HTML saved: {filepath}")
        except Exception as e:
            logger.error(f"Error capturing HTML {name}: {e}")
    
    def _sanitize_filename(self, name: str) -> str:
        """Convert name to safe filename"""
        return "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name).lower()
    
    def _save_json(self, data: Any, filepath: Path):
        """Save data as JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving JSON to {filepath}: {e}")
    
    async def run_full_discovery(self, username: str, password: str):
        """
        Execute complete system discovery
        
        This is the main orchestration method that runs all discovery phases
        """
        start_time = datetime.now()
        logger.info(f"Starting full discovery at {start_time}")
        
        try:
            # Initialize
            await self.initialize_browser()
            
            # Login
            if not await self.login(username, password):
                logger.error("Login failed, cannot proceed")
                return
            
            # Phase 1: Discover navigation
            await self.discover_navigation_structure()
            
            # Phase 2: Explore all main sections
            for section in self.main_sections:
                try:
                    await self.explore_section(section, depth=2)
                    await asyncio.sleep(1)  # Brief pause between sections
                except Exception as e:
                    logger.error(f"Error exploring section {section}: {e}")
                    continue
            
            # Phase 3: Save all discovery data
            await self.save_discovery_results()
            
            # Phase 4: Generate reports
            await self.generate_reports()
            
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"Discovery completed in {duration}")
            logger.info(f"Discovered {len(self.discovered_endpoints)} endpoints")
            logger.info(f"Discovered {len(self.discovered_forms)} forms")
            logger.info(f"Discovered {len(self.discovered_entities)} entities")
            
        except Exception as e:
            logger.error(f"Fatal error during discovery: {e}")
            raise
        finally:
            if self.browser:
                await self.browser.close()
    
    async def save_discovery_results(self):
        """Save all collected discovery data"""
        logger.info("Saving discovery results")
        
        # Save master discovery file
        discovery_data = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'endpoints': [asdict(e) for e in self.discovered_endpoints],
            'forms': [asdict(f) for f in self.discovered_forms],
            'entities': {k: asdict(v) for k, v in self.discovered_entities.items()},
            'navigation': [asdict(n) for n in self.navigation_tree],
            'statistics': {
                'total_endpoints': len(self.discovered_endpoints),
                'total_forms': len(self.discovered_forms),
                'total_entities': len(self.discovered_entities),
                'urls_visited': len(self.visited_urls)
            }
        }
        
        filepath = self.output_dir / 'discovery_data' / 'raw_discovery.json'
        self._save_json(discovery_data, filepath)
        
        logger.info(f"Discovery data saved to {filepath}")
    
    async def generate_reports(self):
        """Generate all documentation reports"""
        logger.info("Generating documentation reports")
        
        # This will be implemented by specialized generator classes
        # For now, create placeholder files
        
        reports = [
            'EXECUTIVE_SUMMARY.md',
            'TECHNICAL_ARCHITECTURE.md',
            'API_FEASIBILITY_REPORT.md',
            'BUSINESS_PROCESS_FLOWS.md',
            'AUTOMATION_ROADMAP.md',
            'MODERNIZATION_STRATEGY.md'
        ]
        
        for report in reports:
            filepath = self.output_dir / report
            if not filepath.exists():
                filepath.write_text(f"# {report.replace('.md', '').replace('_', ' ')}\n\n*To be generated from discovery data*\n")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='KeyedIn Architecture Discovery')
    parser.add_argument('--base-url', required=True, help='KeyedIn base URL')
    parser.add_argument('--username', required=True, help='Login username')
    parser.add_argument('--password', required=True, help='Login password')
    parser.add_argument('--output-dir', default='KeyedIn_System_Map', help='Output directory')
    parser.add_argument('--section', help='Explore specific section only')
    
    args = parser.parse_args()
    
    mapper = KeyedInArchitectureMapper(args.base_url, args.output_dir)
    
    if args.section:
        # Single section mode
        await mapper.initialize_browser()
        if await mapper.login(args.username, args.password):
            await mapper.explore_section(args.section, depth=2)
            await mapper.save_discovery_results()
    else:
        # Full discovery mode
        await mapper.run_full_discovery(args.username, args.password)


if __name__ == '__main__':
    asyncio.run(main())
