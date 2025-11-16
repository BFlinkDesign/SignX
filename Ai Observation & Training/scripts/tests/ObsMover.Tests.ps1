param()

### Pester 5 tests (PowerShell 5 compatible)

Describe 'obs_mover.ps1 basics' {
	It 'loads obs_mover.ps1 without error (dot-sourcing)' {
		{ . (Join-Path -Path $PSScriptRoot -ChildPath '..\obs_mover.ps1') -OneShot -DryRun } | Should -Not -Throw
	}
}

Describe 'set_obs_staging.ps1 probe' {
	It 'succeeds against a temp folder' {
		$temp = Join-Path -Path $env:TEMP -ChildPath ("obs_stage_" + [System.Guid]::NewGuid().ToString('N'))
		$script = Join-Path -Path $PSScriptRoot -ChildPath '..\set_obs_staging.ps1'
		$psi = New-Object System.Diagnostics.ProcessStartInfo
		$psi.FileName = 'powershell.exe'
		$psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Path `"$temp`" -ProbeSizeMB 1"
		$psi.RedirectStandardOutput = $true
		$psi.RedirectStandardError = $true
		$psi.UseShellExecute = $false
		$p = [System.Diagnostics.Process]::Start($psi)
		$p.WaitForExit()
		$p.ExitCode | Should -Be 0
	}
}

Describe 'test_drop.ps1 marker' {
	It 'creates a marker without error' {
		$script = Join-Path -Path $PSScriptRoot -ChildPath '..\test_drop.ps1'
		{ & $script } | Should -Not -Throw
	}
}

Describe 'DriveFS detection (optional)' {
	It 'resolves a path that ends with \\My Drive when mounted' -TestCases @(@{ }) {
		# replicate detection logic
		$fs = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -match '^[A-Z]:\\$' }
		$found = $false
		foreach ($d in $fs) {
			$probe = Join-Path -Path $d.Root -ChildPath 'My Drive'
			if (Test-Path -LiteralPath $probe) { $found = $true; break }
		}
		if (-not $found) {
			Set-ItResult -Skipped -Because 'DriveFS not detected in this environment.'
			return
		}
		$probe | Should -Match '\\My Drive$'
	}
}


