@echo off
echo Starting Real-Time Speech Analysis Interface...
echo.

REM Check if virtual environment exists
if not exist "speech_env\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup_windows.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call speech_env\Scripts\activate.bat

REM Run the application
echo Starting server...
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python realtime_app_windows.py

pause