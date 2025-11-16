#!/usr/bin/env python3
"""
KeyedIn MCP Server - Secure Version with .env Support
Complete access to KeyedIn Manufacturing
"""

import os
import json
import logging
import sys
from typing import Any, Dict, List, Optional
import asyncio
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_transport
from mcp.types import Tool, TextContent, ImageContent
from playwright.async_api import async_playwright, Page
import base64

# Load environment variables
load_dotenv()

# Configure logging to stderr for MCP
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("keyedin-mcp")

class KeyedInClient:
    def __init__(self):
        self.browser = None
        self.page = None
        self.logged_in = False
        self.base_url = "http://eaglesign.keyedinsign.com"
        self.current_section = "Main Menu"
        
        # Main menu sections discovered from diagnostics
        self.main_sections = [
            "CRM", "Project Management", "Estimating and Proposals",
            "Sales Order Entry", "Shipping Tracking", "Sales Analysis",
            "Purchasing", "Inventory and Parts", "Job Cost",
            "Material Requirements Planning", "Production (Shop Floor Control)",
            "Resource Scheduling", "Labor and Payroll Processing",
            "Accounts Payable", "Accounts Receivable",
            "Report Administration", "Administration", "System Management"
        ]
        
    async def initialize(self):
        """Initialize browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        
    async def login(self, username: str = None, password: str = None) -> Dict[str, Any]:
        """Login to KeyedIn - uses .env if credentials not provided"""
        try:
            # Use environment variables if not provided
            if not username:
                username = os.getenv('KEYEDIN_USERNAME')
                if not username:
                    return {"success": False, "error": "No username provided and KEYEDIN_USERNAME not set"}
                    
            if not password:
                password = os.getenv('KEYEDIN_PASSWORD')
                if not password:
                    return {"success": False, "error": "No password provided and KEYEDIN_PASSWORD not set"}
                    
            logger.info(f"Logging in as {username} (from {'env' if not username else 'args'})")
            
            # Navigate to login page
            await self.page.goto(f"{self.base_url}/cgi-bin/mvi.exe/LOGIN.START")
            await self.page.wait_for_load_state('networkidle')
            
            # Fill credentials
            await self.page.fill('#USERNAME', username)
            await self.page.fill('#PASSWORD', password)
            
            # Click login button
            await self.page.click('#btnLogin')
            await self.page.wait_for_timeout(3000)
            
            # Check for successful login by looking for Welcome message
            page_text = await self.page.evaluate('() => document.body.innerText')
            
            if 'Welcome,' in page_text and username.upper() in page_text.upper():
                self.logged_in = True
                logger.info("Login successful!")
                
                # Extract user's full name
                import re
                match = re.search(r'Welcome,\s+([^|]+)', page_text)
                full_name = match.group(1).strip() if match else username
                
                return {
                    "success": True,
                    "message": f"Successfully logged in as {full_name}",
                    "available_sections": self.main_sections
                }
            elif 'LICENSE QUOTA' in page_text:
                return {
                    "success": False,
                    "error": "License quota exceeded - too many users logged in"
                }
            else:
                return {
                    "success": False,
                    "error": "Login failed - check credentials"
                }
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def navigate_to_section(self, section_name: str) -> Dict[str, Any]:
        """Navigate to a specific section by clicking its link"""
        if not self.logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Try to click the section link
            clicked = False
            
            # Try exact text match first
            try:
                await self.page.click(f'a:has-text("{section_name}")', timeout=5000)
                clicked = True
            except:
                # Try partial match
                links = await self.page.query_selector_all('a')
                for link in links:
                    text = await link.text_content()
                    if text and section_name.lower() in text.lower():
                        await link.click()
                        clicked = True
                        break
                        
            if clicked:
                await self.page.wait_for_load_state('networkidle')
                self.current_section = section_name
                
                return {
                    "success": True,
                    "section": section_name,
                    "message": f"Navigated to {section_name}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not find section: {section_name}",
                    "available": self.main_sections
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def get_page_data(self) -> Dict[str, Any]:
        """Extract all data from current page"""
        if not self.logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Get page info
            title = await self.page.title()
            url = self.page.url
            
            # Extract tables
            tables = await self.page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                const results = [];
                
                tables.forEach((table, idx) => {
                    const data = [];
                    const headers = [];
                    
                    // Get headers
                    table.querySelectorAll('th').forEach(th => {
                        headers.push(th.textContent.trim());
                    });
                    
                    // Get rows
                    table.querySelectorAll('tr').forEach(tr => {
                        const row = [];
                        tr.querySelectorAll('td').forEach(td => {
                            row.push(td.textContent.trim());
                        });
                        if (row.length > 0) data.push(row);
                    });
                    
                    if (data.length > 0 || headers.length > 0) {
                        results.push({
                            index: idx,
                            headers: headers,
                            rows: data,
                            rowCount: data.length
                        });
                    }
                });
                
                return results;
            }''')
            
            # Extract forms
            forms = await self.page.evaluate('''() => {
                const forms = document.querySelectorAll('form');
                const results = [];
                
                forms.forEach((form, idx) => {
                    const fields = [];
                    
                    form.querySelectorAll('input, select, textarea').forEach(field => {
                        fields.push({
                            type: field.type || field.tagName.toLowerCase(),
                            name: field.name,
                            id: field.id,
                            value: field.value
                        });
                    });
                    
                    results.push({
                        index: idx,
                        action: form.action,
                        method: form.method,
                        fields: fields
                    });
                });
                
                return results;
            }''')
            
            # Extract links
            links = await self.page.evaluate('''() => {
                const links = document.querySelectorAll('a[href]');
                const results = [];
                
                links.forEach(link => {
                    const text = link.textContent.trim();
                    if (text) {
                        results.push({
                            text: text,
                            href: link.href
                        });
                    }
                });
                
                return results;
            }''')
            
            # Get page text
            page_text = await self.page.evaluate('() => document.body.innerText')
            
            return {
                "success": True,
                "current_section": self.current_section,
                "title": title,
                "url": url,
                "tables": tables,
                "forms": forms,
                "link_count": len(links),
                "sample_links": links[:10],
                "text_preview": page_text[:500] + "..." if len(page_text) > 500 else page_text
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def fill_form(self, form_data: Dict[str, str]) -> Dict[str, Any]:
        """Fill and submit a form"""
        if not self.logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Fill each field
            for field_name, value in form_data.items():
                # Try different selectors
                filled = False
                for selector in [f'[name="{field_name}"]', f'#{field_name}']:
                    try:
                        await self.page.fill(selector, str(value))
                        filled = True
                        break
                    except:
                        continue
                        
                if not filled:
                    logger.warning(f"Could not fill field: {field_name}")
                    
            # Try to submit
            # Look for submit button
            submit_clicked = False
            for selector in ['input[type="submit"]', 'button[type="submit"]', 
                           'input[type="button"][value*="Submit"]', 
                           'button:has-text("Submit")']:
                try:
                    await self.page.click(selector)
                    submit_clicked = True
                    break
                except:
                    continue
                    
            if submit_clicked:
                await self.page.wait_for_load_state('networkidle')
                return {
                    "success": True,
                    "message": "Form submitted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Could not find submit button"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def search(self, query: str) -> Dict[str, Any]:
        """Search within current page"""
        if not self.logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            page_text = await self.page.evaluate('() => document.body.innerText')
            lines = page_text.split('\n')
            
            matches = []
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    # Get context
                    start = max(0, i-1)
                    end = min(len(lines), i+2)
                    context = '\n'.join(lines[start:end])
                    
                    matches.append({
                        "line": i,
                        "text": line,
                        "context": context
                    })
                    
            return {
                "success": True,
                "query": query,
                "matches": len(matches),
                "results": matches[:10]  # First 10 matches
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def screenshot(self, full_page: bool = False) -> str:
        """Take a screenshot and return base64 encoded image"""
        if not self.logged_in:
            raise Exception("Not logged in")
            
        screenshot = await self.page.screenshot(full_page=full_page)
        return base64.b64encode(screenshot).decode()
        
    async def cleanup(self):
        """Cleanup browser resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Global client instance
client = None

async def get_client():
    """Get or create client"""
    global client
    if not client:
        client = KeyedInClient()
        await client.initialize()
    return client

# Create MCP server
server = Server("keyedin")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="login",
            description="Login to KeyedIn Manufacturing system (uses .env if no credentials provided)",
            input_schema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "KeyedIn username (optional if in .env)"},
                    "password": {"type": "string", "description": "KeyedIn password (optional if in .env)"}
                },
                "required": []
            }
        ),
        Tool(
            name="navigate",
            description="Navigate to a section (e.g., CRM, Project Management, Sales Order Entry)",
            input_schema={
                "type": "object",
                "properties": {
                    "section": {"type": "string", "description": "Section name to navigate to"}
                },
                "required": ["section"]
            }
        ),
        Tool(
            name="get_data",
            description="Get all data from current page (tables, forms, links)",
            input_schema={"type": "object", "properties": {}}
        ),
        Tool(
            name="fill_form",
            description="Fill and submit a form on current page",
            input_schema={
                "type": "object",
                "properties": {
                    "form_data": {
                        "type": "object",
                        "description": "Field names and values to fill"
                    }
                },
                "required": ["form_data"]
            }
        ),
        Tool(
            name="search",
            description="Search for text in current page",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="screenshot",
            description="Take a screenshot of current page",
            input_schema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture full page", "default": False}
                }
            }
        ),
        Tool(
            name="list_sections",
            description="List all available main sections",
            input_schema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list:
    """Execute tool calls"""
    
    try:
        client = await get_client()
        
        if name == "login":
            result = await client.login(
                arguments.get("username"),
                arguments.get("password")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "navigate":
            result = await client.navigate_to_section(arguments["section"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_data":
            result = await client.get_page_data()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "fill_form":
            result = await client.fill_form(arguments["form_data"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "search":
            result = await client.search(arguments["query"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "screenshot":
            image_data = await client.screenshot(arguments.get("full_page", False))
            return [ImageContent(type="image", data=image_data, mime_type="image/png")]
            
        elif name == "list_sections":
            if not client.logged_in:
                return [TextContent(type="text", text="Error: Not logged in")]
            sections = "\n".join(f"- {s}" for s in client.main_sections)
            return [TextContent(type="text", text=f"Available sections:\n{sections}")]
            
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        logger.error(f"Tool error: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def cleanup():
    """Cleanup on shutdown"""
    global client
    if client:
        await client.cleanup()

async def main():
    """Main entry point"""
    try:
        logger.info("KeyedIn MCP Server starting...")
        
        # Run with stdio transport
        async with stdio_transport() as (read_stream, write_stream):
            initialization_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, initialization_options)
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())