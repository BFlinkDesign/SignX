Ai-Observation-and-Training-Recorder – Release Notes

Features

- Safe mover for finalized OBS recordings from local staging to Google Drive (DriveFS)
- Auto-detection of DriveFS letter by scanning for "My Drive"
- Event-driven watcher (Created/Renamed) plus periodic sweeper
- Hardened file stability check (size stable + exclusive lock)
- Move with retries, then copy+delete fallback
- Date-based archive structure: Recordings\YYYY\YYYY-MM-DD
- Logging to "C:\Scripts\Logs\obs_mover.log" with rotation (5MB x 5)
- Screenpipe indexing after successful move when available
- Bootstrap script to set up folders, install Screenpipe, sweep once, and install scheduled task
- Helper scripts for staging validation and test marker creation
- Minimal Pester tests

Known limitations / risks

- DriveFS path detection depends on a visible "My Drive" root; non-standard Google Drive setups may require manual -ArchiveRoot
- Very large files may take longer than defaults to stabilize; adjust -WaitUnlockTimeoutSec and -MinStableSeconds as needed
- If destination already has a file with the same name, the mover overwrites it; adjust naming policy if duplicates matter
- Copy+delete fallback verifies by size only (not checksum)
- Scheduled task installs for the current user context; enterprise environments may require different task settings

Upgrade notes

- Review README.md for command-line switches
- Check the log rotation path and adjust -LogPath if needed


