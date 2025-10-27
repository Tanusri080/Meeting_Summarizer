#!/usr/bin/env python3
"""
Step-by-step setup script for Windows
This script will guide you through the setup process and handle common issues
"""

import os
import sys
import subprocess
import time

def run_command(command, description):
    """Run a command and provide feedback"""
    print(f"\n🔄 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT (took too long)")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def check_python():
    """Check Python installation"""
    print("=== Checking Python Installation ===")
    
    try:
        version = sys.version_info
        print(f"Python version: {version.major}.{version.minor}.{version.micro}")
        
        if version.major == 3 and version.minor >= 8:
            print("✅ Python version is compatible")
            return True
        else:
            print("❌ Python version too old. Please install Python 3.8+")
            return False
    except:
        print("❌ Python check failed")
        return False

def setup_virtual_environment():
    """Set up virtual environment"""
    print("\n=== Setting Up Virtual Environment ===")
    
    # Remove existing environment if it exists
    if os.path.exists("speech_env"):
        print("🗑️ Removing existing virtual environment...")
        import shutil
        shutil.rmtree("speech_env")
    
    # Create new virtual environment
    if run_command("python -m venv speech_env", "Creating virtual environment"):
        print("✅ Virtual environment created successfully")
        return True
    else:
        print("❌ Failed to create virtual environment")
        return False

def install_dependencies():
    """Install dependencies step by step"""
    print("\n=== Installing Dependencies ===")
    
    # Activate virtual environment command for Windows
    activate_cmd = "speech_env\\Scripts\\activate &&"
    
    steps = [
        (f"{activate_cmd} python -m pip install --upgrade pip", "Upgrading pip"),
        (f"{activate_cmd} pip install flask flask-socketio", "Installing Flask and SocketIO"),
        (f"{activate_cmd} pip install numpy scipy", "Installing NumPy and SciPy"),
        (f"{activate_cmd} pip install torch --index-url https://download.pytorch.org/whl/cpu", "Installing PyTorch (CPU version)"),
        (f"{activate_cmd} pip install transformers", "Installing Transformers"),
        (f"{activate_cmd} pip install faster-whisper", "Installing Faster Whisper"),
        (f"{activate_cmd} pip install textblob vaderSentiment", "Installing Text Analysis tools"),
        (f"{activate_cmd} pip install librosa scikit-learn", "Installing Audio Processing tools"),
        (f"{activate_cmd} pip install sounddevice", "Installing Sound Device"),
        (f"{activate_cmd} pip install python-socketio eventlet", "Installing SocketIO utilities"),
    ]
    
    failed_steps = []
    
    for command, description in steps:
        if not run_command(command, description):
            failed_steps.append(description)
            print(f"⚠️ {description} failed, but continuing...")
    
    if failed_steps:
        print(f"\n⚠️ Some installations failed: {', '.join(failed_steps)}")
        print("You may need to install these manually")
        return False
    else:
        print("\n✅ All dependencies installed successfully!")
        return True

def download_nltk_data():
    """Download required NLTK data"""
    print("\n=== Downloading NLTK Data ===")
    
    activate_cmd = "speech_env\\Scripts\\activate &&"
    nltk_commands = [
        f"{activate_cmd} python -c \"import nltk; nltk.download('punkt', quiet=True)\"",
        f"{activate_cmd} python -c \"import nltk; nltk.download('vader_lexicon', quiet=True)\"",
    ]
    
    for cmd in nltk_commands:
        run_command(cmd, "Downloading NLTK data")

def test_installation():
    """Test if everything is working"""
    print("\n=== Testing Installation ===")
    
    activate_cmd = "speech_env\\Scripts\\activate &&"
    test_cmd = f"{activate_cmd} python test_setup.py"
    
    if run_command(test_cmd, "Running diagnostic test"):
        return True
    else:
        print("❌ Installation test failed")
        return False

def create_run_script():
    """Create a simple run script"""
    print("\n=== Creating Run Script ===")
    
    run_script_content = """@echo off
echo Starting Real-Time Speech Analysis Interface...
echo.

if not exist "speech_env\\Scripts\\activate.bat" (
    echo Virtual environment not found. Please run setup_step_by_step.py first.
    pause
    exit /b 1
)

call speech_env\\Scripts\\activate.bat
echo Starting server...
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python realtime_app_windows.py
pause
"""
    
    try:
        with open("run_speech_app.bat", "w") as f:
            f.write(run_script_content)
        print("✅ Created run_speech_app.bat")
        return True
    except Exception as e:
        print(f"❌ Failed to create run script: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Real-Time Speech Analysis - Windows Setup")
    print("=" * 60)
    
    # Check Python
    if not check_python():
        print("\n❌ Setup failed: Python version incompatible")
        input("Press Enter to exit...")
        return
    
    # Setup virtual environment
    if not setup_virtual_environment():
        print("\n❌ Setup failed: Could not create virtual environment")
        input("Press Enter to exit...")
        return
    
    # Install dependencies
    print("\n⏳ This may take several minutes...")
    install_success = install_dependencies()
    
    # Download NLTK data
    download_nltk_data()
    
    # Create run script
    create_run_script()
    
    # Final test
    print("\n=== Final Setup Test ===")
    if install_success:
        print("✅ Setup completed successfully!")
        print("\nTo run the application:")
        print("1. Double-click 'run_speech_app.bat' OR")
        print("2. Run: python test_setup.py (to check everything)")
        print("3. Run: python realtime_app_windows.py")
        print("\nThen open your browser to: http://localhost:5000")
    else:
        print("⚠️ Setup completed with some issues")
        print("Run: python test_setup.py to see what's missing")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()