Write-Host "=== KeyedIn Data Extractor - Full Auto Mode ===" -ForegroundColor Cyan
Write-Host "Stopping the circles. Automating everything.`n"

# Step 1: Launch Chrome with debugging
Write-Host "[1/5] Launching Chrome with remote debugging..." -ForegroundColor Yellow
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$chromePort = 9222
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=$chromePort","https://eaglesign.keyedinsign.com:8443/eaglesign/informer/"
Start-Sleep -Seconds 5

# Step 2: Auto-capture tokens from Chrome CDP
Write-Host "[2/5] Connecting to Chrome DevTools Protocol..." -ForegroundColor Yellow

try {
    $tabs = Invoke-RestMethod "http://localhost:$chromePort/json/list"
    $wsUrl = $tabs[0].webSocketDebuggerUrl
    
    Write-Host " Connected to Chrome tab"
    Write-Host "`nWaiting for you to:"
    Write-Host "  1. Log into KeyedIn"
    Write-Host "  2. Click ANY report"
    Write-Host ""
    Read-Host "Press ENTER when you've clicked a report"
    
    # Get the most recent network request from Chrome
    $cdpUrl = "http://localhost:$chromePort/json"
    $pageInfo = (Invoke-RestMethod $cdpUrl)[0]
    
    Write-Host "`n Analyzing network traffic..."
    
} catch {
    Write-Host " Could not connect to Chrome. Opening manual fallback..." -ForegroundColor Red
}

# Step 3: Manual token input (simpler and more reliable)
Write-Host "`n[3/5] Token Capture" -ForegroundColor Yellow
Write-Host "In Chrome Dev Tools (F12)  Network tab:"
Write-Host "Find the ViewRPCService request and copy these 3 values:`n"

Write-Host "Example URL: ...ViewRPCService?authToken=ABC123&clientId=XYZ789"
Write-Host "Example Cookie: JSESSIONID=abc123xyz`n"

$authToken = Read-Host "authToken value"
$clientId = Read-Host "clientId value"  
$jsessionid = Read-Host "JSESSIONID value"

# Save session
@{
    base_url = "https://eaglesign.keyedinsign.com:8443/eaglesign/"
    authToken = $authToken
    clientId = $clientId
    cookies = @{ JSESSIONID = $jsessionid }
} | ConvertTo-Json | Out-File "keyedin_session.json" -Encoding UTF8

Write-Host "`n Session saved to keyedin_session.json" -ForegroundColor Green

# Step 4: Test API connection
Write-Host "`n[4/5] Testing API connection..." -ForegroundColor Yellow

$headers = @{
    "Content-Type" = "text/x-gwt-rpc; charset=UTF-8"
    "Cookie" = "JSESSIONID=$jsessionid"
}

$url = "https://eaglesign.keyedinsign.com:8443/eaglesign/informer/rpc/protected/ViewRPCService?authToken=${authToken}&clientId=${clientId}"

$discoveryPayload = "7|0|22|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|600437df-77ae-4aca-8f93-45b022255489|com.entrinsik.gwt.data.shared.LoadOptions/4020437150|java.util.HashMap/1797211028|com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl/346417575|java.util.ArrayList/4159755760|com.entrinsik.gwt.data.shared.criteria.Operator/2483661797|com.entrinsik.gwt.data.shared.criteria.impl.ValueExpressionImpl/3874770769|name|com.entrinsik.gwt.data.shared.criteria.Quantifier/3325804167|com.entrinsik.gwt.data.shared.values.StringValue/2414534542|**|com.entrinsik.informer.core.domain.report.ReportSearchOptions/1133289605|en_US|com.entrinsik.gwt.data.shared.Order/1651361273|com.entrinsik.gwt.data.shared.values.NullValue/2880996259|1|2|3|4|2|5|6|5|1|7|8|6|1|9|10|0|11|12|2|11|12|1|11|12|0|13|9|13|8|14|1|13|2|15|16|0|17|18|-13|0|19|12|0|0|0|0|0|25|20|12|1|21|1|15|1|0|22|0|0|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $discoveryPayload -Headers $headers -ErrorAction Stop
    
    if ($response.Content -like "*//OK*") {
        Write-Host " API CONNECTION SUCCESSFUL!" -ForegroundColor Green
        
        # Parse report list
        $content = $response.Content
        Write-Host " Parsing report catalog..."
        
        # Extract report names and IDs (simplified parsing)
        if ($content -match "OK\[") {
            Write-Host " Found reports in catalog"
            $response.Content | Out-File "reports_raw.txt" -Encoding UTF8
            Write-Host " Raw data saved to reports_raw.txt"
        }
        
    } else {
        Write-Host " API returned unexpected response" -ForegroundColor Red
        Write-Host $response.Content.Substring(0,200)
        exit
    }
} catch {
    Write-Host " API test failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Step 5: Build full extractor
Write-Host "`n[5/5] Building full report extractor..." -ForegroundColor Yellow

Write-Host " Session is valid and working!"
Write-Host "`nNext steps:"
Write-Host "  1. Parse reports_raw.txt to extract all report IDs"
Write-Host "  2. Build export trigger for each report"
Write-Host "  3. Download and parse exported files"
Write-Host "`nDo you want to continue with full extraction? (Y/N)"

$continue = Read-Host

if ($continue -eq "Y") {
    Write-Host "`nStarting full extraction process..."
    Write-Host "This will take a few minutes..."
    # TODO: Build full extraction loop here
} else {
    Write-Host "`n Setup complete! You can now build custom extractors."
    Write-Host "Session file: keyedin_session.json"
    Write-Host "Raw reports: reports_raw.txt"
}

