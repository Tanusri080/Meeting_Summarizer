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
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize models
print("Loading models...")

# Skip Whisper for now due to memory issues
print("⚠️ Skipping Whisper due to memory constraints")
print("✅ Using fallback transcription for demo")

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
audio_chunk_count = 0

def save_debug_audio(audio_data, filename):
    """Save audio for debugging"""
    try:
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_data)
        print(f"🎵 Audio saved: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to save audio: {e}")
        return False

def process_audio_simple(audio_bytes):
    """Process audio without Whisper - demo version"""
    try:
        print(f"🎤 Processing audio chunk #{audio_chunk_count}: {len(audio_bytes)} bytes")
        
        if len(audio_bytes) < 1024:
            print("⚠️ Audio chunk too short")
            return "", False
        
        # Convert to numpy array
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0
        
        # Calculate audio metrics
        rms = np.sqrt(np.mean(audio_float**2))
        max_amplitude = np.max(np.abs(audio_float))
        
        print(f"📊 RMS: {rms:.6f}, Max: {max_amplitude:.6f}")
        
        # Save debug audio
        debug_filename = f"audio_chunk_{audio_chunk_count:03d}.wav"
        audio_saved = save_debug_audio(audio_bytes, debug_filename)
        
        # Check for speech activity
        silence_threshold = 0.001
        speech_threshold = 0.005  # Lower threshold since we can't use Whisper
        
        if rms < silence_threshold:
            print(f"🔇 Silence (RMS {rms:.6f})")
            return "", False
        elif rms >= speech_threshold:
            print(f"🎯 Speech detected (RMS {rms:.6f})")
            
            # Create a demo transcription based on audio characteristics
            if rms > 0.02:
                demo_text = f"Clear speech detected (strong audio signal)"
            elif rms > 0.01:
                demo_text = f"Speech detected (moderate audio signal)"
            else:
                demo_text = f"Quiet speech detected (weak audio signal)"
            
            # Add some variety based on chunk number
            if audio_chunk_count % 5 == 0:
                demo_text += " - processing complete"
            elif audio_chunk_count % 3 == 0:
                demo_text += " - good audio quality"
            
            print(f"✅ Demo transcription: '{demo_text}'")
            return demo_text, True
        else:
            print(f"⚠️ Quiet audio (RMS {rms:.6f}) - might be background noise")
            return "", False
            
    except Exception as e:
        print(f"❌ Audio processing error: {e}")
        return "", False

@app.route('/')
def index():
    return render_template('realtime_interface.html')

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    active_sessions[session_id] = {
        'transcription': "",
        'start_time': datetime.now()
    }
    print(f"👤 Client connected: {session_id}")
    emit('status', {'message': 'Connected! Demo version - speak to test audio detection.'})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in active_sessions:
        del active_sessions[session_id]
    print(f"👋 Client disconnected: {session_id}")

@socketio.on('audio_data')
def handle_audio_data(data):
    global audio_chunk_count
    session_id = request.sid
    audio_chunk_count += 1
    
    print(f"\n📡 Audio data #{audio_chunk_count} from {session_id}")
    
    try:
        # Decode audio data
        audio_bytes = base64.b64decode(data['audio'])
        
        # Process audio
        transcription, has_speech = process_audio_simple(audio_bytes)
        
        if has_speech and transcription:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to session
            if session_id in active_sessions:
                active_sessions[session_id]['transcription'] += f" {transcription}"
                
                print(f"📤 Sending: '{transcription}'")
                
                # Emit real-time transcription
                emit('transcription', {
                    'text': transcription,
                    'speaker': "Speaker_1",
                    'timestamp': timestamp,
                    'full_text': active_sessions[session_id]['transcription'].strip()
                })
        else:
            print("🔇 No speech in this chunk")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        emit('error', {'message': f'Error processing audio: {str(e)}'})

@socketio.on('stop_recording')
def handle_stop_recording(data=None):
    session_id = request.sid
    print(f"\n🛑 Stop recording - {session_id}")
    print(f"📊 Total chunks processed: {audio_chunk_count}")
    
    if session_id not in active_sessions:
        return
    
    try:
        full_text = active_sessions[session_id]['transcription'].strip()
        print(f"📄 Full text: '{full_text}'")
        
        if not full_text:
            emit('error', {'message': 'No speech detected. Try speaking louder or check your microphone.'})
            return
        
        # Simple summary
        summary = full_text
        if len(full_text.split()) > 15:
            words = full_text.split()[:10]
            summary = ' '.join(words) + "..."
        
        # Sentiment analysis
        sentiment_scores = {'compound': 0, 'pos': 0, 'neg': 0, 'neu': 1}
        overall_sentiment = 'Neutral'
        
        if sentiment_analyzer:
            try:
                sentiment_scores = sentiment_analyzer.polarity_scores(full_text)
                if sentiment_scores['compound'] >= 0.05:
                    overall_sentiment = 'Positive'
                elif sentiment_scores['compound'] <= -0.05:
                    overall_sentiment = 'Negative'
            except Exception as e:
                print(f"❌ Sentiment error: {e}")
        
        # Results
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
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'note': 'Demo version - using audio detection instead of speech recognition'
        }
        
        print("📊 Sending results")
        emit('analysis_complete', results)
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
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
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_chunks': audio_chunk_count,
            'note': 'Demo version - audio detection working, Whisper disabled due to memory constraints'
        }
        
        emit('download_ready', {
            'content': json.dumps(content, indent=2),
            'filename': f'speech_demo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        })
        
    except Exception as e:
        emit('error', {'message': f'Download failed: {str(e)}'})

if __name__ == '__main__':
    print("=" * 60)
    print("🎤 Simple Working Speech Interface (Demo Version)")
    print("=" * 60)
    print("📊 Status:")
    print("   Audio Detection: ✅ Working")
    print("   Whisper: ❌ Disabled (memory issues)")
    print("   Sentiment: ✅ Working")
    print("   Demo Mode: ✅ Enabled")
    print("=" * 60)
    print("🌐 Starting server...")
    print("📱 Open: http://localhost:5000")
    print("🎙️ This version will detect when you speak")
    print("📝 Demo transcription will show audio activity")
    print("🎵 Audio files saved as audio_chunk_XXX.wav")
    print("🔧 Once this works, we can fix Whisper memory issue")
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"❌ Server failed: {e}")
        input("Press Enter to exit...")