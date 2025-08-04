@echo off
echo Installing Simple Global Screen Magnifier
echo =========================================

echo.
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

echo Python found!
echo.

echo Installing/Updating required packages from requirements.txt...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install Python dependencies via pip.
    echo Please check your internet connection and ensure pip is up to date.
    pause
    exit /b 1
)

echo.
echo Python dependencies installation complete. Running final dependency check...
echo (This might print which dependencies are installed or missing)
echo.
python run_magnifier.py

if errorlevel 1 (
    echo.
    echo The Screen Magnifier could not start due to missing or incorrect dependencies.
    echo Please review the output above for details on missing packages.
    echo You might need to manually install them or troubleshoot your Python environment.
) else (
    echo.
    echo Magnifier closed. Press any key to exit.
)
pause