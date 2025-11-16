#!/bin/bash
# Eagle MCP Quick Setup Script

echo "🦅 Eagle Sign MCP Setup"
echo "======================="

# 1. Create project directory
mkdir -p C:/EagleAutomation
cd C:/EagleAutomation

# 2. Install dependencies
echo "Installing dependencies..."
pip install playwright python-dotenv beautifulsoup4 mcp

# 3. Install Playwright browsers
echo "Installing Chromium..."
playwright install chromium

# 4. Create .env file
echo "Creating .env file..."
cat > .env << EOF
# KeyedIn Credentials
KEYEDIN_USERNAME=your_username_here
KEYEDIN_PASSWORD=your_password_here
EOF

# 5. Copy MCP server
echo "Setting up MCP server..."
# Copy your keyedin_mcp_server_secure.py here

# 6. Create test script
cat > test_keyedin.py << 'EOF'
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def quick_test():
    print("Testing KeyedIn connection...")
    print(f"Username from env: {os.getenv('KEYEDIN_USERNAME')}")
    print("Ready to test MCP server")
    
    # Add actual MCP test here
    
asyncio.run(quick_test())
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your KeyedIn credentials"
echo "2. Copy keyedin_mcp_server_secure.py to this directory"
echo "3. Run: python test_keyedin.py"
