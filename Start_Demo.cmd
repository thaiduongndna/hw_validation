@echo off
setlocal
cd /d "%~dp0"
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
    python -m hwval_demo gui
) else (
    py -3 -m hwval_demo gui
)
if errorlevel 1 (
    echo.
    echo Unable to start the demo. Python 3.10+ with Tkinter is required.
    pause
)
