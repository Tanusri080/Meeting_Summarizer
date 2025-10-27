#!/usr/bin/env python3
"""
Quick Setup Script for Real-Time Speech Analysis
This will install all necessary dependencies automatically
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and provide feedback"""
    print(f"\n🔄 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Quick Setup for Real-Time Speech Analysis")
    print("=" * 50)
    
    # Check if virtual environment exists
    if not os.path.exists("speech_env"):
        print("📁 Creating virtual environment...")
        if not run_command("python -m venv speech_env", "Creating virtual environment"):
            print("❌ Failed to create virtual environment")
            input("Press Enter to exit...")
            return
    else:
        print("📁 Virtual environment already exists")
    
    # Install dependencies
    activate_cmd = "speech_env\\Scripts\\activate &&"
    
    dependencies = [
        ("pip install --upgrade pip", "Upgrading pip"),
        ("pip install flask flask-socketio", "Installing Flask and SocketIO"),
        ("pip install numpy scipy", "Installing NumPy and SciPy"),
        ("pip install torch --index-url https://download.pytorch.org/whl/cpu", "Installing PyTorch (CPU)"),
        ("pip install transformers", "Installing Transformers"),
        ("pip install faster-whisper", "Installing Faster Whisper"),
        ("pip install textblob vaderSentiment", "Installing Text Analysis"),
        ("pip install librosa scikit-learn", "Installing Audio Processing"),
        ("pip install sounddevice python-socketio eventlet", "Installing Audio and Socket utilities")
    ]
    
    print("\n📦 Installing dependencies (this may take several minutes)...")
    failed_count = 0
    
    for dep_cmd, description in dependencies:
        full_command = f"{activate_cmd} {dep_cmd}"
        if not run_command(full_command, description):
            failed_count += 1
            print(f"⚠️ {description} failed, but continuing...")
    
    # Download NLTK data
    print("\n📚 Downloading NLTK data...")
    nltk_cmd = f"{activate_cmd} python -c \"import nltk; nltk.download('punkt', quiet=True); nltk.download('vader_lexicon', quiet=True)\""
    run_command(nltk_cmd, "Downloading NLTK data")
    
    # Create run script
    print("\n📝 Creating run script...")
    run_script = """@echo off
echo Starting Real-Time Speech Analysis Interface...
echo.

if not exist "speech_env\\Scripts\\activate.bat" (
    echo Virtual environment not found!
    echo Please run: python quick_setup.py
    pause
    exit /b 1
)

call speech_env\\Scripts\\activate.bat
echo Starting server...
echo.
echo 🌐 Open your browser and go to: http://localhost:5000
echo 🛑 Press Ctrl+C to stop the server
echo.
python realtime_app_windows.py
pause
"""
    
    try:
        with open("run_app.bat", "w") as f:
            f.write(run_script)
        print("✅ Created run_app.bat")
    except Exception as e:
        print(f"❌ Failed to create run script: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SETUP SUMMARY")
    print("=" * 50)
    
    if failed_count == 0:
        print("🎉 SETUP COMPLETED SUCCESSFULLY!")
        print("\n📋 Next steps:")
        print("1. Double-click 'run_app.bat' OR")
        print("2. Run manually:")
        print("   speech_env\\Scripts\\activate")
        print("   python realtime_app_windows.py")
        print("3. Open browser to: http://localhost:5000")
        print("4. Allow microphone access when prompted")
    else:
        print(f"⚠️ Setup completed with {failed_count} failures")
        print("Some packages may need manual installation")
        print("Run 'python test_setup.py' to see what's still missing")
    
    print("\n" + "=" * 50)
    input("Press Enter to continue...")

if __name__ == "__main__":
    main()