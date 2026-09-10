@echo off
setlocal

rem ============================================================
rem  SentinelAI - Stop Script
rem  Stops only the two SentinelAI terminal windows and their
rem  child processes (backend uvicorn, frontend npm/node).
rem  Safe: never touches unrelated Python, Node, or browser
rem  processes.
rem ============================================================

echo.
echo  ===================================
echo   SentinelAI - Stopping Services...
echo  ===================================
echo.

set "FOUND_BACKEND=0"
set "FOUND_FRONTEND=0"

rem ------------------------------------------------------------
rem  Find and stop the Backend window + its child processes
rem ------------------------------------------------------------
for /f "tokens=2" %%i in ('tasklist /FI "WINDOWTITLE eq SentinelAI Backend" /FO LIST 2^>nul ^| findstr "PID:"') do (
    echo  Stopping Backend ^(PID %%i^) and all child processes...
    taskkill /PID %%i /T /F >nul 2>&1
    set "FOUND_BACKEND=1"
)
if "%FOUND_BACKEND%"=="0" (
    echo  [INFO] No SentinelAI Backend window found ^(already stopped or never started^).
)

rem ------------------------------------------------------------
rem  Find and stop the Frontend window + its child processes
rem ------------------------------------------------------------
for /f "tokens=2" %%i in ('tasklist /FI "WINDOWTITLE eq SentinelAI Frontend" /FO LIST 2^>nul ^| findstr "PID:"') do (
    echo  Stopping Frontend ^(PID %%i^) and all child processes...
    taskkill /PID %%i /T /F >nul 2>&1
    set "FOUND_FRONTEND=1"
)
if "%FOUND_FRONTEND%"=="0" (
    echo  [INFO] No SentinelAI Frontend window found ^(already stopped or never started^).
)

rem ------------------------------------------------------------
rem  Clean up temporary launcher scripts if they exist
rem ------------------------------------------------------------
if exist "%TEMP%\sentinelai_start_backend.cmd" del "%TEMP%\sentinelai_start_backend.cmd" >nul 2>&1
if exist "%TEMP%\sentinelai_start_frontend.cmd" del "%TEMP%\sentinelai_start_frontend.cmd" >nul 2>&1

echo.
echo  ===================================
echo   SentinelAI stopped.
echo  ===================================
echo.
pause
