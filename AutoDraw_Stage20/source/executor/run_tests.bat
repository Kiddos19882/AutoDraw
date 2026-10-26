@echo off
setlocal
cd /d "%~dp0"
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
