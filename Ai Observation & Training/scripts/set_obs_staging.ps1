[CmdletBinding()]
param(
	[string]$Path = "C:\Scripts\Ai Observation & Training\OBS_Staging",
	[int]$ProbeSizeMB = 32
)

set-strictmode -version latest
$ErrorActionPreference = 'Stop'

function Is-ForbiddenPath([string]$p) {
	if (-not $p) { return $true }
	$lower = $p.ToLowerInvariant()
	if ($lower.StartsWith('\\\\tsclient\\')) { return $true }
	if ($lower -like '*\\my drive\\*') { return $true }
	return $false
}

try {
	if (Is-ForbiddenPath $Path) {
		Write-Error "Forbidden path: '$Path' (rejecting \\tsclient and any path containing \\My Drive\\)"
		exit 1
	}
	if (-not (Test-Path -LiteralPath $Path)) {
		New-Item -ItemType Directory -Path $Path -Force | Out-Null
	}
	$bytesToWrite = [int64]$ProbeSizeMB * 1MB
	$temp = [System.IO.Path]::Combine($Path, ([System.IO.Path]::GetRandomFileName() + '.tmp'))
	$probe = [System.IO.Path]::ChangeExtension($temp, '.probe')
	$sw = [System.Diagnostics.Stopwatch]::StartNew()
	$bufSize = 1048576 # 1MB
	$buffer = New-Object byte[] $bufSize
	[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
	$fs = New-Object System.IO.FileStream($temp, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 4096, [System.IO.FileOptions]::WriteThrough)
	try {
		$remaining = $bytesToWrite
		while ($remaining -gt 0) {
			$chunk = [int][Math]::Min($bufSize, $remaining)
			$fs.Write($buffer, 0, $chunk)
			$remaining -= $chunk
		}
		$fs.Flush(true)
	} finally {
		$fs.Dispose()
	}
	Rename-Item -LiteralPath $temp -NewName ([System.IO.Path]::GetFileName($probe)) -Force
	Remove-Item -LiteralPath $probe -Force
	$sw.Stop()
	$mbps = [Math]::Round(($ProbeSizeMB / [Math]::Max(0.001, $sw.Elapsed.TotalSeconds)), 2)
	Write-Host "Wrote $ProbeSizeMB MB in $([Math]::Round($sw.Elapsed.TotalSeconds,2)) s => $mbps MB/s"
	Write-Host "OK"
	exit 0
} catch {
	Write-Error "Validation failed: $($_.Exception.Message)"
	exit 2
}


