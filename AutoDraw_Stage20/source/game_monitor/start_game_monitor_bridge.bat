@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "GAME_ORIGIN=%~1"
set "SNIPPET_FILE=%~2"

if not defined GAME_ORIGIN (
    echo Enter the exact HTTPS Origin from the game iframe.
    set /p GAME_ORIGIN=Origin:
)
if not defined GAME_ORIGIN (
    echo Origin is required.
    pause
    exit /b 2
)

if not defined SNIPPET_FILE (
    set "SNIPPET_FILE=%REPO_ROOT%\AutoDraw_Stage20\data\results\brush_behavior_tests\game_monitor_bridge\connection_snippet.js"
)

cd /d "%REPO_ROOT%"
if errorlevel 1 (
    echo Could not change to repository root: "%REPO_ROOT%"
    pause
    exit /b 3
)

py -3.11 -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo Installing the isolated Game Monitor Bridge dependency...
    py -3.11 -m pip install -r "%SCRIPT_DIR%requirements-bridge.txt"
    if errorlevel 1 (
        echo Dependency installation failed. Check Python 3.11 and pip.
        pause
        exit /b 4
    )
)

echo Starting the read-only Game Monitor WebSocket collector...
py -3.11 "%SCRIPT_DIR%game_monitor_bridge_server.py" --origin "%GAME_ORIGIN%" --snippet-file "%SNIPPET_FILE%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Bridge exited with code %RESULT%.
echo.
echo The temporary browser snippet is removed when the server stops.
pause
exit /b %RESULT%
