# SignX Studio Rebrand Script
# Renames Leo Ai Clone -> SignX-Studio and updates all references

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SignX Studio Rebrand Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$oldFolder = "Leo Ai Clone"
$newFolder = "SignX-Studio"
$oldBrand = "CalcuSign APEX"
$newBrand = "SIGN X Studio"
$oldDbName = "calcusign_apex"
$newDbName = "signx_studio"

# Track changes
$changesSummary = @()

# Step 1: Find and replace in all Python files
Write-Host "[1/4] Updating Python files..." -ForegroundColor Yellow

$pythonFiles = Get-ChildItem -Path ".\$oldFolder" -Filter "*.py" -Recurse -File
$pythonCount = 0

foreach ($file in $pythonFiles) {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    $originalContent = $content

    # Replace brand names
    $content = $content -replace [regex]::Escape($oldBrand), $newBrand

    # Replace database names
    $content = $content -replace [regex]::Escape($oldDbName), $newDbName

    if ($content -ne $originalContent) {
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
        $pythonCount++
        Write-Host "  [OK] Updated: $($file.Name)" -ForegroundColor Green
    }
}

$changesSummary += "Python files updated: $pythonCount"

# Step 2: Update Markdown files
Write-Host ""
Write-Host "[2/4] Updating Markdown files..." -ForegroundColor Yellow

$markdownFiles = Get-ChildItem -Path ".\$oldFolder" -Filter "*.md" -Recurse -File
$mdCount = 0

foreach ($file in $markdownFiles) {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    $originalContent = $content

    $content = $content -replace [regex]::Escape($oldBrand), $newBrand
    $content = $content -replace [regex]::Escape($oldDbName), $newDbName

    if ($content -ne $originalContent) {
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
        $mdCount++
        Write-Host "  [OK] Updated: $($file.Name)" -ForegroundColor Green
    }
}

$changesSummary += "Markdown files updated: $mdCount"

# Step 3: Update YAML/config files
Write-Host ""
Write-Host "[3/4] Updating YAML and config files..." -ForegroundColor Yellow

$configFiles = Get-ChildItem -Path ".\$oldFolder" -Include @("*.yaml", "*.yml", "*.json", "*.env.example", "*.toml") -Recurse -File
$configCount = 0

foreach ($file in $configFiles) {
    try {
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        $originalContent = $content

        $content = $content -replace [regex]::Escape($oldBrand), $newBrand
        $content = $content -replace [regex]::Escape($oldDbName), $newDbName

        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
            $configCount++
            Write-Host "  [OK] Updated: $($file.Name)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [SKIP] Skipped: $($file.Name) (binary or locked)" -ForegroundColor DarkYellow
    }
}

$changesSummary += "Config files updated: $configCount"

# Step 4: Rename folder
Write-Host ""
Write-Host "[4/4] Renaming folder..." -ForegroundColor Yellow

if (Test-Path ".\$newFolder") {
    Write-Host "  [WARN] Warning: Folder '$newFolder' already exists!" -ForegroundColor Red
    Write-Host "  Skipping folder rename." -ForegroundColor Red
    $changesSummary += "Folder rename: SKIPPED (target exists)"
} else {
    Rename-Item -Path ".\$oldFolder" -NewName $newFolder
    Write-Host "  [OK] Renamed: $oldFolder -> $newFolder" -ForegroundColor Green
    $changesSummary += "Folder renamed: $oldFolder -> $newFolder"
}

# Step 5: Git commit (if git repo exists)
Write-Host ""
Write-Host "[5/5] Git commit..." -ForegroundColor Yellow

$gitPath = ".\$newFolder\.git"
if (-not (Test-Path $gitPath)) {
    # Initialize git if not exists
    Write-Host "  Initializing git repository..." -ForegroundColor Cyan
    Set-Location ".\$newFolder"
    git init 2>&1 | Out-Null
    git add . 2>&1 | Out-Null
    git commit -m "Initial commit: SignX Studio rebrand from CalcuSign APEX" 2>&1 | Out-Null
    Set-Location ..
    Write-Host "  [OK] Git initialized and committed" -ForegroundColor Green
    $changesSummary += "Git: Repository initialized"
} else {
    Write-Host "  Git repository already exists" -ForegroundColor DarkGray
    $changesSummary += "Git: Already initialized"
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Rebrand Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

foreach ($change in $changesSummary) {
    Write-Host "  * $change" -ForegroundColor White
}

Write-Host ""
Write-Host "[SUCCESS] Rebrand complete!" -ForegroundColor Green
Write-Host ""
