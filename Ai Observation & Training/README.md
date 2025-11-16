Ai-Observation-and-Training-Recorder

Purpose

This project safely moves finalized OBS recordings from a local staging folder to Google Drive for Desktop (DriveFS), organized by date, and then optionally indexes them with Screenpipe.

Flow diagram

OBS (MKV) -> Auto-Remux (.mp4) -> obs_mover -> Google Drive\Recordings\YYYY\YYYY-MM-DD -> Screenpipe index

Acceptance criteria

1) Dropping a .mp4 in staging moves it to My Drive\Recordings\YYYY\YYYY-MM-DD in ≤60s.
2) If DriveFS isn’t mounted, script warns and keeps watching without errors.
3) If file is still writing, mover retries until lock clears (size stable + exclusive lock).
4) Screenpipe (if present) indexes the moved file via `screenpipe add <destfile>`.

Quick start

1) Open PowerShell (as your normal user)
2) Run:
   """
   .\scripts\obs_bootstrap.ps1
   """
3) In OBS, set Recording Path to "C:\Scripts\Ai Observation & Training\OBS_Staging"
4) Make a 10s test recording
5) Verify logs:
   """
   Get-Content "C:\Scripts\Logs\obs_mover.log" -Wait
   """

Commands

- Start interactive mover:
  """
  .\scripts\obs_mover.ps1
  """

- Install scheduled task (hidden, runs on logon):
  """
  .\scripts\obs_mover.ps1 -InstallTask
  """

- Uninstall scheduled task:
  """
  .\scripts\obs_mover.ps1 -UninstallTask
  """

- Run path validator (I/O probe):
  """
  .\scripts\set_obs_staging.ps1 -Path "C:\Scripts\Ai Observation & Training\OBS_Staging" -ProbeSizeMB 32
  """

- Create test file (tiny .mp4 marker):
  """
  .\scripts\test_drop.ps1
  """

Troubleshooting

- My Drive not found → Start Google Drive for Desktop and ensure your drive letter is mounted
- Files not moving → Ensure OBS Advanced → Recording → Auto-remux to MP4 is ON
- Timeouts → Large files may take time to close; the periodic sweeper will pick them up once stable
- Avoid using \\tsclient paths and never record directly to any path containing "\\My Drive\\"

Security & privacy

- All recordings are written to a local staging folder first
- Files are moved to Google Drive only after they finalize and pass stability checks

Versioning & logs

- Versioning is manual via this repository; see RELEASE_NOTES.md for changes
- Logs live at "C:\Scripts\Logs\obs_mover.log" with rotation (5MB x 5)

Build a zip artifact (exclude /scripts/Logs)

Run in the repo root:
"""
$dest = ".\Ai-Observation-and-Training-Recorder.zip"
$files = Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch "\\scripts\\Logs\\" }
Compress-Archive -Path $files.FullName -DestinationPath $dest -Force
"""


