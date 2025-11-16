Param(
    [string]$ConfigPath = "ops/agents/config.yaml",
    [int]$Workers = 0,
    [switch]$NoSwarm
)

$ErrorActionPreference = "Stop"

Write-Host "== SignX Multi-Agent Audit ==" -ForegroundColor Cyan

# Activate local ops venv if present
$venv = ".\.venv_ops\Scripts\Activate.ps1"
if (Test-Path $venv) {
    Write-Host "Activating .venv_ops..." -ForegroundColor DarkGray
    . $venv
} else {
    Write-Host "No .venv_ops found. Continuing with system Python..." -ForegroundColor DarkYellow
}

# Ensure reports dir
if (-not (Test-Path "ops\reports")) {
    New-Item -ItemType Directory -Path "ops\reports" | Out-Null
}

# Run orchestrator
$argsList = @("full", "--config", $ConfigPath)
if ($Workers -gt 0) { $argsList += @("--workers", "$Workers") }
if ($NoSwarm.IsPresent) { $argsList += @("--no-swarm") }
python -m ops.agents.orchestrator @argsList

Write-Host "Reports available under ops/reports" -ForegroundColor Green


