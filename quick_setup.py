#!/usr/bin/env python3
"""
Quick Setup Script for Real-Time Speech Analysis
This will install all necessary dependencies
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and provide feedback"""
    print(f"\n🔄 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e.stderr}")
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
        print("Creating virtual environment...")
        if not run_command("python -m venv speech_env", "Creating virtual environment"):
            print("❌ Failed to create virtual environment")
            return
    
    # Install dependencies
    activate_cmd = "speech_env\\Scripts\\activate &&"
    
    dependencies = [
        "pip install --upgrade pip",
        "pip install flask flask-socketio",
        "pip install numpy scipy",
        "pip install torch --index-url https://download.pytorch.org/whl/cpu",
        "pip install transformers faster-whisper",
        "pip install textblob vaderSentiment",
        "pip install librosa scikit-learn",
        "pip install sounddevice python-socketio eventlet"
    ]
    
    print("\n📦 Installing dependencies...")
    failed_count = 0
    
    for dep in dependencies:
        full_command = f"{activate_cmd} {dep}"
        if not run_command(full_command, f"Installing: {dep}"):
            failed_count += 1
    
    # Download NLTK data
    print("\n📚 Downloading NLTK data...")
    nltk_cmd = f"{activate_cmd} python -c \"import nltk; nltk.download('punkt', quiet=True); nltk.download('vader_lexicon', quiet=True)\""
    run_command(nltk_cmd, "Downloading NLTK data")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SETUP SUMMARY")
    print("=" * 50)
    
    if failed_count == 0:
        print("🎉 Setup completed successfully!")
        print("\nTo run the application:")
        print("1. Activate environment: speech_env\\Scripts\\activate")
        print("2. Run: python realtime_app_windows.py")
        print("3. Open browser to: http://localhost:5000")
    else:
        print(f"⚠️ Setup completed with {failed_count} failures")
        print("Some packages may need manual installation")
        print("Run 'python test_setup.py' to see what's missing")
    
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()