@echo off
echo ==========================================
echo TESTING BRADY NETWORK CONNECTION
echo ==========================================
echo.

echo [1] Testing server connectivity...
ping -n 2 ES-FS02
if errorlevel 1 (
    echo ✗ Cannot reach server! Check VPN connection.
    pause
    exit
)
echo ✓ Server is reachable
echo.

echo [2] Testing authentication...
echo Enter your credentials to test access:
net use \\ES-FS02\IPC$ /user:
if errorlevel 1 (
    echo ✗ Authentication failed!
    echo Try format: EAGLE\username
) else (
    echo ✓ Authentication successful!
    net use \\ES-FS02\IPC$ /delete /y >nul 2>&1
)
echo.

echo [3] Current mapped drives:
net use
echo.

echo [4] Testing share access...
echo.
echo Attempting to list customers2 share:
dir \\ES-FS02\customers2 2>&1 | find "Directory" >nul
if errorlevel 1 (
    echo ✗ Cannot access customers2
) else (
    echo ✓ Can access customers2
)

echo.
echo Attempting to list your user folder:
dir \\ES-FS02\users\brady 2>&1 | find "Directory" >nul
if errorlevel 1 (
    echo ✗ Cannot access users\brady
    echo Note: Your folder might be at users\[yourusername]
) else (
    echo ✓ Can access users\brady
)

echo.
echo ==========================================
echo TEST COMPLETE
echo ==========================================
pause