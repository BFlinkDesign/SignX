param(
	[string]$Path = ".env",
	[switch]$PersistUser = $false
)

function Set-EnvVar {
	param(
		[string]$Name,
		[string]$Value
	)
	if ([string]::IsNullOrWhiteSpace($Name)) { return }
	# Set for current process
	$env:$Name = $Value
	if ($PersistUser) {
		setx $Name $Value | Out-Null
	}
}

if (-not (Test-Path -LiteralPath $Path)) {
	Write-Output "No .env found at '$Path' - skipping."
	exit 0
}

Get-Content -LiteralPath $Path | ForEach-Object {
	$line = $_.Trim()
	if ($line.Length -eq 0) { return }
	if ($line.StartsWith("#")) { return }
	# Split on first '='
	$idx = $line.IndexOf("=")
	if ($idx -lt 1) { return }
	$key = $line.Substring(0, $idx).Trim()
	$val = $line.Substring($idx + 1).Trim()
	# Remove surrounding quotes if present
	if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
		$val = $val.Substring(1, $val.Length - 2)
	}
	Set-EnvVar -Name $key -Value $val
}

Write-Output "Loaded environment variables from '$Path'. PersistUser=$PersistUser"

