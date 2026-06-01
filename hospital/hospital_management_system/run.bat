@echo off
echo.
echo ===============================================
echo   Hospital Management System - Startup Script
echo ===============================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Python found!
echo.

echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting Flask application...
echo.
echo Application will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
