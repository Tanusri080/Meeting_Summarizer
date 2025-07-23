from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import base64
import io
import wave
import numpy as np
import json
import os
from datetime import datetime

# Import with error handling
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize models
print("Loading models...")

# Initialize Whisper with the smallest model
whisper_model = None
if WHISPER_AVAILABLE:
    try:
        whisper_model = WhisperModel("tiny.en", compute_type="int8", num_workers=1)
        print("✅ Whisper tiny.en model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load Whisper model: {e}")
        print("🔄 Trying alternative settings...")
        try:
            whisper_model = WhisperModel("tiny", compute_type="float32", num_workers=1)
            print("✅ Whisper tiny model loaded with float32")
        except Exception as e2:
            print(f"❌ All Whisper models failed: {e2}")
            whisper_model = None

# Initialize sentiment analyzer
sentiment_analyzer = None
if VADER_AVAILABLE:
    try:
        sentiment_analyzer = SentimentIntensityAnalyzer()
        print("✅ Sentiment analyzer loaded")
    except Exception as e:
        print(f"❌ Sentiment analyzer failed: {e}")

# Global variables
active_sessions = {}

def save_audio_for_debug(audio_data, filename="debug_audio.wav"):
    """Save audio data to file for debugging"""
    try:
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_data)
        print(f"🎵 Audio saved to {filename} for debugging")
    except Exception as e:
        print(f"❌ Failed to save audio: {e}")

def process_audio_simple(audio_bytes):
    """Simple audio processing with detailed logging"""
    try:
        print(f"🎤 Processing audio chunk: {len(audio_bytes)} bytes")
        
        # Convert bytes to numpy array
        if len(audio_bytes) < 1024:  # Too short
            print("⚠️ Audio chunk too short, skipping")
            return "", False
        
        # Convert to 16-bit integers then to float32
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0
        
        print(f"🔢 Audio array shape: {audio_float.shape}, range: [{audio_float.min():.3f}, {audio_float.max():.3f}]")
        
        # Check if there's actual audio content
        rms = np.sqrt(np.mean(audio_float**2))
        print(f"📊 Audio RMS energy: {rms:.6f}")
        
        if rms < 0.001:  # Very quiet
            print("🔇 Audio too quiet, likely silence")
            return "", False
        
        # Save for debugging (optional)
        # save_audio_for_debug(audio_bytes, f"debug_{datetime.now().strftime('%H%M%S')}.wav")
        
        if whisper_model:
            print("🎯 Sending to Whisper...")
            try:
                segments, info = whisper_model.transcribe(
                    audio_float,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                transcription = ""
                segment_count = 0
                for segment in segments:
                    transcription += segment.text + " "
                    segment_count += 1
                    print(f"📝 Segment {segment_count}: '{segment.text.strip()}'")
                
                if transcription.strip():
                    print(f"✅ Transcription successful: '{transcription.strip()}'")
                    return transcription.strip(), True
                else:
                    print("❌ No transcription generated")
                    return "", False
                    
            except Exception as e:
                print(f"❌ Whisper transcription error: {e}")
                return "", False
        else:
            print("❌ Whisper model not available")
            return "Speech detected (Whisper not loaded)", True
            
    except Exception as e:
        print(f"❌ Audio processing error: {e}")
        return "", False

@app.route('/')
def index():
    return render_template('realtime_interface_fixed.html')

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    active_sessions[session_id] = {
        'transcription': "",
        'start_time': datetime.now()
    }
    print(f"👤 Client connected: {session_id}")
    emit('status', {'message': 'Connected! Ready to transcribe speech.'})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in active_sessions:
        del active_sessions[session_id]
    print(f"👋 Client disconnected: {session_id}")

@socketio.on('audio_data')
def handle_audio_data(data):
    session_id = request.sid
    print(f"📡 Received audio data from {session_id}")
    
    try:
        # Decode audio data
        audio_bytes = base64.b64decode(data['audio'])
        print(f"🔄 Decoded {len(audio_bytes)} bytes of audio data")
        
        # Process audio
        transcription, has_speech = process_audio_simple(audio_bytes)
        
        if has_speech and transcription:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to session
            if session_id in active_sessions:
                active_sessions[session_id]['transcription'] += f" {transcription}"
                
                print(f"📤 Sending transcription: '{transcription}'")
                
                # Emit real-time transcription
                emit('transcription', {
                    'text': transcription,
                    'speaker': "Speaker_1",
                    'timestamp': timestamp,
                    'full_text': active_sessions[session_id]['transcription'].strip()
                })
        else:
            print("🔇 No speech detected in this chunk")
    
    except Exception as e:
        print(f"❌ Error handling audio data: {e}")
        emit('error', {'message': f'Error processing audio: {str(e)}'})

@socketio.on('stop_recording')
def handle_stop_recording(data=None):
    session_id = request.sid
    print(f"🛑 Stop recording requested by {session_id}")
    
    if session_id not in active_sessions:
        print("❌ Session not found")
        return
    
    try:
        full_text = active_sessions[session_id]['transcription'].strip()
        print(f"📄 Full transcription: '{full_text}'")
        
        if not full_text:
            print("❌ No transcription available")
            emit('error', {'message': 'No speech was detected. Please try speaking louder or closer to the microphone.'})
            return
        
        # Simple summary (just use first sentence or truncate)
        summary = full_text
        if len(full_text.split()) > 20:
            words = full_text.split()[:15]
            summary = ' '.join(words) + "..."
        
        # Simple sentiment analysis
        sentiment_scores = {'compound': 0, 'pos': 0, 'neg': 0, 'neu': 1}
        overall_sentiment = 'Neutral'
        
        if sentiment_analyzer:
            try:
                sentiment_scores = sentiment_analyzer.polarity_scores(full_text)
                if sentiment_scores['compound'] >= 0.05:
                    overall_sentiment = 'Positive'
                elif sentiment_scores['compound'] <= -0.05:
                    overall_sentiment = 'Negative'
                else:
                    overall_sentiment = 'Neutral'
            except Exception as e:
                print(f"❌ Sentiment analysis error: {e}")
        
        # Prepare results
        results = {
            'original_text': full_text,
            'summary': summary,
            'sentiment': {
                'overall': overall_sentiment,
                'scores': sentiment_scores,
                'positive': sentiment_scores['pos'],
                'negative': sentiment_scores['neg'],
                'neutral': sentiment_scores['neu']
            },
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print("📊 Sending analysis results")
        emit('analysis_complete', results)
        
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        emit('error', {'message': f'Analysis failed: {str(e)}'})

@socketio.on('download_results')
def handle_download_results(data=None):
    session_id = request.sid
    
    if session_id not in active_sessions:
        return
    
    try:
        full_text = active_sessions[session_id]['transcription'].strip()
        
        content = {
            'transcription': full_text,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        emit('download_ready', {
            'content': json.dumps(content, indent=2),
            'filename': f'speech_transcript_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        })
        
    except Exception as e:
        emit('error', {'message': f'Download failed: {str(e)}'})

if __name__ == '__main__':
    print("=" * 60)
    print("🎤 Simple Speech Analysis Interface")
    print("=" * 60)
    print("📊 Status:")
    print(f"   Whisper: {'✅ Available' if whisper_model else '❌ Not available'}")
    print(f"   Sentiment: {'✅ Available' if sentiment_analyzer else '❌ Not available'}")
    print("=" * 60)
    print("🌐 Starting server...")
    print("📱 Open your browser: http://localhost:5000")
    print("🎙️ Allow microphone access when prompted")
    print("🗣️ Speak clearly and loudly for best results")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"❌ Server failed: {e}")
        input("Press Enter to exit...")