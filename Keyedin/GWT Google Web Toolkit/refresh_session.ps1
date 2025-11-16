Write-Host "`n=== KeyedIn Session Refresh ==="
Write-Host "1. Open browser to: https://eaglesign.keyedinsign.com:8443/eaglesign/informer/"
Write-Host "2. Log in (if not already logged in)"
Write-Host "3. Open Dev Tools (F12) -> Network tab"
Write-Host "4. Refresh the page or click any report"
Write-Host "5. Find a request to ViewRPCService"
Write-Host "6. Copy these values:"
Write-Host "   - Request URL query params: authToken=... and clientId=..."
Write-Host "   - Request Cookies: JSESSIONID=..."
Write-Host ""

$authToken = Read-Host "Paste authToken"
$clientId = Read-Host "Paste clientId"
$jsessionid = Read-Host "Paste JSESSIONID"

$session = @{
    base_url = "https://eaglesign.keyedinsign.com:8443/eaglesign/"
    authToken = $authToken
    clientId = $clientId
    cookies = @{
        JSESSIONID = $jsessionid
    }
}

$session | ConvertTo-Json | Out-File "keyedin_session.json" -Encoding UTF8

Write-Host "`n Session saved to keyedin_session.json"
Write-Host " Now re-run: .\test_exact_working_payload.ps1"
