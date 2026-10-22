@echo off
title OceanGuard AI Server
cls
echo =========================================================================
echo   OceanGuard AI - Marine Pollution Monitoring ^& Investigation System
echo =========================================================================
echo.

cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\Poojitha\AppData\Local\Programs\Python311\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo Using Python runtime: %PYTHON_EXE%
set PYTHONPATH=%CD%

echo Launching web browser at http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"

echo.
echo Starting FastAPI / Uvicorn server on port 8000 ...
echo.
"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
