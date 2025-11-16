param([Parameter(Mandatory=$true)][string]$JsonPath)
Set-StrictMode -Version Latest; $ErrorActionPreference = "Stop"
if(-not (Test-Path $JsonPath)){ throw "Not found: $JsonPath" }
$Root = Split-Path -Parent $JsonPath
$Log  = Join-Path $Root "run.log"
"== START $(Get-Date -Format s)" | Out-File $Log -Encoding UTF8
$j = Get-Content $JsonPath -Raw | ConvertFrom-Json

# Write files
foreach($f in $j.files){
  $p = Join-Path $Root $f.path
  $d = Split-Path -Parent $p
  if($d -and -not (Test-Path $d)){ New-Item -ItemType Directory -Path $d -Force | Out-Null }
  Set-Content -Path $p -Value $f.content -Encoding UTF8
  "WROTE: $p" | Out-File $Log -Append -Encoding UTF8
}

function Run-Block([string]$name,[string[]]$cmds){
  if(-not $cmds){ return }
  "== $name ==" | Out-File $Log -Append -Encoding UTF8
  foreach($c in $cmds){
    "> $c" | Out-File $Log -Append -Encoding UTF8
    $p = Start-Process pwsh -ArgumentList "-NoLogo -NoProfile -Command `"$c`"" -Wait -PassThru -NoNewWindow
    if($p.ExitCode -ne 0){
      "EXIT $($p.ExitCode) at: $c" | Out-File $Log -Append -Encoding UTF8
      throw "$name failed: $c (exit $($p.ExitCode)). See run.log."
    }
  }
}

Run-Block "INSTALL"   $j.commands.install
Run-Block "PREFLIGHT" $j.commands.preflight
Run-Block "SMOKE"     $j.commands.smoke
Run-Block "TEST"      $j.commands.test
"== PASS $(Get-Date -Format s)" | Out-File $Log -Append -Encoding UTF8
Write-Host " All good. See run.log"
