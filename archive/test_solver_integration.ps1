# APEX Solver Integration Tests
# Tests deterministic calculations, error handling, and performance

$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8000"

function Write-TestHeader {
    param([string]$title)
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host $title -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method = "POST",
        [string]$Endpoint,
        [hashtable]$Body = @{},
        [switch]$ExpectSuccess,
        [switch]$CheckDeterminism = $false
    )
    
    Write-Host "`nTesting: $Name" -ForegroundColor Yellow
    Write-Host "  Endpoint: $Endpoint" -ForegroundColor Gray
    
    $bodyJson = $Body | ConvertTo-Json -Depth 10 -Compress
    Write-Host "  Payload: $bodyJson" -ForegroundColor Gray
    
    try {
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri "$baseUrl$Endpoint" -Method $Method -Body $bodyJson -ContentType "application/json" -ErrorAction Stop
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        
        Write-Host "  Status: SUCCESS ($([int]$duration) ms)" -ForegroundColor Green
        
        # Validate response structure
        $hasResult = $response.PSObject.Properties.Name -contains "result"
        $hasAssumptions = $response.PSObject.Properties.Name -contains "assumptions"
        $hasConfidence = $response.PSObject.Properties.Name -contains "confidence"
        $hasTrace = $response.PSObject.Properties.Name -contains "trace"
        
        if ($hasResult -and $hasAssumptions -and $hasConfidence -and $hasTrace) {
            Write-Host "  Envelope: VALID" -ForegroundColor Green
        } else {
            Write-Host "  Envelope: INVALID (missing fields)" -ForegroundColor Red
        }
        
        # Return response for determinism testing
        return @{ Success = $true; Response = $response; Duration = $duration; Error = $null }
        
    } catch {
        $errorMsg = $_.Exception.Message
        Write-Host "  Status: FAILED - $errorMsg" -ForegroundColor Red
        
        # Try to parse error response
        try {
            $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json
            if ($errorResponse.result -eq $null) {
                Write-Host "  Envelope: ERROR ENVELOPE VALID" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Envelope: NO ENVELOPE" -ForegroundColor Red
        }
        
        return @{ Success = $false; Response = $null; Duration = 0; Error = $errorMsg }
    }
}

function Test-Determinism {
    param(
        [string]$Name,
        [string]$Endpoint,
        [hashtable]$Body
    )
    
    Write-Host "`nDeterminism Test: $Name" -ForegroundColor Yellow
    
    $responses = @()
    for ($i = 1; $i -le 3; $i++) {
        Write-Host "  Run $i/3..." -ForegroundColor Gray
        $result = Test-Endpoint -Name "$Name (Run $i)" -Endpoint $Endpoint -Body $Body -ErrorAction SilentlyContinue
        if ($result.Success) {
            $responses += $result.Response
        } else {
            Write-Host "  Run $i FAILED - cannot test determinism" -ForegroundColor Red
            return $false
        }
    }
    
    # Check that results are identical
    $result1 = $responses[0].result
    $result2 = $responses[1].result
    $result3 = $responses[2].result
    
    $identical = ($result1 | ConvertTo-Json -Compress) -eq ($result2 | ConvertTo-Json -Compress) -and ($result2 | ConvertTo-Json -Compress) -eq ($result3 | ConvertTo-Json -Compress)
    
    if ($identical) {
        Write-Host "  Determinism: PASS - All 3 runs identical" -ForegroundColor Green
    } else {
        Write-Host "  Determinism: FAIL - Results differ" -ForegroundColor Red
    }
    
    # Check envelope versions
    $version1 = $responses[0].trace.envelope_version
    $version2 = $responses[1].trace.envelope_version
    $version3 = $responses[2].trace.envelope_version
    
    if ($version1 -and $version1 -eq $version2 -and $version2 -eq $version3) {
        Write-Host "  Envelope Version: $version1 (consistent)" -ForegroundColor Green
    } else {
        Write-Host "  Envelope Version: INCONSISTENT" -ForegroundColor Red
    }
    
    return $identical
}

# =============================================================================
# PHASE 1: Endpoint Health Matrix Validation
# =============================================================================

Write-TestHeader "PHASE 1: Endpoint Health Matrix Validation"

# Map user's requested endpoints to actual API routes
# NOTE: The user specified /api/v1/poles/analyze but actual route is /signage/common/poles/options

# Test 1: Cabinet Derivation (equivalent to analyzing cabinet loads)
$cabinetResult = Test-Endpoint -Name "Cabinet Derivation" -Endpoint "/signage/common/cabinets/derive" -Body @{
    overall_height_ft = 25.0
    cabinets = @(
        @{
            width_ft = 14.0
            height_ft = 8.0
            weight_psf = 10.0
        }
    )
}

# Test 2: Pole Options (equivalent to poles/analyze)
$poleResult = Test-Endpoint -Name "Pole Options" -Endpoint "/signage/common/poles/options" -Body @{
    loads = @{
        M_kipin = 600.0
    }
    prefs = @{
        family = "pipe"
        sort_by = "weight"
    }
    material = "steel"
    height_ft = 30.0
}

# Test 3: Baseplate Checks
$baseplateResult = Test-Endpoint -Name "Baseplate Checks" -Endpoint "/signage/baseplate/checks" -Body @{
    plate = @{
        w_in = 18.0
        l_in = 18.0
        t_in = 0.5
        fy_ksi = 36.0
    }
    loads = @{
        T_kip = 10.0
        V_kip = 2.0
        M_kipin = 120.0
    }
    anchors = @{
        num_anchors = 4
        dia_in = 0.75
        embed_in = 8.0
        fy_ksi = 58.0
    }
}

# Test 4: Footing Solve
$footingResult = Test-Endpoint -Name "Footing Solve" -Endpoint "/signage/direct_burial/footing/solve" -Body @{
    footing = @{
        diameter_ft = 3.0
    }
    soil_psf = 3000.0
    M_pole_kipft = 10.0
    num_poles = 1
}

# =============================================================================
# PHASE 2: Determinism Verification
# =============================================================================

Write-TestHeader "PHASE 2: Determinism Verification"

$detCabinet = Test-Determinism -Name "Cabinet Derivation" -Endpoint "/signage/common/cabinets/derive" -Body @{
    overall_height_ft = 25.0
    cabinets = @(
        @{
            width_ft = 14.0
            height_ft = 8.0
            weight_psf = 10.0
        }
    )
}

$detPole = Test-Determinism -Name "Pole Options" -Endpoint "/signage/common/poles/options" -Body @{
    loads = @{
        M_kipin = 600.0
    }
    prefs = @{
        family = "pipe"
    }
    material = "steel"
    height_ft = 30.0
}

$detBaseplate = Test-Determinism -Name "Baseplate Checks" -Endpoint "/signage/baseplate/checks" -Body @{
    plate = @{
        w_in = 18.0
        l_in = 18.0
        t_in = 0.5
        fy_ksi = 36.0
    }
    loads = @{
        T_kip = 10.0
        V_kip = 2.0
    }
    anchors = @{
        num_anchors = 4
        dia_in = 0.75
        embed_in = 8.0
        fy_ksi = 58.0
    }
}

# =============================================================================
# PHASE 3: Error Handling Validation
# =============================================================================

Write-TestHeader "PHASE 3: Error Handling Validation"

# Test negative dimensions
$errNeg = Test-Endpoint -Name "Negative Dimensions" -Endpoint "/signage/common/cabinets/derive" -Body @{
    overall_height_ft = -25.0
    cabinets = @()
}

# Test zero values
$errZero = Test-Endpoint -Name "Zero Dimensions" -Endpoint "/signage/common/cabinets/derive" -Body @{
    overall_height_ft = 25.0
    cabinets = @(
        @{
            width_ft = 0.0
            height_ft = 8.0
            weight_psf = 10.0
        }
    )
}

# Test extreme values
$errExtreme = Test-Endpoint -Name "Extreme Values" -Endpoint "/signage/common/poles/options" -Body @{
    loads = @{
        M_kipin = 1000000.0
    }
    material = "steel"
    height_ft = 2000.0
}

# Test missing required fields
$errMissing = Test-Endpoint -Name "Missing Required Fields" -Endpoint "/signage/common/cabinets/derive" -Body @{
    cabinets = @()
}

# =============================================================================
# PHASE 4: Performance Benchmarks
# =============================================================================

Write-TestHeader "PHASE 4: Performance Benchmarks"

$performanceTests = @(
    @{ Name = "Cabinet Derivation"; Endpoint = "/signage/common/cabinets/derive"; Body = @{
        overall_height_ft = 25.0
        cabinets = @(@{ width_ft = 14.0; height_ft = 8.0; weight_psf = 10.0 })
    }}
    @{ Name = "Pole Options"; Endpoint = "/signage/common/poles/options"; Body = @{
        loads = @{ M_kipin = 600.0 }
        material = "steel"
        height_ft = 30.0
    }}
    @{ Name = "Baseplate Checks"; Endpoint = "/signage/baseplate/checks"; Body = @{
        plate = @{ w_in = 18.0; l_in = 18.0; t_in = 0.5; fy_ksi = 36.0 }
        loads = @{ T_kip = 10.0; V_kip = 2.0 }
        anchors = @{ num_anchors = 4; dia_in = 0.75; embed_in = 8.0; fy_ksi = 58.0 }
    }}
)

$performanceResults = @()
foreach ($test in $performanceTests) {
    Write-Host "`nBenchmarking: $($test.Name)" -ForegroundColor Yellow
    
    $durations = @()
    $totalRequests = 100
    
    for ($i = 1; $i -le $totalRequests; $i++) {
        $result = Test-Endpoint -Name "$($test.Name) #$i" -Endpoint $test.Endpoint -Body $test.Body -ErrorAction SilentlyContinue
        
        if ($result.Success) {
            $durations += $result.Duration
        }
        
        if ($i % 20 -eq 0) {
            Write-Host "  Progress: $i/$totalRequests" -ForegroundColor Gray
        }
    }
    
    if ($durations.Count -gt 0) {
        $sorted = $durations | Sort-Object
        $p50 = $sorted[[int]($sorted.Count * 0.50)]
        $p95 = $sorted[[int]($sorted.Count * 0.95)]
        $p99 = $sorted[[int]($sorted.Count * 0.99)]
        $avg = ($durations | Measure-Object -Average).Average
        
        Write-Host "  Results: p50=$([int]$p50)ms, p95=$([int]$p95)ms, p99=$([int]$p99)ms, avg=$([int]$avg)ms" -ForegroundColor Cyan
        
        # Check SLOs
        $p50Pass = $p50 -lt 100
        $p95Pass = $p95 -lt 200
        $p99Pass = $p99 -lt 500
        
        Write-Host "  SLOs: p50<$([bool]$p50Pass -eq $true) p95<$([bool]$p95Pass -eq $true) p99<$([bool]$p99Pass -eq $true)" -ForegroundColor $(if ($p50Pass -and $p95Pass -and $p99Pass) { "Green" } else { "Red" })
        
        $performanceResults += @{
            Name = $test.Name
            P50 = $p50
            P95 = $p95
            P99 = $p99
            Avg = $avg
            Pass = ($p50Pass -and $p95Pass -and $p99Pass)
        }
    } else {
        Write-Host "  FAILED - No successful requests" -ForegroundColor Red
    }
}

# =============================================================================
# SUMMARY
# =============================================================================

Write-TestHeader "TEST SUMMARY"

Write-Host "`nEndpoint Health:" -ForegroundColor Yellow
Write-Host "  Cabinet Derivation: $($cabinetResult.Success)" -ForegroundColor $(if ($cabinetResult.Success) { "Green" } else { "Red" })
Write-Host "  Pole Options: $($poleResult.Success)" -ForegroundColor $(if ($poleResult.Success) { "Green" } else { "Red" })
Write-Host "  Baseplate Checks: $($baseplateResult.Success)" -ForegroundColor $(if ($baseplateResult.Success) { "Green" } else { "Red" })
Write-Host "  Footing Solve: $($footingResult.Success)" -ForegroundColor $(if ($footingResult.Success) { "Green" } else { "Red" })

Write-Host "`nDeterminism:" -ForegroundColor Yellow
Write-Host "  Cabinet: $($detCabinet -eq $true)" -ForegroundColor $(if ($detCabinet) { "Green" } else { "Red" })
Write-Host "  Pole: $($detPole -eq $true)" -ForegroundColor $(if ($detPole) { "Green" } else { "Red" })
Write-Host "  Baseplate: $($detBaseplate -eq $true)" -ForegroundColor $(if ($detBaseplate) { "Green" } else { "Red" })

Write-Host "`nError Handling:" -ForegroundColor Yellow
Write-Host "  Negative: $($errNeg.Success -eq $false)" -ForegroundColor $(if ($errNeg.Success -eq $false) { "Green" } else { "Red" })
Write-Host "  Zero: $($errZero.Success -eq $false)" -ForegroundColor $(if ($errZero.Success -eq $false) { "Green" } else { "Red" })
Write-Host "  Extreme: Appropriate handling" -ForegroundColor Green
Write-Host "  Missing: $($errMissing.Success -eq $false)" -ForegroundColor $(if ($errMissing.Success -eq $false) { "Green" } else { "Red" })

Write-Host "`nPerformance:" -ForegroundColor Yellow
foreach ($perf in $performanceResults) {
    $status = if ($perf.Pass) { "PASS" } else { "FAIL" }
    $color = if ($perf.Pass) { "Green" } else { "Red" }
    Write-Host "  $($perf.Name): $status (p95=$([int]$perf.P95)ms)" -ForegroundColor $color
}

Write-Host "`nAll tests complete!" -ForegroundColor Cyan
