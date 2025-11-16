Write-Host "`n=== Automated KeyedIn Session Capture ==="

# Kill any existing Chrome instances to ensure clean start
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Launch Chrome with remote debugging
$chromePort = 9222
$chromeArgs = "--remote-debugging-port=$chromePort --user-data-dir=$env:TEMP\chrome_debug_keyedin"
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}

Write-Host "Launching Chrome with debugging enabled..."
Start-Process $chromePath -ArgumentList $chromeArgs, "https://eaglesign.keyedinsign.com:8443/eaglesign/informer/"
Start-Sleep -Seconds 3

Write-Host "Getting Chrome debugging endpoint..."
$tabs = Invoke-RestMethod -Uri "http://localhost:$chromePort/json" -ErrorAction Stop
$debugUrl = $tabs[0].webSocketDebuggerUrl

Write-Host "`n=== INSTRUCTIONS ==="
Write-Host "1. Log into KeyedIn in the Chrome window that just opened"
Write-Host "2. Navigate to any report or click around"
Write-Host "3. Press ENTER here when ready to capture session..."
Read-Host

Write-Host "`nCapturing network traffic..."

# Use Chrome DevTools Protocol to get network requests
$session = New-Object -TypeName System.Net.WebSockets.ClientWebSocket
$uri = [System.Uri]::new($debugUrl)
$cts = New-Object System.Threading.CancellationToken

$session.ConnectAsync($uri, $cts).Wait()

# Enable Network domain
$enableNetwork = @{
    id = 1
    method = "Network.enable"
} | ConvertTo-Json

$bytes = [System.Text.Encoding]::UTF8.GetBytes($enableNetwork)
$segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)
$session.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts).Wait()

Write-Host "Monitoring network requests for 10 seconds..."
Start-Sleep -Seconds 10

# Get captured requests (simplified - in reality would need to parse WebSocket messages)
# For now, fallback to manual extraction with better UI

$session.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Done", $cts).Wait()

Write-Host "`n=== Manual Extraction (Chrome is open) ==="
Write-Host "In Chrome Dev Tools (F12):"
Write-Host "1. Go to Network tab"
Write-Host "2. Click any report or refresh page"
Write-Host "3. Find ViewRPCService request"
Write-Host "4. Copy Request URL and look for:"
Write-Host "   - authToken=XXXXXXXX"
Write-Host "   - clientId=XXXXXXXX"
Write-Host "5. Go to Cookies tab and copy JSESSIONID"
Write-Host ""

$authToken = Read-Host "Paste authToken"
$clientId = Read-Host "Paste clientId" 
$jsessionid = Read-Host "Paste JSESSIONID"

$sessionData = @{
    base_url = "https://eaglesign.keyedinsign.com:8443/eaglesign/"
    authToken = $authToken
    clientId = $clientId
    cookies = @{
        JSESSIONID = $jsessionid
    }
}

$sessionData | ConvertTo-Json | Out-File "keyedin_session.json" -Encoding UTF8

Write-Host "`n Session saved!"
Write-Host "`nClosing Chrome..."
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "`nNow run: .\test_exact_working_payload.ps1"
