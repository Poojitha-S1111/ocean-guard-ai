@echo off
title OceanGuard AI Server
cls
echo =========================================================================
echo   OceanGuard AI - Marine Pollution Monitoring ^& Investigation System
echo =========================================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%backend"

set "PYTHON_EXE=C:\Users\Poojitha\AppData\Local\Programs\Python311\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo Using Python runtime: %PYTHON_EXE%
echo Setting PYTHONPATH to: %CD%
set PYTHONPATH=%CD%

echo.
echo Launching web browser at http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"

echo.
echo Starting FastAPI / Uvicorn server on port 8000 ...
echo (Press CTRL+C anytime in this window to stop the server)
echo.
"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
