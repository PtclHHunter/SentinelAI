@echo off
setlocal enabledelayedexpansion
title SentinelAI - Requirements Check

echo ============================================
echo   SentinelAI - System Requirements Check
echo ============================================
echo.

set PASS=0
set FAIL=0

:: --- Python ---
echo [CHECK] Python 3.x ...
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "delims=" %%v in ('py -3 --version 2^>^&1') do set PYVER=%%v
    echo   [PASS] !PYVER!
    set /a PASS+=1
) else (
    echo   [FAIL] Python 3.x not found
    set /a FAIL+=1
)

:: --- Node.js ---
echo [CHECK] Node.js ...
if exist "C:\Program Files\nodejs\node.exe" (
    for /f "delims=" %%v in ('"C:\Program Files\nodejs\node.exe" --version 2^>^&1') do set NODEVER=%%v
    echo   [PASS] Node.js !NODEVER!
    set /a PASS+=1
) else (
    echo   [FAIL] Node.js not found
    set /a FAIL+=1
)

:: --- npm ---
echo [CHECK] npm ...
if exist "C:\Program Files\nodejs\npm.cmd" (
    for /f "delims=" %%v in ('cmd /c "C:\Program Files\nodejs\npm.cmd" --version 2^>^&1') do set NPMVER=%%v
    echo   [PASS] npm !NPMVER!
    set /a PASS+=1
) else (
    echo   [FAIL] npm not found
    set /a FAIL+=1
)

:: --- Python packages ---
echo.
echo [CHECK] Python packages ...

for %%p in (fastapi uvicorn sqlalchemy pydantic pydantic_settings python_multipart reportlab httpx) do (
    py -3 -c "import %%p" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [PASS] %%p installed
        set /a PASS+=1
    ) else (
        echo   [FAIL] %%p NOT installed
        set /a FAIL+=1
    )
)

:: --- node_modules ---
echo.
echo [CHECK] Frontend dependencies ...
if exist "frontend\node_modules" (
    echo   [PASS] node_modules exists
    set /a PASS+=1
) else (
    echo   [FAIL] node_modules missing
    set /a FAIL+=1
)

:: --- Database ---
echo.
echo [CHECK] Database ...
if exist "backend\data\sentinel.db" (
    echo   [PASS] sentinel.db exists
    set /a PASS+=1
) else (
    echo   [FAIL] sentinel.db missing
    set /a FAIL+=1
)

:: --- Sample logs ---
echo.
echo [CHECK] Sample logs ...
if exist "backend\data\sample_logs\auth_sample.log" (
    echo   [PASS] Sample logs present
    set /a PASS+=1
) else (
    echo   [FAIL] Sample logs missing
    set /a FAIL+=1
)

:: --- Summary ---
echo.
echo ============================================
set /a TOTAL=!PASS!+!FAIL!
echo   Results: !PASS!/!TOTAL! checks passed
if !FAIL! equ 0 (
    echo   Status: ALL CLEAR - Ready to launch!
    echo.
    echo   Run LAUNCH_SENTINELAI.bat to start.
) else (
    echo   Status: !FAIL! issue^(s^) found. Fix before launching.
)
echo ============================================

endlocal
