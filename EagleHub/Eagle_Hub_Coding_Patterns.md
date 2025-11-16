# Eagle Workflow Hub - Coding Patterns & Examples

## PowerShell Script Template

```powershell
# ============================================================================
# EAGLE WORKFLOW HUB - [MODULE NAME]
# ============================================================================
# Version: 2.0
# Author: Eagle Sign Co
# Description: [Brief description]
# Dependencies: KeyedIn, Outlook, Network Access
# ============================================================================

# GLOBAL CONFIGURATION
$Global:EagleConfig = @{
    ServerPath = "\\ES-FS02\users\brady\EagleHub"
    LocalPath = "C:\EagleHub"
    LogPath = "\\ES-FS02\users\brady\EagleHub\Logs"
    KeyedInURL = "http://keyedin.eaglesign.com"
    EmailCheckInterval = 30  # minutes
    AutoMode = $true
    MarkupPercent = 35
    Browser = "chrome"
}

# LOGGING FUNCTION (Use in every script)
function Write-EagleLog {
    param(
        [string]$Message,
        [string]$Type = "INFO",
        [string]$Module = "SYSTEM"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Type] [$Module] $Message"
    
    # Console output with colors
    switch ($Type) {
        "ERROR"   { Write-Host $logEntry -ForegroundColor Red }
        "WARNING" { Write-Host $logEntry -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
        "PROCESS" { Write-Host $logEntry -ForegroundColor Cyan }
        default   { Write-Host $logEntry }
    }
    
    # File logging
    $logFile = Join-Path $Global:EagleConfig.LogPath "Eagle-Hub-$(Get-Date -Format 'yyyy-MM-dd').log"
    $logEntry | Out-File -FilePath $logFile -Append -Encoding UTF8
}

# ERROR HANDLING WRAPPER
function Invoke-EagleOperation {
    param(
        [scriptblock]$Operation,
        [string]$OperationName,
        [string]$Module
    )
    
    try {
        Write-EagleLog "Starting $OperationName..." "PROCESS" $Module
        $result = & $Operation
        Write-EagleLog "✅ $OperationName completed successfully" "SUCCESS" $Module
        return $result
    }
    catch {
        Write-EagleLog "❌ $OperationName failed: $($_.Exception.Message)" "ERROR" $Module
        
        # Attempt recovery
        if ($Global:EagleConfig.AutoMode) {
            Write-EagleLog "🔄 Attempting automatic recovery..." "WARNING" $Module
            Start-Sleep -Seconds 5
            # Retry logic here
        }
        
        return $null
    }
}
```

## Email Processing Pattern

```powershell
function Process-BidRequestEmail {
    param(
        [Microsoft.Office.Interop.Outlook.MailItem]$Email
    )
    
    Write-EagleLog "📧 Processing bid request from $($Email.SenderName)" "PROCESS" "OUTLOOK"
    
    # Extract key information
    $bidInfo = @{
        Customer = Extract-CustomerName -Subject $Email.Subject -Body $Email.Body
        JobNumber = Generate-JobNumber
        ReceivedDate = $Email.ReceivedTime
        Attachments = @()
        Priority = Determine-Priority -Sender $Email.SenderEmailAddress
    }
    
    # Process attachments
    foreach ($attachment in $Email.Attachments) {
        $savePath = Join-Path $Global:EagleConfig.ServerPath "Incoming\$($bidInfo.JobNumber)"
        
        if (-not (Test-Path $savePath)) {
            New-Item -ItemType Directory -Path $savePath -Force | Out-Null
        }
        
        $filePath = Join-Path $savePath $attachment.FileName
        $attachment.SaveAsFile($filePath)
        
        $bidInfo.Attachments += @{
            Name = $attachment.FileName
            Path = $filePath
            Type = [System.IO.Path]::GetExtension($attachment.FileName)
        }
        
        Write-EagleLog "📎 Saved attachment: $($attachment.FileName)" "SUCCESS" "OUTLOOK"
    }
    
    # Create KeyedIn entry
    New-KeyedInEntry -BidInfo $bidInfo
    
    # Start processing pipeline
    Start-BidProcessingPipeline -BidInfo $bidInfo
    
    return $bidInfo
}
```

## KeyedIn Integration Pattern

```powershell
function Get-KeyedInHistoricalData {
    param(
        [string]$CustomerName,
        [string]$SignType
    )
    
    Write-EagleLog "🗃️ Querying KeyedIn for historical data..." "PROCESS" "KEYEDIN"
    
    # Read from Excel export (safest integration method)
    $excelPath = "\\ES-FS02\customers2\2025 Work Order Tracking(correct book).xlsx"
    
    try {
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $false
        $workbook = $excel.Workbooks.Open($excelPath)
        $worksheet = $workbook.Worksheets.Item(1)
        
        $historicalJobs = @()
        $row = 2  # Start after header
        
        while ($worksheet.Cells.Item($row, 1).Value2) {
            $job = @{
                JobNumber = $worksheet.Cells.Item($row, 1).Value2
                Customer = $worksheet.Cells.Item($row, 2).Value2
                SignType = $worksheet.Cells.Item($row, 3).Value2
                SquareFeet = $worksheet.Cells.Item($row, 4).Value2
                TotalCost = $worksheet.Cells.Item($row, 5).Value2
                Date = $worksheet.Cells.Item($row, 6).Value2
            }
            
            if ($job.Customer -like "*$CustomerName*" -or $job.SignType -eq $SignType) {
                $historicalJobs += $job
            }
            
            $row++
        }
        
        $workbook.Close($false)
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
        
        Write-EagleLog "✅ Found $($historicalJobs.Count) similar jobs" "SUCCESS" "KEYEDIN"
        return $historicalJobs
    }
    catch {
        Write-EagleLog "❌ KeyedIn query failed: $($_.Exception.Message)" "ERROR" "KEYEDIN"
        return @()
    }
}
```

## Drawing Analysis Pattern

```powershell
function Analyze-DrawingScale {
    param(
        [string]$PDFText
    )
    
    Write-EagleLog "📐 Detecting drawing scale..." "PROCESS" "DRAWING"
    
    # AIA standard scale patterns
    $scalePatterns = @(
        @{ Pattern = '1/8"\s*=\s*1''-0"'; Scale = 96 }
        @{ Pattern = '1/4"\s*=\s*1''-0"'; Scale = 48 }
        @{ Pattern = '1/2"\s*=\s*1''-0"'; Scale = 24 }
        @{ Pattern = '1"\s*=\s*1''-0"'; Scale = 12 }
        @{ Pattern = '3/8"\s*=\s*1''-0"'; Scale = 32 }
        @{ Pattern = '3/4"\s*=\s*1''-0"'; Scale = 16 }
        @{ Pattern = '1\s*:\s*100'; Scale = 100 }
        @{ Pattern = '1\s*:\s*50'; Scale = 50 }
    )
    
    foreach ($scalePattern in $scalePatterns) {
        if ($PDFText -match $scalePattern.Pattern) {
            Write-EagleLog "✅ Scale detected: $($Matches[0]) (Factor: $($scalePattern.Scale))" "SUCCESS" "DRAWING"
            return $scalePattern.Scale
        }
    }
    
    Write-EagleLog "⚠️ No scale detected, using default 1/8\" = 1'-0\"" "WARNING" "DRAWING"
    return 96  # Default to 1/8" = 1'-0"
}
```

## Pricing Calculation Pattern

```powershell
function Calculate-IntelligentPrice {
    param(
        [string]$SignType,
        [double]$SquareFeet,
        [array]$HistoricalData
    )
    
    Write-EagleLog "💰 Calculating intelligent pricing..." "PROCESS" "PRICING"
    
    # Filter relevant historical data
    $relevantJobs = $HistoricalData | Where-Object {
        $_.SignType -eq $SignType -and
        [Math]::Abs($_.SquareFeet - $SquareFeet) / $SquareFeet -le 0.3
    }
    
    if ($relevantJobs.Count -ge 3) {
        # Calculate statistics
        $costPerSqFt = $relevantJobs | ForEach-Object { $_.TotalCost / $_.SquareFeet }
        $avgCost = ($costPerSqFt | Measure-Object -Average).Average
        $stdDev = Calculate-StandardDeviation -Values $costPerSqFt
        
        # Calculate confidence based on sample size
        $confidence = [Math]::Min(95, 60 + ($relevantJobs.Count * 5))
        
        # Apply markup
        $basePrice = $avgCost * $SquareFeet
        $finalPrice = $basePrice * (1 + ($Global:EagleConfig.MarkupPercent / 100))
        
        $result = @{
            BasePrice = [Math]::Round($basePrice, 2)
            FinalPrice = [Math]::Round($finalPrice, 2)
            CostPerSqFt = [Math]::Round($avgCost, 2)
            Confidence = $confidence
            SampleSize = $relevantJobs.Count
            StdDeviation = [Math]::Round($stdDev, 2)
            PriceRange = @{
                Low = [Math]::Round($finalPrice * 0.95, 2)
                High = [Math]::Round($finalPrice * 1.05, 2)
            }
        }
        
        Write-EagleLog "✅ Price calculated: $$($result.FinalPrice) (±5% = $$($result.PriceRange.Low)-$$($result.PriceRange.High))" "SUCCESS" "PRICING"
        Write-EagleLog "📊 Based on $($result.SampleSize) similar jobs, $($result.Confidence)% confidence" "SUCCESS" "PRICING"
    }
    else {
        # Use default pricing matrix
        $defaultRates = @{
            "Channel Letters" = 85.00
            "Cabinet Signs" = 55.00
            "Monument Signs" = 135.00
            "Vinyl Graphics" = 35.00
            "Digital Prints" = 45.00
            "Dimensional Letters" = 75.00
        }
        
        $rate = $defaultRates[$SignType] ?? 65.00
        $basePrice = $rate * $SquareFeet
        $finalPrice = $basePrice * (1 + ($Global:EagleConfig.MarkupPercent / 100))
        
        $result = @{
            BasePrice = [Math]::Round($basePrice, 2)
            FinalPrice = [Math]::Round($finalPrice, 2)
            CostPerSqFt = $rate
            Confidence = 60
            SampleSize = 0
            Note = "Using default rates - insufficient historical data"
        }
        
        Write-EagleLog "⚠️ Using default rate: $$rate/sq ft (insufficient historical data)" "WARNING" "PRICING"
    }
    
    return $result
}
```

## HTML Dashboard Pattern

```html
<!-- Dashboard Component Template -->
<div class="eagle-dashboard-component">
    <div class="component-header">
        <h3><span class="icon">📊</span> Component Title</h3>
        <div class="status-indicator" id="component-status">
            <span class="status-dot active"></span>
            <span class="status-text">Active</span>
        </div>
    </div>
    
    <div class="component-body">
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value" id="metric-1">0</div>
                <div class="metric-label">Label</div>
            </div>
        </div>
    </div>
    
    <div class="component-actions">
        <button class="btn btn-primary" onclick="performAction()">
            <span class="btn-icon">🚀</span>
            <span class="btn-text">Action</span>
        </button>
    </div>
</div>

<script>
// Component JavaScript Pattern
class EagleComponent {
    constructor(componentId, config) {
        this.id = componentId;
        this.config = {
            updateInterval: 30000,  // 30 seconds
            autoRefresh: true,
            ...config
        };
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.startAutoRefresh();
        this.loadData();
    }
    
    bindEvents() {
        document.getElementById(`${this.id}-refresh`).addEventListener('click', () => {
            this.loadData();
        });
    }
    
    startAutoRefresh() {
        if (this.config.autoRefresh) {
            setInterval(() => {
                this.loadData();
            }, this.config.updateInterval);
        }
    }
    
    async loadData() {
        try {
            this.setStatus('loading');
            const data = await this.fetchData();
            this.updateDisplay(data);
            this.setStatus('active');
        } catch (error) {
            console.error(`Error in ${this.id}:`, error);
            this.setStatus('error');
        }
    }
    
    setStatus(status) {
        const statusElement = document.getElementById(`${this.id}-status`);
        statusElement.className = `status-indicator ${status}`;
        
        const statusText = {
            'loading': 'Loading...',
            'active': 'Active',
            'error': 'Error',
            'idle': 'Idle'
        };
        
        statusElement.querySelector('.status-text').textContent = statusText[status];
    }
}
</script>
```

## File Organization Pattern

```powershell
function Organize-ProjectFiles {
    param(
        [string]$JobNumber,
        [string]$CustomerName,
        [string]$ProjectType
    )
    
    Write-EagleLog "📁 Organizing project files..." "PROCESS" "FILES"
    
    # Standard folder structure
    $projectRoot = Join-Path $Global:EagleConfig.ServerPath "Projects\$JobNumber"
    
    $folders = @(
        "01_Incoming",
        "02_Estimates",
        "03_Drawings",
        "04_Production",
        "05_Photos",
        "06_Invoices",
        "07_Correspondence"
    )
    
    foreach ($folder in $folders) {
        $folderPath = Join-Path $projectRoot $folder
        if (-not (Test-Path $folderPath)) {
            New-Item -ItemType Directory -Path $folderPath -Force | Out-Null
            Write-EagleLog "📂 Created: $folder" "SUCCESS" "FILES"
        }
    }
    
    # Create project info file
    $projectInfo = @{
        JobNumber = $JobNumber
        Customer = $CustomerName
        ProjectType = $ProjectType
        CreatedDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Status = "Active"
        FilePaths = @{
            Root = $projectRoot
            Incoming = Join-Path $projectRoot "01_Incoming"
            Estimates = Join-Path $projectRoot "02_Estimates"
            Drawings = Join-Path $projectRoot "03_Drawings"
            Production = Join-Path $projectRoot "04_Production"
            Photos = Join-Path $projectRoot "05_Photos"
            Invoices = Join-Path $projectRoot "06_Invoices"
            Correspondence = Join-Path $projectRoot "07_Correspondence"
        }
    }
    
    $projectInfo | ConvertTo-Json -Depth 3 | Out-File -FilePath (Join-Path $projectRoot "project-info.json") -Encoding UTF8
    
    Write-EagleLog "✅ Project structure created for $JobNumber" "SUCCESS" "FILES"
    return $projectInfo
}
```

## Scheduled Task Pattern

```powershell
# Create scheduled tasks for automation
function Setup-EagleScheduledTasks {
    Write-EagleLog "⏰ Setting up scheduled tasks..." "PROCESS" "SYSTEM"
    
    $tasks = @(
        @{
            Name = "Eagle Hub 30min Scan"
            Interval = 30
            Script = "Eagle-Hub-Quick-Scan.ps1"
        },
        @{
            Name = "Eagle Hub Hourly Deep Scan"
            Interval = 60
            Script = "Eagle-Hub-Deep-Scan.ps1"
        }
    )
    
    foreach ($task in $tasks) {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-ExecutionPolicy Bypass -File `"$($Global:EagleConfig.ServerPath)\Scripts\$($task.Script)`""
        
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
            -RepetitionInterval (New-TimeSpan -Minutes $task.Interval) `
            -RepetitionDuration (New-TimeSpan -Days 365)
        
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -RestartCount 3
        
        Register-ScheduledTask `
            -TaskName $task.Name `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description "Eagle Workflow Hub automated task" `
            -Force
        
        Write-EagleLog "✅ Scheduled task created: $($task.Name)" "SUCCESS" "SYSTEM"
    }
}
```

## Pattern Learning Algorithm

```powershell
function Learn-UserPatterns {
    param(
        [string]$PatternType,
        [hashtable]$ObservedData
    )
    
    Write-EagleLog "🧠 Learning user patterns..." "PROCESS" "AI"
    
    $patternFile = Join-Path $Global:EagleConfig.ServerPath "AI\patterns.json"
    
    # Load existing patterns
    if (Test-Path $patternFile) {
        $patterns = Get-Content $patternFile | ConvertFrom-Json -AsHashtable
    } else {
        $patterns = @{}
    }
    
    # Update pattern data
    if (-not $patterns.ContainsKey($PatternType)) {
        $patterns[$PatternType] = @{
            Observations = @()
            Confidence = 0
            LastUpdated = Get-Date
        }
    }
    
    # Add new observation
    $patterns[$PatternType].Observations += $ObservedData
    
    # Keep only recent observations (last 100)
    if ($patterns[$PatternType].Observations.Count -gt 100) {
        $patterns[$PatternType].Observations = $patterns[$PatternType].Observations[-100..-1]
    }
    
    # Calculate confidence
    $patterns[$PatternType].Confidence = [Math]::Min(95, 50 + ($patterns[$PatternType].Observations.Count))
    $patterns[$PatternType].LastUpdated = Get-Date
    
    # Save updated patterns
    $patterns | ConvertTo-Json -Depth 5 | Out-File -FilePath $patternFile -Encoding UTF8
    
    Write-EagleLog "✅ Pattern learned: $PatternType (Confidence: $($patterns[$PatternType].Confidence)%)" "SUCCESS" "AI"
    
    return $patterns[$PatternType]
}
```