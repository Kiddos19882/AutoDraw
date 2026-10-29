@echo off
setlocal
cd /d "%~dp0"

rem Match the preparation suite runner used by run_all_tests.py.
rem unittest discovery does not execute ordinary pytest function tests.
for %%I in ("%~dp0..\..") do set "APP_ROOT=%%~fI"
set "PYTHONPATH=%APP_ROOT%;%APP_ROOT%\source\preparation;%APP_ROOT%\source\executor;%PYTHONPATH%"

py -3 -m pytest -q -ra tests
set TEST_EXIT=%ERRORLEVEL%
echo.
if "%TEST_EXIT%"=="0" (
  echo RESULT: PREPARATION PYTEST SUITE PASSED.
) else (
  echo RESULT: PREPARATION PYTEST SUITE FAILED.
)
pause
exit /b %TEST_EXIT%
