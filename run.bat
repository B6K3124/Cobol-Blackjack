@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.10 or newer.
    exit /b 1
)

if not exist "cobol\build\blackjack" (
    if not exist "cobol\build\blackjack.exe" (
        echo Building the COBOL engine...
        python build.py
        if errorlevel 1 exit /b 1
    )
)

python -m blackjack %*
endlocal