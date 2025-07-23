#!/usr/bin/env python3
"""
Diagnostic script to test your Python environment and dependencies
Run this first to identify issues before running the main application
"""

import sys
import subprocess
import importlib.util

def check_python_version():
    """Check if Python version is compatible"""
    print("=== Python Version Check ===")
    print(f"Python version: {sys.version}")
    
    version_info = sys.version_info
    if version_info.major == 3 and version_info.minor >= 8:
        print("✅ Python version is compatible")
        return True
    else:
        print("❌ Python version too old. Need Python 3.8+")
        return False

def check_package(package_name, import_name=None):
    """Check if a package is installed and can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        # Try to import the package
        importlib.import_module(import_name)
        print(f"✅ {package_name} is installed and working")
        return True
    except ImportError:
        print(f"❌ {package_name} is not installed or not working")
        return False

def test_basic_dependencies():
    """Test basic dependencies"""
    print("\n=== Basic Dependencies Check ===")
    
    dependencies = [
        ("flask", "flask"),
        ("flask-socketio", "flask_socketio"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
    ]
    
    all_good = True
    for package, import_name in dependencies:
        if not check_package(package, import_name):
            all_good = False
    
    return all_good

def test_ai_dependencies():
    """Test AI/ML dependencies"""
    print("\n=== AI/ML Dependencies Check ===")
    
    dependencies = [
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("faster-whisper", "faster_whisper"),
        ("textblob", "textblob"),
        ("vaderSentiment", "vaderSentiment"),
        ("librosa", "librosa"),
        ("scikit-learn", "sklearn"),
    ]
    
    all_good = True
    for package, import_name in dependencies:
        if not check_package(package, import_name):
            all_good = False
    
    return all_good

def test_audio_dependencies():
    """Test audio processing dependencies"""
    print("\n=== Audio Dependencies Check ===")
    
    dependencies = [
        ("sounddevice", "sounddevice"),
        ("pydub", "pydub"),
    ]
    
    all_good = True
    for package, import_name in dependencies:
        if not check_package(package, import_name):
            all_good = False
    
    return all_good

def test_file_structure():
    """Check if required files exist"""
    print("\n=== File Structure Check ===")
    
    import os
    
    required_files = [
        "realtime_app_windows.py",
        "templates/realtime_interface.html",
    ]
    
    all_good = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} is missing")
            all_good = False
    
    return all_good

def provide_solutions():
    """Provide solutions for common issues"""
    print("\n=== Solutions ===")
    print("If you see missing dependencies above, try these commands in order:")
    print()
    print("1. Create/activate virtual environment:")
    print("   python -m venv speech_env")
    print("   speech_env\\Scripts\\activate")
    print()
    print("2. Upgrade pip:")
    print("   python -m pip install --upgrade pip")
    print()
    print("3. Install dependencies step by step:")
    print("   pip install flask flask-socketio")
    print("   pip install numpy scipy")
    print("   pip install torch --index-url https://download.pytorch.org/whl/cpu")
    print("   pip install transformers faster-whisper")
    print("   pip install textblob vaderSentiment")
    print("   pip install librosa scikit-learn")
    print("   pip install sounddevice pydub")
    print()
    print("4. If you get Visual C++ errors:")
    print("   - Install Microsoft C++ Build Tools")
    print("   - Or try: pip install --only-binary=all [package_name]")
    print()
    print("5. Download NLTK data:")
    print("   python -c \"import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')\"")

def main():
    """Main diagnostic function"""
    print("🔍 Real-Time Speech Analysis - Diagnostic Tool")
    print("=" * 50)
    
    # Run all checks
    python_ok = check_python_version()
    basic_ok = test_basic_dependencies()
    ai_ok = test_ai_dependencies()
    audio_ok = test_audio_dependencies()
    files_ok = test_file_structure()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    if python_ok and basic_ok and ai_ok and audio_ok and files_ok:
        print("🎉 All checks passed! You should be able to run the application.")
        print("Run: python realtime_app_windows.py")
    else:
        print("⚠️  Some issues found. See solutions below.")
        provide_solutions()

if __name__ == "__main__":
    main()