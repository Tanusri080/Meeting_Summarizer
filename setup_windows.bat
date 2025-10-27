@echo off
echo Setting up Real-Time Speech Analysis Interface for Windows...
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv speech_env
if %errorlevel% neq 0 (
    echo Error creating virtual environment. Make sure Python is installed.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call speech_env\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements_windows.txt

if %errorlevel% neq 0 (
    echo Some packages failed to install. Trying alternative approach...
    pip install flask flask-socketio numpy scipy transformers torch --index-url https://download.pytorch.org/whl/cpu
    pip install textblob vaderSentiment librosa scikit-learn
    pip install faster-whisper sounddevice
)

echo.
echo Setup complete!
echo.
echo To run the application:
echo 1. Activate the environment: speech_env\Scripts\activate.bat
echo 2. Run the app: python realtime_app_windows.py
echo 3. Open browser to: http://localhost:5000
echo.
pause