@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher ^(py.exe^) was not found.
  echo Install Python 3.11 x64 with Tcl/Tk and retry.
  pause
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 was not found. Install Python 3.11 x64 and retry.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 goto :fail
)
call ".venv\Scripts\activate.bat"
python -m pip install -r requirements-runtime.txt
if errorlevel 1 goto :fail
python integrated_app.py
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo AutoDraw did not start. Read the error output above.
pause
exit /b 1
