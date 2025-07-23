# Real-Time Speech Analysis Interface - Windows Setup Guide

## Prerequisites

1. **Python 3.8 or higher** installed on your system
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Git** (optional, if you want to clone from repository)
   - Download from: https://git-scm.com/download/win

## Quick Setup (Automated)

### Option 1: Automated Setup
1. Open Command Prompt or PowerShell as Administrator
2. Navigate to your project folder
3. Run the setup script:
   ```cmd
   setup_windows.bat
   ```
4. Wait for installation to complete
5. Run the application:
   ```cmd
   run_app.bat
   ```

## Manual Setup (If automated setup fails)

### Step 1: Create Virtual Environment
```cmd
python -m venv speech_env
speech_env\Scripts\activate.bat
```

### Step 2: Upgrade pip
```cmd
python -m pip install --upgrade pip
```

### Step 3: Install Dependencies (One by one if needed)
```cmd
# Core dependencies
pip install flask flask-socketio

# AI/ML dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers faster-whisper

# Audio processing
pip install numpy scipy librosa sounddevice

# Text analysis
pip install textblob vaderSentiment scikit-learn

# Additional utilities
pip install python-socketio eventlet pydub
```

### Step 4: Download NLTK Data (Required for TextBlob)
```python
python -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')"
```

## Running the Application

### Method 1: Using Batch File
```cmd
run_app.bat
```

### Method 2: Manual
```cmd
speech_env\Scripts\activate.bat
python realtime_app_windows.py
```

## Accessing the Interface

1. Open your web browser
2. Go to: `http://localhost:5000`
3. Allow microphone access when prompted

## Features

- **Real-time Speech-to-Text**: Live transcription as you speak
- **Sentiment Analysis**: Analyzes emotional tone of speech
- **Text Summarization**: Generates concise summaries
- **Multi-speaker Support**: Handles multiple speakers (basic implementation)
- **Download Results**: Export transcriptions and analysis
- **Share Functionality**: Easy sharing of results

## Usage Instructions

1. **Start Recording**: Click the "Start Recording" button
2. **Speak**: Talk into your microphone - text will appear in real-time
3. **Stop Recording**: Click "Stop Recording" when finished
4. **View Results**: See transcription, summary, and sentiment analysis
5. **Download/Share**: Use the provided options to save or share results

## Troubleshooting

### Common Issues:

1. **Microphone not working**:
   - Check browser permissions
   - Ensure microphone is not muted
   - Try refreshing the page

2. **Models loading slowly**:
   - First run downloads AI models (may take time)
   - Subsequent runs will be faster

3. **Port already in use**:
   - Change port in `realtime_app_windows.py` line: `socketio.run(app, host='0.0.0.0', port=5001, debug=True)`

4. **Installation errors**:
   - Try running Command Prompt as Administrator
   - Update Python to latest version
   - Install Visual Studio Build Tools if needed

### Performance Tips:

- Close other applications using microphone
- Use a good quality microphone for better results
- Speak clearly and at moderate pace
- Ensure stable internet connection for model downloads

## File Structure

```
project/
├── realtime_app_windows.py      # Main application file
├── requirements_windows.txt     # Python dependencies
├── setup_windows.bat           # Automated setup script
├── run_app.bat                 # Application runner
├── templates/
│   └── realtime_interface.html # Web interface
└── speech_env/                 # Virtual environment (created during setup)
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Ensure all prerequisites are installed
3. Try the manual setup method
4. Check Python and pip versions: `python --version` and `pip --version`

## Advanced Configuration

You can modify the following in `realtime_app_windows.py`:
- Change Whisper model size (base, small, medium, large)
- Adjust voice activity detection threshold
- Modify summarization parameters
- Change server port and host settings