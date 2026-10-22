@echo off
title OceanGuard AI - Public WhatsApp Share Launcher
cls
echo =========================================================================
echo   OceanGuard AI - Public Live Share Launcher (for WhatsApp / Web)
echo =========================================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%backend"

set "PYTHON_EXE=C:\Users\Poojitha\AppData\Local\Programs\Python311\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [1/3] Setting up local backend server environment...
set PYTHONPATH=%CD%

echo [2/3] Starting OceanGuard AI server in the background...
start "OceanGuard Backend" /min "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo [3/3] Creating secure public HTTPS link for WhatsApp sharing...
echo.
echo -------------------------------------------------------------------------
echo   CONNECTING TUNNEL... 
echo   Your public HTTPS URL will appear below in a few seconds!
echo   Copy that URL and share it on WhatsApp.
echo   Keep this window open while your friends or colleagues test the site.
echo -------------------------------------------------------------------------
echo.

ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 nokey@localhost.run

pause
