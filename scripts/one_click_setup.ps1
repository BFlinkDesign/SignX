param(
	[string]$DotEnvPath = ".env",
	[switch]$PersistEnv = $true,
	[switch]$InstallExtensions = $true,
	[switch]$InstallRobot = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Header($text) { Write-Host "=== $text ===" -ForegroundColor Cyan }
function Exec($cmd) {
	Write-Host "> $cmd" -ForegroundColor DarkGray
	Invoke-Expression $cmd
}

Write-Header "Loading .env (PersistEnv=$PersistEnv)"
& "$PSScriptRoot\\load_dotenv.ps1" -Path $DotEnvPath -PersistUser:$PersistEnv

Write-Header "Ensuring Python venv"
$pyList = & py -0p 2>$null
if (-not $pyList) {
	throw "No Python registered with 'py' launcher. Please install Python 3.11+."
}
# Choose highest version
$pyExe = ($pyList -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Last 1)
Write-Host "Using Python: $pyExe"

if (-not (Test-Path -LiteralPath ".venv")) {
	Exec "py -3 -m venv .venv"
}

$venvPython = ".\\.venv\\Scripts\\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
	throw "Virtual environment python not found at $venvPython"
}

Exec "$venvPython -m pip install -U pip"
if ($InstallRobot) {
	Write-Header "Installing Robot Framework toolchain"
	Exec "$venvPython -m pip install -U robotframework robotframework-lsp robotframework-robocop robotframework-tidy debugpy"
	Exec ".\\.venv\\Scripts\\robot.exe --version"
}

if ($InstallExtensions) {
	Write-Header "Installing VS Code recommended extensions"
	$extsJson = ".vscode\\extensions.json"
	if (Test-Path -LiteralPath $extsJson) {
		$exts = (Get-Content -Raw -LiteralPath $extsJson | ConvertFrom-Json).recommendations
		foreach ($ext in $exts) {
			try {
				Exec "code --install-extension $ext --force"
			} catch {
				Write-Warning "Failed to install extension $ext: $_"
			}
		}
	} else {
		Write-Warning "No .vscode/extensions.json found; skipping extension install."
	}
}

Write-Header "Validating Java for RSP/SonarLint"
try {
	Exec "java -version"
} catch {
	Write-Warning "Java not found on PATH. Ensure JDK 17+ is installed and JAVA_HOME is set."
}

Write-Header "Summary"
Write-Host "SONAR_SERVER_URL=$($env:SONAR_SERVER_URL)"
Write-Host "SONAR_PROJECT_KEY=$($env:SONAR_PROJECT_KEY)"
Write-Host "SONAR_TOKEN set? " -NoNewline
Write-Host ([string]::IsNullOrWhiteSpace($env:SONAR_TOKEN) ? "NO" : "YES") -ForegroundColor ([string]::IsNullOrWhiteSpace($env:SONAR_TOKEN) ? "Red" : "Green")
Write-Host ""
Write-Host "Done. Restart VS Code to ensure environment changes are picked up, then:"
Write-Host " - Ctrl+Shift+P → Developer: Reload Window"
Write-Host " - Check Output: SonarLint, RSP connectors"

