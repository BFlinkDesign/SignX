# Leo AI Clone - Professional Cleanup
# Apple-style: Radical simplicity + Clear results

param([switch]$DryRun)

$root = "C:\Scripts\Leo Ai Clone"
Set-Location $root

Write-Host "`n🧹 Leo AI Clone Cleanup" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

# 1. Archive old iteration docs
$archiveDocs = @(
    "AGENT2_*.md", "AGENT3_*.md", "AGENT_5_*.md",
    "*_COMPLETE.md", "*_SUMMARY.md", "SESSION_*.md",
    "*_STATUS.md", "IMPLEMENTATION_*.md", "REFACTORING_*.md",
    "DEPLOYMENT*.md", "FINAL_*.md", "*READY.md"
)

if (-not (Test-Path "archive")) { New-Item -ItemType Directory "archive" | Out-Null }

$archived = 0
foreach ($pattern in $archiveDocs) {
    Get-ChildItem -Filter $pattern | ForEach-Object {
        if ($_.Name -notmatch "^(README|STATUS)\.md$") {
            if ($DryRun) {
                Write-Host "  → Would archive: $($_.Name)" -ForegroundColor Yellow
            } else {
                Move-Item $_.FullName "archive\" -Force
                Write-Host "  ✓ Archived: $($_.Name)" -ForegroundColor Green
            }
            $archived++
        }
    }
}

# 2. Remove build artifacts & caches
$junk = @(
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".next", "dist", "build", ".venv", "venv",
    "*.pyc", "*.pyo", ".coverage", "coverage", ".tox"
)

$cleaned = 0
$freedMB = 0

foreach ($item in $junk) {
    Get-ChildItem -Recurse -Force -Filter $item -ErrorAction SilentlyContinue | ForEach-Object {
        $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | 
                 Measure-Object -Property Length -Sum).Sum / 1MB
        
        if ($DryRun) {
            Write-Host "  → Would delete: $($_.FullName) ($([math]::Round($size, 2)) MB)" -ForegroundColor Yellow
        } else {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Deleted: $($_.Name) ($([math]::Round($size, 2)) MB)" -ForegroundColor Green
            $freedMB += $size
        }
        $cleaned++
    }
}

# 3. Git ignored files
if (Test-Path ".git") {
    Write-Host "`n📦 Git ignored files:" -ForegroundColor Cyan
    if ($DryRun) {
        git clean -Xdn
    } else {
        git clean -Xdf
    }
}

# 4. Summary
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "  • $archived documentation files archived"
Write-Host "  • $cleaned cache/build items removed"
if (-not $DryRun) {
    Write-Host "  • $([math]::Round($freedMB, 2)) MB freed"
}
Write-Host "`n✨ Done!`n" -ForegroundColor Green

if ($DryRun) {
    Write-Host "⚠️  Dry run complete. Run without -DryRun to execute." -ForegroundColor Yellow
}
