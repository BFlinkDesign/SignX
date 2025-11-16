$session = Get-Content keyedin_session.json | ConvertFrom-Json
$baseUrl = $session.base_url
$authToken = $session.authToken
$clientId = $session.clientId

$headers = @{
    "Content-Type" = "text/x-gwt-rpc; charset=UTF-8"
    "X-GWT-Module-Base" = "${baseUrl}informer/"
    "X-GWT-Permutation" = "6823F3E0DFFF554BC1A7951AA98B182D"
}

$url = "${baseUrl}informer/rpc/protected/ViewRPCService?authToken=${authToken}&clientId=${clientId}"

Write-Host "`n=== Testing getData with array parameters ==="

# Use a discovered report ViewToken
$viewToken = "600437df-77ae-4aca-8f93-45b022255489"

# Test: getData with ViewToken array and empty LoadOptions (simplified from discovery payload)
Write-Host "`nTest: getData([ViewToken[]], [LoadOptions[]]) - NO search criteria"
$payload = "7|0|8|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|$viewToken|1|2|3|4|2|5|6|5|1|7|8|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload -Headers $headers -ErrorAction Stop
    Write-Host "   Status: $($response.StatusCode)"
    Write-Host "   Length: $($response.Content.Length) bytes"
    
    # Save full response
    $response.Content | Out-File "getdata_test_response.txt" -Encoding UTF8
    Write-Host "   Full response saved to: getdata_test_response.txt"
    
    # Show preview
    if ($response.Content.Length -gt 500) {
        Write-Host "`n  Response preview (first 500 chars):"
        Write-Host "  $($response.Content.Substring(0, 500))"
        Write-Host "  ..."
    } else {
        Write-Host "`n  Full response:"
        Write-Host "  $($response.Content)"
    }
    
} catch {
    Write-Host "   Error: $($_.Exception.Message)"
}

Write-Host "`n=== Test Complete ==="
Write-Host "Check getdata_test_response.txt for full details"
