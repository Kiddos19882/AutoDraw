@echo off
setlocal
cd /d "%~dp0"
set "AUTODRAW_ROOT=%~dp0..\.."
set "PYTHONPATH=%AUTODRAW_ROOT%;%AUTODRAW_ROOT%\source\preparation;%AUTODRAW_ROOT%\source\executor;%~dp0tests;%PYTHONPATH%"
py -3 -m unittest discover -s tests -v
set TEST_EXIT=%ERRORLEVEL%
echo.
if "%TEST_EXIT%"=="0" (
  echo RESULT: ALL TESTS PASSED.
) else (
  echo RESULT: TESTS FAILED.
)
pause
exit /b %TEST_EXIT%
