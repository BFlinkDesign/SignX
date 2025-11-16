@echo off
echo ==========================================
echo FIRST TIME SETUP - FULL COPY
echo ==========================================
echo This will copy ALL files from G: and H:
echo This will take MANY HOURS!
echo.
pause

if not exist G:\ (
    echo ERROR: Network drives not found! Connect VPN first.
    pause
    exit
)

echo Creating folder structure...
mkdir "C:\WorkSync\G_Drive" 2>nul
mkdir "C:\WorkSync\H_Drive" 2>nul
mkdir "C:\WorkSync\Logs" 2>nul
mkdir "C:\WorkSync\Daily_Backups" 2>nul

echo.
echo [1/2] Copying entire G: drive...
echo This will resume if interrupted.
robocopy G:\ C:\WorkSync\G_Drive /E /MT:32 /R:2 /W:10 /XO /NP /LOG:"C:\WorkSync\Logs\G_initial.txt" /TEE

echo.
echo [2/2] Copying entire H: drive...
robocopy H:\ C:\WorkSync\H_Drive /E /MT:32 /R:2 /W:10 /XO /NP /LOG:"C:\WorkSync\Logs\H_initial.txt" /TEE

echo.
echo ==========================================
echo INITIAL SETUP COMPLETE!
echo Use sync_all_drives.bat for daily syncs
echo ==========================================
pause