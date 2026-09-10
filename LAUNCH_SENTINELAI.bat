@echo off
setlocal

rem ============================================================
rem  SentinelAI - One-Click Launcher
rem  Starts backend + frontend and opens the dashboard.
rem  No installation, no admin rights, no internet required.
rem ============================================================

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"

echo.
echo  ===================================
echo   SentinelAI - Starting Services...
echo  ===================================
echo.

rem ------------------------------------------------------------
rem  Check Python - try py launcher, then python, with fallback paths
rem ------------------------------------------------------------
set "PYTHON_CMD="

rem  Try py launcher in PATH
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :found_python
)

rem  Check common py.exe locations
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\py.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\py.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\py.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\py.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\py.exe"
    "C:\Python314\py.exe"
    "C:\Python313\py.exe"
    "C:\Python312\py.exe"
    "C:\Python311\py.exe"
    "C:\Python310\py.exe"
    "C:\Python39\py.exe"
) do (
    if exist %%P (
        set "PYTHON_CMD=%%~P -3"
        goto :found_python
    )
)

rem  Try python in PATH (avoids Windows Store stub)
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTEST=%%i"
    echo %PYTEST% | findstr /i "Python 3" >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
        goto :found_python
    )
)

rem  Check common python.exe locations
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
) do (
    if exist %%P (
        set "PYTHON_CMD=%%~P"
        goto :found_python
    )
)

echo  [ERROR] Python not found.
echo  Install Python 3.10+ from https://www.python.org
echo  and ensure "Add Python to PATH" is checked.
echo.
pause
exit /b 1

:found_python
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "PYVER=%%i"
echo  [OK] Found: %PYVER%

rem ------------------------------------------------------------
rem  Check Node.js - try PATH, then common install locations
rem ------------------------------------------------------------
set "NODE_CMD="
set "NPM_CMD="

rem  Try node in PATH
where node >nul 2>&1
if %errorlevel% equ 0 (
    set "NODE_CMD=node"
    set "NPM_CMD=npm"
    goto :found_node
)

rem  Check common Node.js install locations
for %%P in (
    "%ProgramFiles%\nodejs\node.exe"
    "%LOCALAPPDATA%\Programs\nodejs\node.exe"
    "%APPDATA%\nvm\current\node.exe"
) do (
    if exist %%P (
        set "NODE_DIR=%%~dpP"
        set "NODE_CMD=%%~P"
        set "NPM_CMD=%%~dpPnpm.cmd"
        goto :found_node
    )
)

rem  Check nvm for Windows installations
if exist "%APPDATA%\nvm" (
    for /d %%D in ("%APPDATA%\nvm\v*") do (
        if exist "%%D\node.exe" (
            set "NODE_DIR=%%D"
            set "NODE_CMD=%%D\node.exe"
            set "NPM_CMD=%%D\npm.cmd"
            goto :found_node
        )
    )
)

echo  [ERROR] Node.js not found.
echo  Install Node.js 18+ LTS from https://nodejs.org
echo  and ensure it is added to your PATH.
echo.
pause
exit /b 1

:found_node
for /f "tokens=*" %%i in ('%NODE_CMD% --version 2^>^&1') do set "NODEVER=%%i"
echo  [OK] Found: Node.js %NODEVER%

rem  Verify npm exists - check PATH first, then same dir as node
where npm >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Found: npm
    set "NPM_CMD=npm"
) else (
    if defined NODE_DIR (
        if exist "%NODE_DIR%\npm.cmd" (
            echo  [OK] Found: npm
            set "NPM_CMD=%NODE_DIR%\npm.cmd"
        ) else (
            echo  [ERROR] npm not found.
            echo  It should be installed alongside Node.js.
            echo  Reinstall from https://nodejs.org
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo  [ERROR] npm not found.
        echo  It should be installed alongside Node.js.
        echo  Reinstall from https://nodejs.org
        echo.
        pause
        exit /b 1
    )
)

rem ------------------------------------------------------------
rem  Verify backend dependencies exist (do NOT install)
rem ------------------------------------------------------------
%PYTHON_CMD% -c "import fastapi, uvicorn, sqlalchemy" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Backend Python dependencies are missing.
    echo  Follow the README setup instructions:
    echo    cd backend
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo  [OK] Backend dependencies ready

rem ------------------------------------------------------------
rem  Verify frontend dependencies exist (do NOT install)
rem ------------------------------------------------------------
if not exist "%FRONTEND_DIR%\node_modules" (
    echo.
    echo  [ERROR] Frontend node_modules not found.
    echo  Follow the README setup instructions:
    echo    cd frontend
    echo    npm install
    echo.
    pause
    exit /b 1
)
echo  [OK] Frontend dependencies ready

rem ------------------------------------------------------------
rem  Seed IOC database if it does not exist
rem ------------------------------------------------------------
if not exist "%BACKEND_DIR%\data\sentinel.db" (
    echo.
    echo  [INFO] First run detected - seeding demo IOC database...
    cd /d "%BACKEND_DIR%"
    %PYTHON_CMD% seed_data.py
)

rem ------------------------------------------------------------
rem  Create temporary launcher scripts (avoids quoting issues)
rem ------------------------------------------------------------
set "TEMP_BACKEND=%TEMP%\sentinelai_start_backend.cmd"
set "TEMP_FRONTEND=%TEMP%\sentinelai_start_frontend.cmd"

(
    echo @echo off
    echo cd /d "%BACKEND_DIR%"
    echo %PYTHON_CMD% -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    echo pause
) > "%TEMP_BACKEND%"

(
    echo @echo off
    echo cd /d "%FRONTEND_DIR%"
    echo %NPM_CMD% run dev
    echo pause
) > "%TEMP_FRONTEND%"

rem ------------------------------------------------------------
rem  Start Backend in a new terminal
rem ------------------------------------------------------------
echo.
echo  [STARTING] Backend on http://127.0.0.1:8000 ...
start "SentinelAI Backend" cmd /k "%TEMP_BACKEND%"

rem ------------------------------------------------------------
rem  Start Frontend in a new terminal
rem ------------------------------------------------------------
echo  [STARTING] Frontend on http://localhost:5173 ...
start "SentinelAI Frontend" cmd /k "%TEMP_FRONTEND%"

rem ------------------------------------------------------------
rem  Wait for services to start, then open browser
rem ------------------------------------------------------------
echo.
echo  Waiting 6 seconds for services to start...
timeout /t 6 /nobreak >nul

echo  Opening dashboard in your browser...
start http://localhost:5173/dashboard

echo.
echo  ===================================
echo   SentinelAI is running!
echo  ===================================
echo.
echo   Frontend:  http://localhost:5173/dashboard
echo   Backend:   http://127.0.0.1:8000/docs
echo.
echo   Close the two terminal windows to stop.
echo.
pause
