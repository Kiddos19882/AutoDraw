@echo off
setlocal
set "PYTHONUTF8=1"
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher ^(py.exe^) was not found.
  echo Install Python 3.11 x64 with Tcl/Tk, then retry.
if not defined AUTODRAW_NO_PAUSE pause
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 was not found. Install Python 3.11 x64 and retry.
if not defined AUTODRAW_NO_PAUSE pause
  exit /b 1
)

if not exist ".venv-build\Scripts\python.exe" (
  py -3.11 -m venv .venv-build
  if errorlevel 1 goto :fail
)
call ".venv-build\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail
python -m pip install -r requirements-runtime.txt
if errorlevel 1 goto :fail
python run_all_tests.py
if errorlevel 1 goto :fail
python build_windows.py
if errorlevel 1 goto :fail
python smoke_test_portable.py
if errorlevel 1 goto :fail

echo.
echo Build succeeded.
echo Unified portable application: release\AutoDrawPortable\AutoDraw.exe
echo Copy the complete AutoDrawPortable folder to another Windows PC.
echo User data is stored in AutoDrawPortable\data.
if not defined AUTODRAW_NO_PAUSE pause
exit /b 0

:fail
echo.
echo Build failed. Read the error output above.
if not defined AUTODRAW_NO_PAUSE pause
exit /b 1
