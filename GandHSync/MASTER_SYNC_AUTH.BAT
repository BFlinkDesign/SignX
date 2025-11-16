@echo off
echo ==========================================
echo BRADY NETWORK SYNC WITH AUTHENTICATION
echo ==========================================
echo.

:: Your Brady server paths
set SERVER_G=\\ES-FS02\customers2
set SERVER_H=\\ES-FS02\users\brady
set DOMAIN=Eagle

:: Check if already mapped
if exist G:\ if exist H:\ goto :already_mapped

:: Get credentials
echo Please enter your Brady network credentials:
echo (Format: username or EAGLE\username)
echo.
set /p USERNAME="Username: "

:: Clean up any existing connections
net use G: /delete /y >nul 2>&1
net use H: /delete /y >nul 2>&1
net use \\ES-FS02 /delete /y >nul 2>&1

:: Map drives with credentials
echo.
echo Mapping network drives (you'll be prompted for password)...
echo.

:: Map G: drive
echo Mapping G: drive (customers2)...
net use G: %SERVER_G% /persistent:yes /user:%USERNAME%
if errorlevel 1 (
    echo Failed to map G: drive!
    pause
    exit
)

:: Map H: drive  
echo.
echo Mapping H: drive (your personal folder)...
net use H: %SERVER_H% /persistent:yes
if errorlevel 1 (
    :: Try with credentials again if first mapping worked but second didn't
    net use H: %SERVER_H% /persistent:yes /user:%USERNAME%
)

:already_mapped
:: Verify drives exist
if not exist G:\ (
    echo ERROR: G: drive not accessible!
    pause
    exit
)
if not exist H:\ (
    echo ERROR: H: drive not accessible!
    pause
    exit
)

echo.
echo ✓ Network drives successfully mapped!
echo.

:: Create folders
if not exist "C:\WorkSync\G_Drive" mkdir "C:\WorkSync\G_Drive"
if not exist "C:\WorkSync\H_Drive" mkdir "C:\WorkSync\H_Drive"
if not exist "C:\WorkSync\Logs" mkdir "C:\WorkSync\Logs"

:: Check if first time (folders empty)
dir /b "C:\WorkSync\G_Drive" 2>nul | find /v /c "" > nul
if %errorlevel%==1 (
    echo FIRST TIME SETUP DETECTED
    echo This will copy ALL files from your Brady drives
    echo This may take several hours!
    echo.
    echo Press Ctrl+C to cancel, or
    pause
    goto :full_copy
) else (
    goto :regular_sync
)

:full_copy
echo.
echo [1/2] Copying entire customers2 (G:) drive...
echo This includes all customer files you have access to
robocopy G:\ C:\WorkSync\G_Drive /E /MT:32 /R:2 /W:10 /XO /NP /LOG:"C:\WorkSync\Logs\G_initial.txt" /TEE

echo.
echo [2/2] Copying your personal Brady folder (H:)...
robocopy H:\ C:\WorkSync\H_Drive /E /MT:32 /R:2 /W:10 /XO /NP /LOG:"C:\WorkSync\Logs\H_initial.txt" /TEE
goto :done

:regular_sync
:: Set log files
set logdate=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set logdate=%logdate: =0%

echo [1/2] Syncing customers2 (G:) drive...
robocopy G:\ C:\WorkSync\G_Drive /MIR /MT:32 /R:2 /W:10 /NP /LOG:"C:\WorkSync\Logs\G_sync_%logdate%.txt"

echo.
echo [2/2] Syncing your Brady folder (H:)...
robocopy H:\ C:\WorkSync\H_Drive /MIR /MT:32 /R:2 /W:10 /NP /LOG:"C:\WorkSync\Logs\H_sync_%logdate%.txt"

:done
echo.
echo ==========================================
echo ✓ SYNC COMPLETE!
echo ==========================================
echo customers2 → C:\WorkSync\G_Drive
echo brady folder → C:\WorkSync\H_Drive
echo.
echo You can now work offline with these files!
echo ==========================================
pause