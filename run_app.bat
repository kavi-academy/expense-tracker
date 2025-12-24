@echo off
setlocal

echo ===================================================
echo   Python Expense Tracker - Auto Launcher
echo ===================================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation.
    pause
    exit /b
)

:: Create Virtual Environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: Install Dependencies
if not exist "venv\installed.flag" (
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b
    )
    echo. > venv\installed.flag
)

:: Run the App
echo [INFO] Starting Streamlit App...
streamlit run app.py --server.headless true --server.headless true

pause
