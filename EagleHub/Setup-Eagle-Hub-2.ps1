# ============================================================================
# EAGLE WORKFLOW HUB 2 - INSTALLATION & SETUP
# ============================================================================

param(
    [switch]$Install = $false,
    [switch]$Configure = $false,
    [switch]$StartChrome = $false,
    [switch]$ScheduleTasks = $false
)

$EagleHubPath = "\\ES-FS02\users\brady\EagleHub"

function Write-Setup {
    param($Message, $Type = "INFO")
    
    switch($Type) {
        "SUCCESS" { Write-Host "✅ $Message" -ForegroundColor Green }
        "ERROR" { Write-Host "❌ $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "⚠️ $Message" -ForegroundColor Yellow }
        "INFO" { Write-Host "📋 $Message" -ForegroundColor Cyan }
    }
}

function Install-EagleHub2 {
    Write-Setup "🦅 Installing Eagle Workflow Hub 2..." "INFO"
    
    # Create server directory structure
    $directories = @(
        $EagleHubPath,
        "$EagleHubPath\Config",
        "$EagleHubPath\Logs",
        "$EagleHubPath\Bids",
        "$EagleHubPath\Drawings", 
        "$EagleHubPath\Historical",
        "$EagleHubPath\Templates",
        "$EagleHubPath\Scripts"
    )
    
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Setup "Created: $dir" "SUCCESS"
        }
    }
    
    # Copy files to server location
    $currentDir = $PSScriptRoot
    
    Copy-Item "$currentDir\eagle-workflow-hub-2.html" "$EagleHubPath\eagle-workflow-hub-2.html" -Force
    Copy-Item "$currentDir\Eagle-Hub-2-Engine.ps1" "$EagleHubPath\Scripts\Eagle-Hub-2-Engine.ps1" -Force
    
    # Create Chrome launcher
    Create-ChromeLauncher
    
    # Create default configuration
    Create-DefaultConfig
    
    # Create bid template
    Create-BidTemplate
    
    Write-Setup "Installation completed!" "SUCCESS"
}

function Create-ChromeLauncher {
    $launcherScript = @"
@echo off
title Eagle Workflow Hub 2 - Chrome Launcher
echo 🦅 Starting Eagle Workflow Hub 2...

REM Kill any existing Chrome instances for clean start
taskkill /f /im chrome.exe 2>nul

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start Chrome with Eagle Hub 2
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --new-window ^
    --start-maximized ^
    --disable-web-security ^
    --allow-running-insecure-content ^
    --disable-features=VizDisplayCompositor ^
    "$EagleHubPath\eagle-workflow-hub-2.html"

echo ✅ Eagle Workflow Hub 2 launched in Chrome
echo 📍 Location: $EagleHubPath\eagle-workflow-hub-2.html
echo.
echo Press any key to close this launcher...
pause >nul
"@
    
    $launcherPath = "$EagleHubPath\Launch-Eagle-Hub-2.bat"
    Set-Content -Path $launcherPath -Value $launcherScript -Encoding ASCII
    
    Write-Setup "Chrome launcher created: $launcherPath" "SUCCESS"
}

function Create-DefaultConfig {
    $defaultConfig = @{
        ServerPath = $EagleHubPath
        AutoMode = $true
        EmailCheckInterval = 30
        MarkupPercent = 35
        ScaleDetection = "auto"
        ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
        NotificationEmail = ""
        ActiveRole = "Estimator"
        SystemTimeout = 30
        MaxRetries = 3
        BackupEnabled = $true
        LogLevel = "INFO"
        Features = @{
            EmailProcessing = $true
            KeyedInIntegration = $true
            AutoPricing = $true
            DrawingAnalysis = $true
            BidGeneration = $true
            MultiHatMode = $true
        }
    }
    
    $configPath = "$EagleHubPath\Config\eagle-hub-config.json"
    $defaultConfig | ConvertTo-Json -Depth 3 | Set-Content -Path $configPath -Encoding UTF8
    
    Write-Setup "Default configuration created: $configPath" "SUCCESS"
}

function Create-BidTemplate {
    $bidTemplate = @"
<!DOCTYPE html>
<html>
<head>
    <title>Eagle Sign Co. - Bid Proposal</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #1e3c72; padding-bottom: 20px; margin-bottom: 30px; }
        .company-name { font-size: 2.5em; color: #1e3c72; margin: 0; }
        .company-tagline { font-style: italic; color: #666; }
        .bid-details { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .cost-breakdown { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
        .total-cost { background: #1e3c72; color: white; padding: 15px; text-align: center; font-size: 1.5em; border-radius: 8px; }
        .confidence-badge { background: #28a745; color: white; padding: 5px 10px; border-radius: 20px; font-size: 0.8em; }
        .footer { border-top: 2px solid #ddd; padding-top: 20px; margin-top: 40px; font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="company-name">🦅 Eagle Sign Co.</h1>
        <p class="company-tagline">Professional Sign Manufacturing & Installation</p>
    </div>
    
    <h2>Bid Proposal - Job #{{JobNumber}}</h2>
    <p><strong>Date:</strong> {{Date}}</p>
    <p><strong>Estimator:</strong> {{Estimator}}</p>
    
    <div class="bid-details">
        <h3>Project Details</h3>
        <p><strong>Sign Type:</strong> {{SignType}}</p>
        <p><strong>Total Area:</strong> {{SquareFeet}} square feet</p>
        <p><strong>Rate:</strong> ${{CostPerSqFt}} per square foot</p>
        <p><strong>Confidence Level:</strong> <span class="confidence-badge">{{Confidence}}% Accuracy</span></p>
    </div>
    
    <div class="total-cost">
        <strong>Total Investment: ${{TotalCost}}</strong>
    </div>
    
    <div class="cost-breakdown">
        <div>
            <h4>What's Included:</h4>
            <ul>
                <li>Professional design consultation</li>
                <li>Premium materials and fabrication</li>
                <li>Professional installation</li>
                <li>1-year warranty on workmanship</li>
                <li>Permit assistance (if required)</li>
            </ul>
        </div>
        <div>
            <h4>Next Steps:</h4>
            <ul>
                <li>Quote valid for {{ValidDays}} days</li>
                <li>50% deposit required to begin</li>
                <li>Typical completion: 2-3 weeks</li>
                <li>Call to schedule site visit</li>
                <li>Questions? Contact us anytime!</li>
            </ul>
        </div>
    </div>
    
    <div class="footer">
        <p><strong>{{CompanyName}}</strong> - Your Partner in Professional Signage</p>
        <p>This estimate was generated using advanced pricing analytics based on {{Confidence}}% historical data accuracy.</p>
        <p><em>Generated by Eagle Workflow Hub 2 - Automated Estimating System</em></p>
    </div>
</body>
</html>
"@
    
    $templatePath = "$EagleHubPath\Templates\BidTemplate.html"
    Set-Content -Path $templatePath -Value $bidTemplate -Encoding UTF8
    
    Write-Setup "Bid template created: $templatePath" "SUCCESS"
}

function Setup-ScheduledTasks {
    Write-Setup "⏰ Setting up scheduled tasks..." "INFO"
    
    # Task 1: Auto-run every 30 minutes
    $action30 = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File `"$EagleHubPath\Scripts\Eagle-Hub-2-Engine.ps1`" -Mode Auto"
    $trigger30 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) -Once -At (Get-Date).AddMinutes(1)
    $settings30 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    Register-ScheduledTask -TaskName "Eagle Hub 2 - Auto Scan (30 min)" -Action $action30 -Trigger $trigger30 -Settings $settings30 -Force
    
    # Task 2: Hourly full scan
    $actionHour = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File `"$EagleHubPath\Scripts\Eagle-Hub-2-Engine.ps1`" -Mode Auto -IntervalMinutes 60"
    $triggerHour = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 1) -Once -At (Get-Date).AddHours(1)
    $settingsHour = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    Register-ScheduledTask -TaskName "Eagle Hub 2 - Full Scan (Hourly)" -Action $actionHour -Trigger $triggerHour -Settings $settingsHour -Force
    
    # Task 3: Daily startup
    $actionStartup = New-ScheduledTaskAction -Execute "$EagleHubPath\Launch-Eagle-Hub-2.bat"
    $triggerStartup = New-ScheduledTaskTrigger -AtLogon
    $settingsStartup = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    Register-ScheduledTask -TaskName "Eagle Hub 2 - Startup Launch" -Action $actionStartup -Trigger $triggerStartup -Settings $settingsStartup -Force
    
    Write-Setup "Scheduled tasks created successfully!" "SUCCESS"
    Write-Setup "  - Auto scan every 30 minutes" "INFO"
    Write-Setup "  - Full scan every hour" "INFO"  
    Write-Setup "  - Launch at Windows startup" "INFO"
}

function Start-ChromeWithHub {
    Write-Setup "🌐 Starting Chrome with Eagle Hub 2..." "INFO"
    
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    $hubUrl = "file:///$($EagleHubPath.Replace('\', '/'))/eagle-workflow-hub-2.html"
    
    if (Test-Path $chromePath) {
        # Kill existing Chrome processes for clean start
        Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep 2
        
        # Start Chrome with Eagle Hub
        $chromeArgs = @(
            "--new-window",
            "--start-maximized", 
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--allow-file-access-from-files",
            $hubUrl
        )
        
        Start-Process -FilePath $chromePath -ArgumentList $chromeArgs
        Write-Setup "Chrome launched with Eagle Hub 2!" "SUCCESS"
        Write-Setup "URL: $hubUrl" "INFO"
    } else {
        Write-Setup "Chrome not found at $chromePath" "ERROR"
        Write-Setup "Please install Chrome or update the path in config" "WARNING"
    }
}

function Show-Menu {
    Write-Host "`n🦅 EAGLE WORKFLOW HUB 2 - SETUP & CONFIGURATION" -ForegroundColor Cyan
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. 📦 Full Installation" -ForegroundColor Green
    Write-Host "2. ⚙️ Configure Settings Only" -ForegroundColor Yellow
    Write-Host "3. 🌐 Launch in Chrome" -ForegroundColor Blue
    Write-Host "4. ⏰ Setup Scheduled Tasks" -ForegroundColor Magenta
    Write-Host "5. 🧪 Test System Connections" -ForegroundColor Cyan
    Write-Host "6. 📋 Show Current Status" -ForegroundColor White
    Write-Host "0. ❌ Exit" -ForegroundColor Red
    Write-Host ""
}

function Test-SystemConnections {
    Write-Setup "🔌 Testing system connections..." "INFO"
    
    # Test server path
    if (Test-Path $EagleHubPath) {
        Write-Setup "Server path accessible: $EagleHubPath" "SUCCESS"
    } else {
        Write-Setup "Server path not accessible: $EagleHubPath" "ERROR"
    }
    
    # Test Chrome
    if (Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe") {
        Write-Setup "Chrome found and ready" "SUCCESS"
    } else {
        Write-Setup "Chrome not found" "WARNING"
    }
    
    # Test Outlook
    try {
        $outlook = New-Object -ComObject Outlook.Application
        Write-Setup "Outlook connection: Ready" "SUCCESS"
    } catch {
        Write-Setup "Outlook connection: Failed" "WARNING"
    }
    
    # Test PowerShell execution policy
    $policy = Get-ExecutionPolicy
    if ($policy -eq "Restricted") {
        Write-Setup "PowerShell execution policy is Restricted" "WARNING"
        Write-Setup "Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" "INFO"
    } else {
        Write-Setup "PowerShell execution policy: $policy (OK)" "SUCCESS"
    }
}

function Show-Status {
    Write-Setup "📊 Eagle Workflow Hub 2 Status:" "INFO"
    Write-Host ""
    
    # Check installation
    if (Test-Path "$EagleHubPath\eagle-workflow-hub-2.html") {
        Write-Setup "✅ Installation: Complete" "SUCCESS"
    } else {
        Write-Setup "❌ Installation: Not found" "ERROR"
    }
    
    # Check scheduled tasks
    $tasks = Get-ScheduledTask -TaskName "Eagle Hub 2*" -ErrorAction SilentlyContinue
    if ($tasks) {
        Write-Setup "✅ Scheduled Tasks: $($tasks.Count) tasks configured" "SUCCESS"
        foreach ($task in $tasks) {
            Write-Setup "  - $($task.TaskName): $($task.State)" "INFO"
        }
    } else {
        Write-Setup "❌ Scheduled Tasks: Not configured" "WARNING"
    }
    
    # Check configuration
    if (Test-Path "$EagleHubPath\Config\eagle-hub-config.json") {
        Write-Setup "✅ Configuration: Found" "SUCCESS"
    } else {
        Write-Setup "❌ Configuration: Missing" "ERROR"
    }
    
    Write-Host ""
    Write-Setup "📁 Server Location: $EagleHubPath" "INFO"
    Write-Setup "🌐 Launch URL: file:///$($EagleHubPath.Replace('\', '/'))/eagle-workflow-hub-2.html" "INFO"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if ($Install) {
    Install-EagleHub2
} elseif ($Configure) {
    Create-DefaultConfig
    Write-Setup "Configuration updated!" "SUCCESS"
} elseif ($StartChrome) {
    Start-ChromeWithHub
} elseif ($ScheduleTasks) {
    Setup-ScheduledTasks
} else {
    # Interactive menu
    do {
        Show-Menu
        $choice = Read-Host "Select option (0-6)"
        
        switch ($choice) {
            "1" { 
                Install-EagleHub2
                Setup-ScheduledTasks
                Start-ChromeWithHub
            }
            "2" { Create-DefaultConfig }
            "3" { Start-ChromeWithHub }
            "4" { Setup-ScheduledTasks }
            "5" { Test-SystemConnections }
            "6" { Show-Status }
            "0" { Write-Setup "👋 Goodbye!" "INFO"; break }
            default { Write-Setup "Invalid selection. Please try again." "WARNING" }
        }
        
        if ($choice -ne "0") {
            Write-Host "`nPress any key to continue..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    } while ($choice -ne "0")
}

Write-Setup "`n🦅 Eagle Workflow Hub 2 Setup Complete!" "SUCCESS"
