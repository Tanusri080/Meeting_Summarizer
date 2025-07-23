#!/usr/bin/env python3
"""
Real-Time Speech Analysis Interface Startup Script
This script initializes and runs the real-time speech analysis interface.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'flask', 'flask_socketio', 'faster_whisper', 'transformers',
        'textblob', 'vaderSentiment', 'librosa', 'sklearn', 'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies"""
    print("Installing required dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = ['recordings', 'static/css', 'static/js', 'templates']
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created successfully!")

def download_models():
    """Download required ML models"""
    print("Downloading required models (this may take a few minutes)...")
    
    try:
        # Import and initialize models to trigger downloads
        from faster_whisper import WhisperModel
        from transformers import pipeline
        
        print("📥 Downloading Whisper model...")
        whisper_model = WhisperModel("base", compute_type="int8")
        
        print("📥 Downloading summarization model...")
        summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
        
        print("✅ Models downloaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading models: {e}")
        return False

def run_interface():
    """Run the real-time interface"""
    try:
        print("\n🚀 Starting Real-Time Speech Analysis Interface...")
        print("📍 The interface will be available at: http://localhost:5000")
        print("🔊 Make sure your microphone is working and permissions are granted")
        print("⏹️  Press Ctrl+C to stop the server\n")
        
        # Import and run the Flask app
        from realtime_app import app, socketio
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        print("\n👋 Interface stopped by user")
    except Exception as e:
        print(f"❌ Error running interface: {e}")

def main():
    """Main startup function"""
    print("🎤 Real-Time Speech Analysis Interface")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('realtime_app.py'):
        print("❌ Error: realtime_app.py not found!")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"📦 Missing packages: {', '.join(missing)}")
        if input("Install missing dependencies? (y/n): ").lower().startswith('y'):
            if not install_dependencies():
                print("❌ Failed to install dependencies. Please install manually.")
                sys.exit(1)
        else:
            print("❌ Cannot proceed without required dependencies.")
            sys.exit(1)
    else:
        print("✅ All dependencies are installed!")
    
    # Download models
    print("\n🤖 Checking ML models...")
    if not download_models():
        print("❌ Failed to download required models.")
        sys.exit(1)
    
    # Run the interface
    print("\n" + "=" * 50)
    run_interface()

if __name__ == "__main__":
    main()