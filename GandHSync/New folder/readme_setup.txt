G AND H NETWORK DRIVE SYNC SETUP INSTRUCTIONS
=============================================

FOLDER STRUCTURE:
1. Create folder: C:\Scripts\GandHSync\
2. Save all downloaded files to this folder

FILE DESCRIPTIONS:
- initial_setup.bat         = Run ONCE to copy all files (takes hours)
- sync_all_drives.bat      = Daily sync script (run manually or auto)
- auto_sync_when_connected.bat = Monitors and syncs automatically
- start_sync_hidden.vbs    = Makes auto sync run invisibly
- README_SETUP.txt         = This file

FIRST TIME SETUP:
1. Connect to VPN
2. Run initial_setup.bat (let it run overnight)
3. This creates C:\WorkSync\ folders with all your files

DAILY USE - MANUAL:
1. Connect to VPN
2. Double-click sync_all_drives.bat
3. Work from C:\WorkSync\G_Drive and C:\WorkSync\H_Drive

AUTOMATIC SETUP:
1. Copy start_sync_hidden.vbs to your Startup folder
   - Press Win+R
   - Type: shell:startup
   - Paste the .vbs file there
2. Restart Windows
3. Script runs automatically (hidden)
4. Syncs whenever you connect VPN

SYNC BEHAVIOR:
- Checks for VPN every 5 minutes
- Syncs immediately when VPN detected
- Re-syncs every 4 hours while connected
- G: drive always syncs
- H: drive only syncs if changes detected

YOUR SYNCED FILES LOCATION:
- G: drive copy: C:\WorkSync\G_Drive\
- H: drive copy: C:\WorkSync\H_Drive\
- Sync logs: C:\WorkSync\Logs\
- Daily backups: C:\WorkSync\Daily_Backups\

NOTES:
- First sync takes many hours
- Daily syncs are much faster (only changes)
- Keep 50GB+ free space for sync files
- VPN must be connected to sync