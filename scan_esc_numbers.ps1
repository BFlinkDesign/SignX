#Requires -Version 5.1
# ESC Filename Scanner - Scans G:\ for MMYY-NNNNN-RR patterns in filenames
# Streams results to CSV to avoid memory pressure on large scans

param(
    [string]$DrivePath = "G:\",
    [string]$OutputCsv = "C:\Scripts\signx-warehouse\esc_file_index.csv",
    [int]$ProgressInterval = 500
)

$ErrorActionPreference = "SilentlyContinue"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# ESC pattern: MMYY-NNNNN-RR (RR optional)
$escRegex = [regex]'(\d{2})(\d{2})-(\d{4,5})-?(\d{2})?'

# Stats tracking (lightweight counters only)
$stats = @{
    TotalFoldersScanned = 0
    TotalFilesChecked   = 0
    TotalMatches        = 0
    UniqueEscNumbers    = [System.Collections.Generic.HashSet[string]]::new()
    QuoteNumberCounts   = [System.Collections.Generic.Dictionary[string,int]]::new()
    ExtensionCounts     = [System.Collections.Generic.Dictionary[string,int]]::new()
    CustomerHits        = [System.Collections.Generic.Dictionary[string,int]]::new()
}

# Open CSV writer (StreamWriter for performance)
$writer = [System.IO.StreamWriter]::new($OutputCsv, $false, [System.Text.Encoding]::UTF8)
$writer.WriteLine("esc_number,quote_number,date_code,month,year,revision,full_path,filename,file_extension,file_size_bytes,last_modified,customer_folder,letter_folder")

function Write-CsvRow {
    param($row)
    # Escape fields that might contain commas or quotes
    $escaped = $row | ForEach-Object {
        $val = "$_"
        if ($val -match '[,"\r\n]') {
            '"' + $val.Replace('"', '""') + '"'
        } else {
            $val
        }
    }
    $writer.WriteLine($escaped -join ',')
}

# Enumerate all top-level folders on G:
Write-Host "=== ESC Filename Scanner ===" -ForegroundColor Cyan
Write-Host "Drive: $DrivePath"
Write-Host "Output: $OutputCsv"
Write-Host "Pattern: MMYY-NNNNN-RR"
Write-Host ""

$topFolders = Get-ChildItem -Path $DrivePath -Directory -ErrorAction SilentlyContinue
Write-Host "Top-level folders: $($topFolders.Count)"

$customerFolders = [System.Collections.Generic.List[object]]::new()
foreach ($top in $topFolders) {
    $letter = $top.Name
    # Get customer-level folders (depth 1 under each top folder)
    $customers = Get-ChildItem -Path $top.FullName -Directory -ErrorAction SilentlyContinue
    foreach ($c in $customers) {
        $customerFolders.Add([PSCustomObject]@{
            Letter   = $letter
            Customer = $c.Name
            Path     = $c.FullName
        })
    }
    # Also scan files directly under top-level folders (not in customer subfolder)
    $topFiles = Get-ChildItem -Path $top.FullName -File -ErrorAction SilentlyContinue
    foreach ($f in $topFiles) {
        $stats.TotalFilesChecked++
        $m = $escRegex.Match($f.Name)
        if ($m.Success) {
            $month    = $m.Groups[1].Value
            $year     = $m.Groups[2].Value
            $quoteNum = $m.Groups[3].Value
            $rev      = if ($m.Groups[4].Success) { $m.Groups[4].Value } else { "" }
            $escFull  = "$month$year-$quoteNum$(if($rev){"-$rev"}else{''})"
            $ext      = $f.Extension.ToLower()

            Write-CsvRow @(
                $escFull, $quoteNum, "$month$year", $month, $year, $rev,
                $f.FullName, $f.Name, $ext, $f.Length,
                $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                $letter, $letter
            )

            $stats.TotalMatches++
            [void]$stats.UniqueEscNumbers.Add($escFull)

            if ($stats.QuoteNumberCounts.ContainsKey($quoteNum)) {
                $stats.QuoteNumberCounts[$quoteNum]++
            } else {
                $stats.QuoteNumberCounts[$quoteNum] = 1
            }
            if ($stats.ExtensionCounts.ContainsKey($ext)) {
                $stats.ExtensionCounts[$ext]++
            } else {
                $stats.ExtensionCounts[$ext] = 1
            }
        }
    }
}

$totalCustomers = $customerFolders.Count
Write-Host "Customer folders to scan: $totalCustomers"
Write-Host "Starting scan..." -ForegroundColor Yellow
Write-Host ""

# Scan each customer folder recursively
foreach ($cf in $customerFolders) {
    $stats.TotalFoldersScanned++

    try {
        $files = Get-ChildItem -Path $cf.Path -Recurse -File -ErrorAction SilentlyContinue
    } catch {
        continue
    }

    foreach ($f in $files) {
        $stats.TotalFilesChecked++

        $m = $escRegex.Match($f.Name)
        if (-not $m.Success) { continue }

        $month    = $m.Groups[1].Value
        $year     = $m.Groups[2].Value
        $quoteNum = $m.Groups[3].Value
        $rev      = if ($m.Groups[4].Success) { $m.Groups[4].Value } else { "" }
        $escFull  = "$month$year-$quoteNum$(if($rev){"-$rev"}else{''})"
        $ext      = $f.Extension.ToLower()

        Write-CsvRow @(
            $escFull, $quoteNum, "$month$year", $month, $year, $rev,
            $f.FullName, $f.Name, $ext, $f.Length,
            $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
            $cf.Customer, $cf.Letter
        )

        $stats.TotalMatches++
        [void]$stats.UniqueEscNumbers.Add($escFull)

        if ($stats.QuoteNumberCounts.ContainsKey($quoteNum)) {
            $stats.QuoteNumberCounts[$quoteNum]++
        } else {
            $stats.QuoteNumberCounts[$quoteNum] = 1
        }
        if ($stats.ExtensionCounts.ContainsKey($ext)) {
            $stats.ExtensionCounts[$ext]++
        } else {
            $stats.ExtensionCounts[$ext] = 1
        }
        if ($stats.CustomerHits.ContainsKey($cf.Customer)) {
            $stats.CustomerHits[$cf.Customer]++
        } else {
            $stats.CustomerHits[$cf.Customer] = 1
        }
    }

    # Progress report
    if ($stats.TotalFoldersScanned % $ProgressInterval -eq 0) {
        $pct = [math]::Round($stats.TotalFoldersScanned / $totalCustomers * 100, 1)
        $elapsed = $stopwatch.Elapsed.ToString("hh\:mm\:ss")
        $rate = [math]::Round($stats.TotalFoldersScanned / $stopwatch.Elapsed.TotalSeconds, 1)
        $eta = if ($rate -gt 0) {
            $remaining = ($totalCustomers - $stats.TotalFoldersScanned) / $rate
            [TimeSpan]::FromSeconds($remaining).ToString("hh\:mm\:ss")
        } else { "??:??:??" }
        Write-Host "  [$elapsed] $($stats.TotalFoldersScanned)/$totalCustomers folders ($pct%) | $($stats.TotalFilesChecked) files checked | $($stats.TotalMatches) matches | ETA: $eta" -ForegroundColor DarkGray
        $writer.Flush()
    }
}

$writer.Flush()
$writer.Close()
$stopwatch.Stop()

# === SUMMARY ===
Write-Host ""
Write-Host "=== SCAN COMPLETE ===" -ForegroundColor Green
Write-Host "Elapsed: $($stopwatch.Elapsed.ToString('hh\:mm\:ss'))"
Write-Host ""
Write-Host "--- Totals ---"
Write-Host "  Folders scanned:    $($stats.TotalFoldersScanned)"
Write-Host "  Files checked:      $($stats.TotalFilesChecked)"
Write-Host "  Files indexed:      $($stats.TotalMatches)"
Write-Host "  Unique ESC numbers: $($stats.UniqueEscNumbers.Count)"
Write-Host "  Unique quote nums:  $($stats.QuoteNumberCounts.Count)"
Write-Host ""

Write-Host "--- Top 20 Quote Numbers by File Count ---"
$stats.QuoteNumberCounts.GetEnumerator() |
    Sort-Object Value -Descending |
    Select-Object -First 20 |
    ForEach-Object { Write-Host ("  {0}: {1} files" -f $_.Key, $_.Value) }
Write-Host ""

Write-Host "--- File Type Distribution ---"
$stats.ExtensionCounts.GetEnumerator() |
    Sort-Object Value -Descending |
    Select-Object -First 20 |
    ForEach-Object { Write-Host ("  {0}: {1}" -f $_.Key, $_.Value) }
Write-Host ""

Write-Host "--- Top 20 Customers by Indexed Files ---"
$stats.CustomerHits.GetEnumerator() |
    Sort-Object Value -Descending |
    Select-Object -First 20 |
    ForEach-Object { Write-Host ("  {0}: {1} files" -f $_.Key, $_.Value) }
Write-Host ""

Write-Host "Output: $OutputCsv"
$csvSize = (Get-Item $OutputCsv).Length / 1MB
Write-Host "CSV size: $([math]::Round($csvSize, 2)) MB"
