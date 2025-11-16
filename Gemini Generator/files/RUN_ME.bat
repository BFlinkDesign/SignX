@echo off
REM Eagle Sign - Gemini Project Document Generator
REM Double-click this file to generate project summaries

echo.
echo ====================================================================
echo  EAGLE SIGN - GEMINI PROJECT DOCUMENT GENERATOR
echo ====================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking Python installation...
python --version

echo.
echo [2/3] Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Generating project summaries...
echo.
python generate_gemini_docs.py

echo.
echo ====================================================================
echo  PROCESS COMPLETE
echo ====================================================================
echo.

REM Check if output directory was created
if exist "%USERPROFILE%\Desktop\Gemini_Project_Summaries\" (
    echo Opening output folder...
    start "" "%USERPROFILE%\Desktop\Gemini_Project_Summaries\"
) else (
    echo Output folder not found. Check for errors above.
)

pause
