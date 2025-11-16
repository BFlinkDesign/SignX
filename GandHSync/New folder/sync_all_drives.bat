@echo off
echo ==========================================
echo NETWORK DRIVE SYNC - G:\ and H:\
echo ==========================================
echo.

:: Check VPN connection
if not exist G:\ (
    echo ERROR: Network drives not found! Connect VPN first.
    pause
    exit
)

:: Create folders
if not exist "C:\WorkSync\G_Drive" mkdir "C:\WorkSync\G_Drive"
if not exist "C:\WorkSync\H_Drive" mkdir "C:\WorkSync\H_Drive"
if not exist "C:\WorkSync\Logs" mkdir "C:\WorkSync\Logs"

:: Set log files
set logdate=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set logdate=%logdate: =0%

echo [1/4] Syncing G: Drive (daily changes)...
echo ==========================================
robocopy G:\ C:\WorkSync\G_Drive /MIR /MT:32 /R:2 /W:10 /NP /LOG:"C:\WorkSync\Logs\G_sync_%logdate%.txt"

echo.
echo [2/4] Checking H: Drive for changes...
echo ==========================================

:: Compare H: drive to see if sync needed
robocopy H:\ C:\WorkSync\H_Drive /L /E /XO /NP /NDL /NJS /NJH | find "New File" >nul
if %errorlevel%==0 (
    echo Changes detected on H: - syncing...
    robocopy H:\ C:\WorkSync\H_Drive /MIR /MT:32 /R:2 /W:10 /NP /LOG:"C:\WorkSync\Logs\H_sync_%logdate%.txt"
) else (
    echo No changes on H: - skipping sync
)

echo.
echo [3/4] Backing up G: changes...
echo ==========================================
set backupdir=C:\WorkSync\Daily_Backups\G_%date:~-4,4%%date:~-10,2%%date:~-7,2%
robocopy G:\ "%backupdir%" /E /MAXAGE:2 /MT:32 /R:1 /W:5 /XO /NP

echo.
echo [4/4] Summary:
echo ==========================================
echo G: Drive synced to: C:\WorkSync\G_Drive
echo H: Drive synced to: C:\WorkSync\H_Drive
echo Logs saved to: C:\WorkSync\Logs
echo.
pause