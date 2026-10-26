@echo off
setlocal
cd /d "%~dp0"
python run_all_tests.py
if errorlevel 1 (
  echo.
  echo Tests failed. See the output above.
  pause
  exit /b 1
)
endlocal
