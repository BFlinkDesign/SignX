# Deploy-KeyedInAgent.ps1
# Complete deployment script for KeyedIn Resilient Agent
# Run as: powershell -ExecutionPolicy Bypass -File Deploy-KeyedInAgent.ps1

param(
    [string]$InstallPath = "C:\KeyedInAgent",
    [string]$Username = "",
    [string]$Password = "",
    [switch]$NoTaskScheduler,
    [switch]$NoChrome
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 KeyedIn Resilient Agent Deployment" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "⚠️  This script requires Administrator privileges" -ForegroundColor Yellow
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

# Create directory structure
Write-Host "📁 Creating directory structure..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallPath\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallPath\config" | Out-Null

# Create .env configuration file
Write-Host "⚙️  Creating configuration..." -ForegroundColor Green
$EnvContent = @"
# KeyedIn Agent Configuration
KEYEDIN_BASE_URL=http://eaglesign.keyedinsign.com
KEYEDIN_USERNAME=$Username
KEYEDIN_PASSWORD=$Password
HEADLESS=true
DEFAULT_TIMEOUT_MS=15000
STORAGE_STATE=keyedin_session.json
LOCKFILE=.keyedin_lock
LOGIN_BACKOFF_SECONDS=45
MAX_LOGIN_RETRIES=2
SERVICE_INTERVAL=300
CDP_PORT=9222
"@

$EnvContent | Out-File -FilePath "$InstallPath\.env" -Encoding UTF8

# Create run_agent.bat
Write-Host "📝 Creating batch files..." -ForegroundColor Green
$RunAgentBat = @'
@echo off
setlocal
set SCRIPT_DIR=%~dp0
set LOGDIR=%SCRIPT_DIR%logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM Create timestamped log file
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do if not "%%I"=="" set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set LOG=%LOGDIR%\agent_%TIMESTAMP%.log

REM Find Python executable
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYEXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    for %%i in (python.exe) do set "PYEXE=%%~$PATH:i"
    if "!PYEXE!"=="" (
        echo ERROR: Python not found in PATH or virtual environment
        echo Please install Python or run setup.bat first
        pause
        exit /b 1
    )
)

echo Starting KeyedIn Agent Service...
echo Python: %PYEXE%
echo Log: %LOG%
echo.

REM Run agent in service mode with CDP (Chrome debugging)
"%PYEXE%" "%SCRIPT_DIR%keyedin_resilient_agent.py" --service --headless --cdp-port 9222 --interval 300 >> "%LOG%" 2>&1

if %ERRORLEVEL% neq 0 (
    echo Agent exited with error code %ERRORLEVEL%
    echo Check log file: %LOG%
    pause
)
'@

$RunAgentBat | Out-File -FilePath "$InstallPath\run_agent.bat" -Encoding ASCII

# Create run_once.bat for testing
$RunOnceBat = @'
@echo off
setlocal
set SCRIPT_DIR=%~dp0

REM Find Python executable
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYEXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    for %%i in (python.exe) do set "PYEXE=%%~$PATH:i"
    if "!PYEXE!"=="" (
        echo ERROR: Python not found
        pause
        exit /b 1
    )
)

echo Testing KeyedIn Agent...
echo.

REM Run agent once for testing
"%PYEXE%" "%SCRIPT_DIR%keyedin_resilient_agent.py" --run-once --cdp-port 9222

echo.
echo Test completed. Press any key to continue...
pause > nul
'@

$RunOnceBat | Out-File -FilePath "$InstallPath\run_once.bat" -Encoding ASCII

# Create setup.bat for Python environment
$SetupBat = @'
@echo off
setlocal
set SCRIPT_DIR=%~dp0

echo Setting up Python environment for KeyedIn Agent...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv "%SCRIPT_DIR%.venv"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
"%SCRIPT_DIR%.venv\Scripts\pip" install --upgrade pip
"%SCRIPT_DIR%.venv\Scripts\pip" install playwright python-dotenv aiohttp
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install Python packages
    pause
    exit /b 1
)

REM Install Playwright browsers
echo Installing Playwright browsers...
"%SCRIPT_DIR%.venv\Scripts\python" -m playwright install chromium
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install Playwright browsers
    pause
    exit /b 1
)

echo.
echo ✅ Setup completed successfully!
echo You can now run the agent with run_once.bat or run_agent.bat
pause
'@

$SetupBat | Out-File -FilePath "$InstallPath\setup.bat" -Encoding ASCII

if (-not $NoChrome) {
    # Create Chrome debug starter
    $ChromeDebugBat = @'
@echo off
echo Starting Chrome with debugging enabled on port 9222...
echo.

REM Kill any existing Chrome processes
taskkill /F /IM chrome.exe /T >nul 2>&1

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start Chrome with debugging
set CHROME_PATH=%PROGRAMFILES%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME_PATH%" (
    set CHROME_PATH=%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe
)
if not exist "%CHROME_PATH%" (
    set CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
)

if exist "%CHROME_PATH%" (
    echo Starting Chrome from: %CHROME_PATH%
    start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" --profile-directory="Default"
    echo.
    echo ✅ Chrome started with debugging enabled
    echo The agent can now connect to Chrome on port 9222
) else (
    echo ❌ Chrome not found in standard locations
    echo Please install Chrome or update the path in this script
)

echo.
pause
'@

    $ChromeDebugBat | Out-File -FilePath "$InstallPath\start_chrome_debug.bat" -Encoding ASCII
}

# Create stop_agent.bat
$StopAgentBat = @'
@echo off
echo Stopping KeyedIn Agent...

REM Stop scheduled task if it exists
schtasks /End /TN "\KeyedIn\ResilientAgent" >nul 2>&1

REM Kill any running Python processes with our script
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr keyedin_resilient_agent') do (
    echo Stopping agent process %%i
    taskkill /F /PID %%i
)

echo Agent stopped.
pause
'@

$StopAgentBat | Out-File -FilePath "$InstallPath\stop_agent.bat" -Encoding ASCII

# Install Python dependencies
Write-Host "🐍 Setting up Python environment..." -ForegroundColor Green
Set-Location $InstallPath

try {
    # Try to create virtual environment
    $pythonExe = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonExe) {
        Write-Host "Creating virtual environment..."
        & python -m venv .venv
        
        if (Test-Path ".venv\Scripts\pip.exe") {
            Write-Host "Installing dependencies..."
            & .\.venv\Scripts\pip install --upgrade pip --quiet
            & .\.venv\Scripts\pip install playwright python-dotenv aiohttp --quiet
            & .\.venv\Scripts\python -m playwright install chromium --quiet
            Write-Host "✅ Virtual environment created successfully" -ForegroundColor Green
        } else {
            throw "Failed to create virtual environment"
        }
    } else {
        Write-Host "⚠️  Python not found in PATH" -ForegroundColor Yellow
        Write-Host "Please install Python and run setup.bat manually" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Failed to setup Python environment: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Please run setup.bat manually after deployment" -ForegroundColor Yellow
}

if (-not $NoTaskScheduler) {
    # Create Task Scheduler XML
    Write-Host "📅 Creating Task Scheduler job..." -ForegroundColor Green
    $TaskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.6" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
    <RegistrationInfo>
        <Description>KeyedIn Resilient Agent - Maintains persistent session and monitors system health</Description>
        <URI>\KeyedIn\ResilientAgent</URI>
    </RegistrationInfo>
    <Triggers>
        <LogonTrigger>
            <Enabled>true</Enabled>
            <Delay>PT1M</Delay>
        </LogonTrigger>
    </Triggers>
    <Principals>
        <Principal id="Author">
            <LogonType>InteractiveToken</LogonType>
            <RunLevel>HighestAvailable</RunLevel>
        </Principal>
    </Principals>
    <Settings>
        <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
        <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
        <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
        <AllowHardTerminate>true</AllowHardTerminate>
        <StartWhenAvailable>true</StartWhenAvailable>
        <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
        <AllowStartOnDemand>true</AllowStartOnDemand>
        <Enabled>true</Enabled>
        <Hidden>false</Hidden>
        <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
        <Priority>7</Priority>
        <RestartOnFailure>
            <Interval>PT5M</Interval>
            <Count>3</Count>
        </RestartOnFailure>
    </Settings>
    <Actions Context="Author">
        <Exec>
            <Command>$InstallPath\run_agent.bat</Command>
            <WorkingDirectory>$InstallPath</WorkingDirectory>
        </Exec>
    </Actions>
</Task>
"@

    $TaskXml | Out-File -FilePath "$InstallPath\KeyedInAgent.task.xml" -Encoding UTF8

    # Register the task
    try {
        schtasks /Create /TN "\KeyedIn\ResilientAgent" /XML "$InstallPath\KeyedInAgent.task.xml" /F | Out-Null
        Write-Host "✅ Task Scheduler job created" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Failed to create Task Scheduler job: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "You can import $InstallPath\KeyedInAgent.task.xml manually" -ForegroundColor Yellow
    }
}

# Create README
Write-Host "📖 Creating documentation..." -ForegroundColor Green
$ReadmeContent = @"
# KeyedIn Resilient Agent

## Quick Start

1. **First Time Setup**
   - Run `setup.bat` to install Python dependencies
   - Edit `.env` file with your KeyedIn credentials
   - Test with `run_once.bat`

2. **Chrome Integration (Recommended)**
   - Run `start_chrome_debug.bat` to enable Chrome debugging
   - This allows the agent to reuse your existing Chrome session

3. **Running the Agent**
   - `run_once.bat` - Test run (interactive)
   - `run_agent.bat` - Background service
   - `stop_agent.bat` - Stop the service

## Files

- `keyedin_resilient_agent.py` - Main agent script
- `.env` - Configuration file (edit with your credentials)
- `setup.bat` - Install Python dependencies
- `run_once.bat` - Test the agent
- `run_agent.bat` - Run as service
- `stop_agent.bat` - Stop the service
- `start_chrome_debug.bat` - Start Chrome with debugging
- `logs/` - Agent log files

## Configuration (.env file)

```
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
HEADLESS=true
CDP_PORT=9222
SERVICE_INTERVAL=300
```

## Features

✅ **Chrome Integration** - Reuses your existing Chrome session with saved passwords
✅ **Session Persistence** - Stays logged in between runs  
✅ **Auto Recovery** - Handles lockouts and session expiry
✅ **Intelligent Login** - Detects "Welcome" and "Logout" signals
✅ **Background Service** - Runs invisibly with Task Scheduler
✅ **Rate Limiting** - Prevents "too many attempts" errors
✅ **Comprehensive Logging** - Full audit trail

## Troubleshooting

**Agent won't start:**
- Check logs in `logs/` folder
- Run `setup.bat` to reinstall dependencies
- Verify Python is installed

**Login issues:**
- Check credentials in `.env` file
- Try `start_chrome_debug.bat` first
- Look for lockout messages in logs

**Chrome connection issues:**
- Ensure Chrome is started with `start_chrome_debug.bat`
- Check that port 9222 is not blocked
- Try running without Chrome integration (edit run_agent.bat)

## Task Scheduler

The agent is configured to:
- Start automatically at login
- Restart if it crashes (3 attempts)
- Run with highest privileges
- Only start when network is available

## Log Files

Agent creates timestamped log files in `logs/`:
- `agent_YYYYMMDD_HHMMSS.log`

## Support

For issues, check the log files first. The agent includes detailed error reporting and self-diagnostic capabilities.
"@

$ReadmeContent | Out-File -FilePath "$InstallPath\README.md" -Encoding UTF8

# Run self-test if Python environment is ready
Write-Host "🧪 Running self-test..." -ForegroundColor Green
if (Test-Path "$InstallPath\.venv\Scripts\python.exe") {
    try {
        $testResult = & "$InstallPath\.venv\Scripts\python.exe" "$InstallPath\keyedin_resilient_agent.py" --selftest
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Self-test passed" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Self-test had warnings" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Could not run self-test: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Skipping self-test (Python environment not ready)" -ForegroundColor Yellow
}

# Final output
Write-Host ""
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📂 Installation Path: $InstallPath" -ForegroundColor White
Write-Host "📋 Logs Directory:   $InstallPath\logs\" -ForegroundColor White
Write-Host "🔧 Test Command:     $InstallPath\run_once.bat" -ForegroundColor White
Write-Host "🚀 Service Command:  $InstallPath\run_agent.bat" -ForegroundColor White
if (-not $NoChrome) {
    Write-Host "🎯 Chrome Setup:     $InstallPath\start_chrome_debug.bat" -ForegroundColor White
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

if (-not $NoTaskScheduler) {
    Write-Host "🔄 Background service is configured and ready to start" -ForegroundColor Green
    Write-Host "   Check status: schtasks /Query /TN '\KeyedIn\ResilientAgent'" -ForegroundColor Gray
    Write-Host "   Start now:    schtasks /Run /TN '\KeyedIn\ResilientAgent'" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "📖 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Edit $InstallPath\.env with your KeyedIn credentials" -ForegroundColor White
if (-not $NoChrome) {
    Write-Host "   2. Run start_chrome_debug.bat to enable Chrome integration" -ForegroundColor White
    Write-Host "   3. Test with run_once.bat" -ForegroundColor White
    Write-Host "   4. Deploy with run_agent.bat or Task Scheduler" -ForegroundColor White
} else {
    Write-Host "   2. Test with run_once.bat" -ForegroundColor White  
    Write-Host "   3. Deploy with run_agent.bat" -ForegroundColor White
}
Write-Host ""
Write-Host "🎉 Your KeyedIn agent is ready to go!" -ForegroundColor Green