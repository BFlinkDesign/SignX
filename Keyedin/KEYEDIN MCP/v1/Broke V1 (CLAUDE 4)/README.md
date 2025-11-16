# KeyedIn Resilient Agent - Complete Deployment Guide

## 🎯 Quick Start (5 Minutes)

```powershell
# 1. Save Deploy-KeyedInAgent.ps1 and run as Administrator
# (Installs to C:\Scripts\MCP\KEYEDIN\v1 by default)
powershell -ExecutionPolicy Bypass -File Deploy-KeyedInAgent.ps1

# 2. Edit credentials
notepad C:\Scripts\MCP\KEYEDIN\v1\.env

# 3. Start Chrome with debugging
C:\Scripts\MCP\KEYEDIN\v1\start_chrome_debug.bat

# 4. Test the agent
C:\Scripts\MCP\KEYEDIN\v1\run_once.bat

# 5. Deploy as service
C:\Scripts\MCP\KEYEDIN\v1\run_agent.bat
```

## 📋 What You Get

### Core Components
- **🤖 Resilient Agent** - Persistent KeyedIn automation with Chrome integration
- **🔄 Background Service** - Runs invisibly, starts at login, auto-recovers
- **⚡ MCP Server** - Fast Claude integration for sub-second responses
- **📊 Data Extraction** - Tables, forms, search, export capabilities
- **🔐 Session Management** - Never logs out, handles timeouts gracefully

### Key Features
✅ **Chrome Password Manager** - Reuses your saved credentials  
✅ **Session Persistence** - Stays logged in between runs  
✅ **Auto Recovery** - Handles lockouts, session expiry, crashes  
✅ **Intelligent Login** - Detects "Welcome" and "Logout" signals accurately  
✅ **Rate Limiting** - Prevents "too many attempts" errors  
✅ **Comprehensive Logging** - Full audit trail with timestamps  
✅ **Task Scheduler** - Windows service integration  
✅ **Claude Integration** - MCP server for instant data access  

## 🚀 Deployment Steps

### Step 1: Run the Deployment Script

Save all the artifacts above to a folder, then run:

```powershell
# As Administrator
powershell -ExecutionPolicy Bypass -File Deploy-KeyedInAgent.ps1
```

**Instructions:**
```powershell
# Custom install path
Deploy-KeyedInAgent.ps1 -InstallPath "D:\MyAgents\KeyedIn"

# Pre-configure credentials
Deploy-KeyedInAgent.ps1 -Username "YourUser" -Password "YourPass"

# Skip Task Scheduler setup
Deploy-KeyedInAgent.ps1 -NoTaskScheduler

# Skip Chrome integration
Deploy-KeyedInAgent.ps1 -NoChrome
```

### Step 2: Configure Credentials

Edit `C:\Scripts\MCP\KEYEDIN\v1\.env`:

```bash
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
```

**Or leave blank to use Chrome's saved passwords!**

### Step 3: Enable Chrome Integration (Recommended)

```batch
# Close Chrome, then run:
C:\Scripts\MCP\KEYEDIN\v1\start_chrome_debug.bat
```

This starts Chrome with debugging enabled so the agent can reuse your existing session.

### Step 4: Test Everything

```batch
# Test run (visible browser)
C:\Scripts\MCP\KEYEDIN\v1\run_once.bat
```

Look for:
- ✅ Chrome connection successful
- ✅ Login detection working  
- ✅ Session saved
- ✅ Projects page accessible

### Step 5: Deploy as Service

```batch
# Background service (invisible)
C:\Scripts\MCP\KEYEDIN\v1\run_agent.bat
```

**Or use Task Scheduler:**
```batch
# Start the scheduled task
schtasks /Run /TN "\KeyedIn\ResilientAgent"

# Check status
schtasks /Query /TN "\KeyedIn\ResilientAgent" /V
```

## 🔧 Configuration Options

### Environment Variables (.env file)

```bash
# === REQUIRED ===
KEYEDIN_BASE_URL=http://eaglesign.keyedinsign.com
KEYEDIN_USERNAME=          # Leave blank for Chrome autofill
KEYEDIN_PASSWORD=          # Leave blank for Chrome autofill

# === BROWSER ===
HEADLESS=true              # false for development
CDP_PORT=9222              # Chrome debug port
DEFAULT_TIMEOUT_MS=15000   # Page operation timeout

# === SESSION ===
STORAGE_STATE=keyedin_session.json
MAX_SESSION_AGE_HOURS=24
SESSION_CHECK_INTERVAL=1800

# === LOGIN ===
LOGIN_BACKOFF_SECONDS=45   # Wait after failed login
MAX_LOGIN_RETRIES=2        # Max attempts before giving up

# === SERVICE ===
SERVICE_INTERVAL=300       # Health check every 5 minutes
LOG_LEVEL=INFO            # DEBUG for troubleshooting
```

### Chrome Profile Configuration

```bash
# Use specific Chrome profile
CHROME_PROFILE=Profile 1   # Default = "Default"
USE_CHROME_PROFILE=true    # Enable profile reuse
```

### Development Mode

```bash
# Development settings
HEADLESS=false
DEBUG_MODE=true
SERVICE_INTERVAL=60
LOG_LEVEL=DEBUG
SAVE_ERROR_SCREENSHOTS=true
```

## 🔌 Claude Integration (MCP Server)

### Setup MCP Server

```bash
# Install MCP package
pip install mcp

# Run MCP server
python keyedin_mcp_server.py
```

### Add to Claude Desktop

Edit your Claude Desktop config:

```json
{
  "mcpServers": {
    "keyedin-connector": {
      "command": "python",
      "args": ["C:\\Scripts\\MCP\\KEYEDIN\\v1\\keyedin_mcp_server.py"],
      "cwd": "C:\\Scripts\\MCP\\KEYEDIN\\v1"
    }
  }
}
```

### Available Tools for Claude

```
keyedin_status          - Check agent connectivity
keyedin_login           - Ensure logged in
keyedin_navigate        - Go to projects/costs/customers
keyedin_extract_table   - Get table data
keyedin_search_page     - Find text on page
keyedin_get_projects    - List all projects
keyedin_get_costs       - Extract cost data
keyedin_click_element   - Click buttons/links
keyedin_fill_form       - Fill out forms
keyedin_export_data     - Export to CSV/JSON/Excel
```

## 📊 Usage Examples

### Basic Agent Operations

```python
# Check if agent is healthy
python keyedin_resilient_agent.py --run-once

# Run as background service
python keyedin_resilient_agent.py --service

# Clear saved session
python keyedin_resilient_agent.py --clear-session

# Run self-test
python keyedin_resilient_agent.py --selftest
```

### Claude Integration Examples

```
# Ask Claude:
"Check KeyedIn status"
→ Uses keyedin_status tool

"Get me a list of all active projects"  
→ Uses keyedin_get_projects tool

"Export the current cost data to Excel"
→ Uses keyedin_export_data tool

"Navigate to the CRM module"
→ Uses keyedin_navigate tool with module="crm"
```

## 🔍 Troubleshooting

### Common Issues

**🔴 Agent won't start**
```bash
# Check logs
type C:\Scripts\MCP\KEYEDIN\v1\logs\*.log

# Reinstall dependencies  
C:\Scripts\MCP\KEYEDIN\v1\setup.bat

# Verify Python
python --version
```

**🔴 Login failures**
```bash
# Check credentials
notepad C:\Scripts\MCP\KEYEDIN\v1\.env

# Clear saved session
python keyedin_resilient_agent.py --clear-session

# Test Chrome integration
C:\Scripts\MCP\KEYEDIN\v1\start_chrome_debug.bat
```

**🔴 "Too many attempts"**
```bash
# Wait 30 minutes, then:
python keyedin_resilient_agent.py --clear-session

# Check lockout in logs
findstr "lockout\|attempts" C:\Scripts\MCP\KEYEDIN\v1\logs\*.log
```

**🔴 Chrome connection issues**
```bash
# Verify Chrome debug port
netstat -an | findstr 9222

# Restart Chrome with debugging
taskkill /F /IM chrome.exe
C:\Scripts\MCP\KEYEDIN\v1\start_chrome_debug.bat
```

### Log Analysis

```bash
# View recent errors
findstr /C:"ERROR" C:\Scripts\MCP\KEYEDIN\v1\logs\*.log

# Check login attempts  
findstr /C:"Login" C:\Scripts\MCP\KEYEDIN\v1\logs\*.log

# Monitor health checks
findstr /C:"Health" C:\Scripts\MCP\KEYEDIN\v1\logs\*.log
```

### Service Management

```bash
# Check service status
schtasks /Query /TN "\KeyedIn\ResilientAgent" /FO LIST

# Stop service
C:\Scripts\MCP\KEYEDIN\v1\stop_agent.bat

# Restart service
schtasks /End /TN "\KeyedIn\ResilientAgent"
schtasks /Run /TN "\KeyedIn\ResilientAgent"

# View service logs
type C:\Scripts\MCP\KEYEDIN\v1\logs\agent_*.log
```

## 🎛️ Advanced Configuration

### Example Configurations

```bash
# Production
copy .env .env.prod
# Edit .env.prod with production settings

# Development  
copy .env .env.dev
# Edit .env.dev with debug settings

# Run with specific config
set KEYEDIN_ENV=prod
cd C:\Scripts\MCP\KEYEDIN\v1
python keyedin_resilient_agent.py --service
```

### Custom Chrome Profiles

```bash
# Use different Chrome profile
CHROME_PROFILE=Work Profile
CHROME_USER_DATA=C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data
```

### Network Configuration

```bash
# Proxy settings
BROWSER_ARGS=--proxy-server=proxy.company.com:8080

# Custom timeout
DEFAULT_TIMEOUT_MS=30000
NETWORK_TIMEOUT=60
```

### Performance Tuning

```bash
# Faster performance (headless)
HEADLESS=true
DISABLE_IMAGES=true
SERVICE_INTERVAL=600

# Development (visible)
HEADLESS=false
DEBUG_SLOWMO=1000
SAVE_ERROR_SCREENSHOTS=true
```

## 📈 Monitoring & Maintenance

### Health Monitoring

The agent automatically:
- Checks login status every 5 minutes
- Restarts on crashes (3 attempts)
- Logs all operations with timestamps
- Saves error screenshots when enabled

### Log Rotation

```bash
# Clean old logs (optional)
forfiles /p C:\Scripts\MCP\KEYEDIN\v1\logs /s /m *.log /d -30 /c "cmd /c del @path"
```

### Performance Metrics

Monitor these log entries:
- `Login successful` - Authentication working
- `Health check passed` - System stable  
- `Navigation failed` - UI changes detected
- `Session expired` - Automatic recovery triggered

## 🔒 Security Notes

### Credential Security
- Store credentials in `.env` file (not source code)
- Use Chrome password manager when possible
- Consider Windows Credential Manager integration

### Network Security
- Agent connects only to your KeyedIn server
- No external data transmission except to KeyedIn
- All session data stored locally

### Access Control
- Agent runs with your user privileges
- Lockfile prevents multiple instances
- Task Scheduler restricts to logged-in user

## 🆘 Support & Debugging

### Enable Debug Mode

```bash
# .env file
DEBUG_MODE=true
LOG_LEVEL=DEBUG
HEADLESS=false
SAVE_ERROR_SCREENSHOTS=true

# Run with verbose output
python keyedin_resilient_agent.py --run-once
```

### Collect Debug Information

```bash
# System info
systeminfo | findstr /C:"OS Name" /C:"OS Version"
python --version
where chrome

# Agent status
python keyedin_resilient_agent.py --selftest

# Network connectivity
ping eaglesign.keyedinsign.com
telnet eaglesign.keyedinsign.com 80
```

### Submit Bug Report

Include these files:
- Latest log file from `logs/`
- Screenshot from `screenshots/` (if enabled)  
- Your `.env` file (**remove passwords first**)
- Output from `--selftest`

---

## 🎉 Success!

Your KeyedIn agent is now:
✅ **Always connected** - Persistent session, never logs out  
✅ **Self-healing** - Automatic recovery from errors  
✅ **Fast & reliable** - Sub-second responses via MCP  
✅ **Invisible** - Runs in background, starts at login  
✅ **Secure** - Uses your Chrome passwords, local storage only  

**Next Steps:**
- Connect Claude to your MCP server
- Build custom workflows
- Set up data export schedules
- Monitor logs for optimization opportunities

Happy automating! 🚀