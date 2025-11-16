# Test script to find the right API method for getting report definitions
$session = Get-Content keyedin_session.json | ConvertFrom-Json
$baseUrl = $session.base_url
$authToken = $session.authToken
$clientId = $session.clientId

$headers = @{
    'Content-Type' = 'text/x-gwt-rpc; charset=UTF-8'
    'X-GWT-Module-Base' = "${baseUrl}informer/"
    'X-GWT-Permutation' = '6823F3E0DFFF554BC1A7951AA98B182D'
    'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

$url = "${baseUrl}informer/rpc/protected/ViewRPCService?authToken=${authToken}&clientId=${clientId}"

# Test ViewToken for "Inventory List" or similar report
# We'll use one of the discovered ViewTokens
$viewToken = "600437df-77ae-4aca-8f93-45b022255489"

Write-Host "`n=== Testing Different API Methods ==="

# Test 1: Try getView
Write-Host "`nTest 1: getView"
$payload1 = "7|0|6|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getView|com.entrinsik.gwt.data.shared.ViewToken/3777265110|$viewToken|1|2|3|4|1|5|6|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload1 -Headers $headers -ErrorAction Stop
    Write-Host "  Status: $($response.StatusCode)"
    Write-Host "  Length: $($response.Content.Length) bytes"
    Write-Host "  Preview: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))"
} catch {
    Write-Host "  Error: $($_.Exception.Message)"
}

# Test 2: Try load
Write-Host "`nTest 2: load"
$payload2 = "7|0|6|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|load|com.entrinsik.gwt.data.shared.ViewToken/3777265110|$viewToken|1|2|3|4|1|5|6|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload2 -Headers $headers -ErrorAction Stop
    Write-Host "  Status: $($response.StatusCode)"
    Write-Host "  Length: $($response.Content.Length) bytes"
    Write-Host "  Preview: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))"
} catch {
    Write-Host "  Error: $($_.Exception.Message)"
}

# Test 3: Try getDefinition
Write-Host "`nTest 3: getDefinition"
$payload3 = "7|0|6|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getDefinition|com.entrinsik.gwt.data.shared.ViewToken/3777265110|$viewToken|1|2|3|4|1|5|6|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload3 -Headers $headers -ErrorAction Stop
    Write-Host "  Status: $($response.StatusCode)"
    Write-Host "  Length: $($response.Content.Length) bytes"
    Write-Host "  Preview: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))"
} catch {
    Write-Host "  Error: $($_.Exception.Message)"
}

# Test 4: Try getData with minimal params (see what error it gives)
Write-Host "`nTest 4: getData with minimal params"
$payload4 = "7|0|6|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|com.entrinsik.gwt.data.shared.ViewToken/3777265110|$viewToken|1|2|3|4|1|5|6|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload4 -Headers $headers -ErrorAction Stop
    Write-Host "  Status: $($response.StatusCode)"
    Write-Host "  Length: $($response.Content.Length) bytes"
    Write-Host "  Preview: $($response.Content.Substring(0, [Math]::Min(500, $response.Content.Length)))"
    
    # Save full response for inspection
    $response.Content | Out-File "test4_response.txt" -Encoding UTF8
    Write-Host "  Full response saved to: test4_response.txt"
} catch {
    Write-Host "  Error: $($_.Exception.Message)"
}

Write-Host "`n=== Tests Complete ==="
Write-Host "Check the responses above to see which method works"
