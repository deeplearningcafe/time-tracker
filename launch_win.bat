@echo off
setlocal enabledelayedexpansion

echo --- Starting Time Tracker ---

:: 1. Load and Sanitize .env
:: We read each line as a whole (delims=) to prevent splitting at spaces.
if exist .env (
    for /f "usebackq delims=" %%L in (".env") do (
        set "line=%%L"
        :: Ignore empty lines and lines starting with #
        if "!line!" neq "" if "!line:~0,1!" neq "#" (
            :: Split only at the first "="
            for /f "tokens=1,* delims==" %%A in ("!line!") do (
                set "KEY=%%A"
                set "VAL=%%B"

                :: 1. Strip all double quotes
                set "VAL=!VAL:"=!"

                :: 2. Strip inline comments (split by # and take first part)
                for /f "tokens=1 delims=#" %%I in ("!VAL!") do set "VAL=%%I"

                :: 3. Trim trailing spaces (recursive-like trim)
                for /l %%k in (1,1,20) do (
                    if "!VAL:~-1!"==" " set "VAL=!VAL:~0,-1!"
                )

                :: 4. Set the variable
                set "!KEY!=!VAL!"
            )
        )
    )
)

echo Checking if the drive directory "%LOCAL_MOUNT%" exists
if not exist "%LOCAL_MOUNT%" mkdir "%LOCAL_MOUNT%"

:: 1. DOWNLOAD (Sync Down)
echo Checking for updates from cloud...
:: quotes to handle spaces in the path
if exist "%RCLONE_EXE_PATH%" (
    "%RCLONE_EXE_PATH%" copy "%REMOTE_NAME%:%REMOTE_PATH%" "%LOCAL_MOUNT%"
) else (
    echo Warning: rclone not found at: "%RCLONE_EXE_PATH%"
)

:: 2. RUN APP
for %%I in ("%LOCAL_MOUNT%") do set "SYNC_DRIVE_PATH=%%~fI"

call conda activate track

echo Launching App...
echo Debug status: [%DEBUG%]

if /I "%DEBUG%"=="true" (
    echo DEBUG mode detected: Launching separate terminals...

    start "Django Backend" cmd /c ^
        "call conda activate track && python backend\manage.py runserver"

    start "Vue Frontend" cmd /c "cd frontend && npm run dev"

    echo ---------------------------------------------------
    echo   App is running in debug mode in separate windows.
    echo   Press any key in this terminal to STOP and SYNC.
    echo ---------------------------------------------------
    pause >nul

    echo Closing instances...

    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 "') do (
        taskkill /f /pid %%a >nul 2>&1
    )
) else (
    python backend\manage.py runserver
)

:: 3. UPLOAD (Sync Up)
echo.
echo --- App Stopped. Synchronizing Data... ---

python backend\manage.py export_sync_data

if exist "%RCLONE_EXE_PATH%" (
    "%RCLONE_EXE_PATH%" sync "%LOCAL_MOUNT%" "%REMOTE_NAME%:%REMOTE_PATH%"
    echo Sync complete.
) else (
    echo Warning: rclone not found. Sync skipped.
)

echo --- Goodbye! ---
endlocal
