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

Write-Host "`n=== Testing getData Signatures ==="

# Test 1: Array signature - get list of items FROM the reports catalog
Write-Host "`n[Test 1] getData with arrays - Get reports list"
$catalogToken = "600437df-77ae-4aca-8f93-45b022255489"
$payload1 = "7|0|10|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|com.entrinsik.gwt.data.shared.LoadOptions/4020437150|java.util.HashMap/1797211028|$catalogToken|1|2|3|4|2|5|6|5|1|7|8|6|1|9|0|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload1 -Headers $headers -ErrorAction Stop
    Write-Host "  ✓ Status: $($response.StatusCode) - Length: $($response.Content.Length) bytes"
    $response.Content | Out-File "test1_reports_list.txt" -Encoding UTF8
    Write-Host "  ✓ Saved to: test1_reports_list.txt"
    Write-Host "  Preview: $($response.Content.Substring(0, [Math]::Min(300, $response.Content.Length)))"
} catch {
    Write-Host "  ✗ Failed: $($_.Exception.Message)"
}

# Test 2: Try to get data from a SPECIFIC report ViewToken
# From the chat doc, 884e1edf-5d7c-4712-ab98-fde7ec97785e is "Inventory List"
Write-Host "`n[Test 2] Try minimal getData on specific report"
$reportToken = "884e1edf-5d7c-4712-ab98-fde7ec97785e"
$payload2 = "7|0|10|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|com.entrinsik.gwt.data.shared.LoadOptions/4020437150|java.util.HashMap/1797211028|$reportToken|1|2|3|4|2|5|6|5|1|7|8|6|1|9|0|"

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload2 -Headers $headers -ErrorAction Stop
    Write-Host "  ✓ Status: $($response.StatusCode) - Length: $($response.Content.Length) bytes"
    $response.Content | Out-File "test2_report_data.txt" -Encoding UTF8
    Write-Host "  ✓ Saved to: test2_report_data.txt"
    Write-Host "  Preview: $($response.Content.Substring(0, [Math]::Min(300, $response.Content.Length)))"
} catch {
    Write-Host "  ✗ Failed: $($_.Exception.Message)"
}

Write-Host "`n=== Complete - Check output files ==="
