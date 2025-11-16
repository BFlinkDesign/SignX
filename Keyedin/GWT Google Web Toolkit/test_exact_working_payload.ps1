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

Write-Host "`n=== Using EXACT working payload from original chat ==="

# This is the EXACT payload that worked in the original reverse engineering
# It searches the reports catalog (ViewToken 600437df...) with wildcard search
$catalogToken = "600437df-77ae-4aca-8f93-45b022255489"

$payload = "7|0|22|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|327E0F303D0CA463050DC31340CFE01D|com.entrinsik.informer.core.client.service.ViewRPCService|getData|[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|com.entrinsik.gwt.data.shared.ViewToken/3777265110|$catalogToken|com.entrinsik.gwt.data.shared.LoadOptions/4020437150|java.util.HashMap/1797211028|com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl/346417575|java.util.ArrayList/4159755760|com.entrinsik.gwt.data.shared.criteria.Operator/2483661797|com.entrinsik.gwt.data.shared.criteria.impl.ValueExpressionImpl/3874770769|name|com.entrinsik.gwt.data.shared.criteria.Quantifier/3325804167|com.entrinsik.gwt.data.shared.values.StringValue/2414534542|**|com.entrinsik.informer.core.domain.report.ReportSearchOptions/1133289605|en_US|com.entrinsik.gwt.data.shared.Order/1651361273|com.entrinsik.gwt.data.shared.values.NullValue/2880996259|1|2|3|4|2|5|6|5|1|7|8|6|1|9|10|0|11|12|2|11|12|1|11|12|0|13|9|13|8|14|1|13|2|15|16|0|17|18|-13|0|19|12|0|0|0|0|0|25|20|12|1|21|1|15|1|0|22|0|0|"

Write-Host "Sending discovery payload (searches for reports with wildcard **)..."

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $payload -Headers $headers -ErrorAction Stop
    Write-Host "   Status: $($response.StatusCode)"
    Write-Host "   Length: $($response.Content.Length) bytes"
    
    $response.Content | Out-File "working_discovery.txt" -Encoding UTF8
    Write-Host "   Saved to: working_discovery.txt"
    
    # Parse response to count reports
    if ($response.Content -like "*//OK*") {
        Write-Host "   SUCCESS - Response contains data!"
        $reportCount = ([regex]::Matches($response.Content, "Report/")).Count
        Write-Host "   Found approximately $reportCount report references"
    }
    
    Write-Host "`n  First 500 chars:"
    Write-Host "  $($response.Content.Substring(0, [Math]::Min(500, $response.Content.Length)))"
    
} catch {
    Write-Host "   Error: $($_.Exception.Message)"
}

Write-Host "`n=== Complete ==="
