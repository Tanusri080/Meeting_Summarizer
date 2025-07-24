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
print("⚠️ Skipping Whisper due to memory constraints")
print("✅ Using strict audio detection")

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
consecutive_speech_chunks = 0
background_noise_level = 0.0

def calculate_background_noise(audio_float):
    """Calculate background noise level for adaptive thresholding"""
    global background_noise_level
    rms = np.sqrt(np.mean(audio_float**2))
    
    # Update background noise level (moving average)
    if background_noise_level == 0.0:
        background_noise_level = rms
    else:
        background_noise_level = 0.9 * background_noise_level + 0.1 * rms
    
    return background_noise_level

def is_likely_speech(audio_float):
    """More sophisticated speech detection"""
    try:
        # Calculate various audio features
        rms = np.sqrt(np.mean(audio_float**2))
        
        # Calculate zero crossing rate (speech has more zero crossings than noise)
        zero_crossings = np.sum(np.diff(np.sign(audio_float)) != 0)
        zero_crossing_rate = zero_crossings / len(audio_float)
        
        # Calculate spectral centroid (rough measure of brightness)
        # Higher frequency content often indicates speech
        fft = np.abs(np.fft.fft(audio_float))
        freqs = np.fft.fftfreq(len(audio_float), 1/16000)
        spectral_centroid = np.sum(freqs[:len(freqs)//2] * fft[:len(fft)//2]) / np.sum(fft[:len(fft)//2])
        
        # Update background noise
        bg_noise = calculate_background_noise(audio_float)
        
        print(f"📊 RMS: {rms:.6f}, ZCR: {zero_crossing_rate:.4f}, SC: {spectral_centroid:.1f}Hz, BG: {bg_noise:.6f}")
        
        # Strict thresholds
        min_rms_threshold = max(0.01, bg_noise * 3)  # At least 3x background noise
        min_zero_crossing_rate = 0.05  # Speech has reasonable zero crossings
        max_zero_crossing_rate = 0.3   # But not too many (noise)
        min_spectral_centroid = 200    # Speech usually has energy above 200Hz
        max_spectral_centroid = 4000   # But not too high (noise/feedback)
        
        # Check all conditions
        rms_ok = rms > min_rms_threshold
        zcr_ok = min_zero_crossing_rate < zero_crossing_rate < max_zero_crossing_rate
        sc_ok = min_spectral_centroid < spectral_centroid < max_spectral_centroid
        
        print(f"🔍 Checks - RMS: {rms_ok} ({rms:.6f}>{min_rms_threshold:.6f})")
        print(f"🔍 Checks - ZCR: {zcr_ok} ({zero_crossing_rate:.4f} in [{min_zero_crossing_rate}, {max_zero_crossing_rate}])")
        print(f"🔍 Checks - SC: {sc_ok} ({spectral_centroid:.1f}Hz in [{min_spectral_centroid}, {max_spectral_centroid}])")
        
        # All conditions must be met
        is_speech = rms_ok and zcr_ok and sc_ok
        
        return is_speech, rms, zero_crossing_rate, spectral_centroid
        
    except Exception as e:
        print(f"❌ Speech detection error: {e}")
        return False, 0, 0, 0

def process_audio_strict(audio_bytes):
    """Process audio with strict speech detection"""
    global consecutive_speech_chunks
    
    try:
        print(f"\n🎤 Processing chunk #{audio_chunk_count}: {len(audio_bytes)} bytes")
        
        if len(audio_bytes) < 1024:
            print("⚠️ Audio chunk too short")
            return "", False
        
        # Convert to numpy array
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0
        
        # Detect speech with multiple criteria
        is_speech, rms, zcr, sc = is_likely_speech(audio_float)
        
        if is_speech:
            consecutive_speech_chunks += 1
            print(f"🎯 SPEECH DETECTED! (consecutive: {consecutive_speech_chunks})")
            
            # Only return transcription after multiple consecutive speech chunks
            # This reduces false positives from brief noise spikes
            if consecutive_speech_chunks >= 2:
                # Save audio for verification
                debug_filename = f"speech_chunk_{audio_chunk_count:03d}.wav"
                save_audio_file(audio_bytes, debug_filename)
                
                demo_text = f"Speech detected (chunk {audio_chunk_count})"
                
                # Add quality indicator
                if rms > 0.05:
                    demo_text += " - excellent quality"
                elif rms > 0.02:
                    demo_text += " - good quality"
                else:
                    demo_text += " - acceptable quality"
                
                print(f"✅ Transcription: '{demo_text}'")
                return demo_text, True
            else:
                print(f"⏳ Need more consecutive speech chunks ({consecutive_speech_chunks}/2)")
                return "", False
        else:
            consecutive_speech_chunks = 0  # Reset counter
            print(f"🔇 Not speech - likely background noise")
            return "", False
            
    except Exception as e:
        print(f"❌ Audio processing error: {e}")
        return "", False

def save_audio_file(audio_data, filename):
    """Save audio for debugging"""
    try:
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_data)
        print(f"🎵 Saved: {filename}")
    except Exception as e:
        print(f"❌ Save failed: {e}")

@app.route('/')
def index():
    return render_template('realtime_interface.html')

@socketio.on('connect')
def handle_connect():
    global background_noise_level, consecutive_speech_chunks
    session_id = request.sid
    active_sessions[session_id] = {
        'transcription': "",
        'start_time': datetime.now()
    }
    # Reset background noise calculation for new session
    background_noise_level = 0.0
    consecutive_speech_chunks = 0
    print(f"👤 Client connected: {session_id}")
    emit('status', {'message': 'Connected! Strict audio detection enabled. Speak clearly and loudly.'})

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
    
    print(f"\n📡 Audio chunk #{audio_chunk_count} from {session_id}")
    
    try:
        # Decode audio data
        audio_bytes = base64.b64decode(data['audio'])
        
        # Process with strict detection
        transcription, has_speech = process_audio_strict(audio_bytes)
        
        if has_speech and transcription:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to session
            if session_id in active_sessions:
                active_sessions[session_id]['transcription'] += f" {transcription}"
                
                print(f"📤 SENDING: '{transcription}'")
                
                # Emit real-time transcription
                emit('transcription', {
                    'text': transcription,
                    'speaker': "Speaker_1",
                    'timestamp': timestamp,
                    'full_text': active_sessions[session_id]['transcription'].strip()
                })
        else:
            print("🔇 No valid speech detected")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        emit('error', {'message': f'Error processing audio: {str(e)}'})

@socketio.on('stop_recording')
def handle_stop_recording(data=None):
    global consecutive_speech_chunks
    session_id = request.sid
    consecutive_speech_chunks = 0  # Reset for next recording
    
    print(f"\n🛑 Stop recording - {session_id}")
    print(f"📊 Total chunks processed: {audio_chunk_count}")
    
    if session_id not in active_sessions:
        return
    
    try:
        full_text = active_sessions[session_id]['transcription'].strip()
        print(f"📄 Full transcription: '{full_text}'")
        
        if not full_text:
            emit('error', {'message': 'No clear speech detected. Try speaking louder and more clearly, or check your microphone settings.'})
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
            'note': 'Strict detection mode - only clear speech is detected'
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
            'background_noise_level': background_noise_level,
            'note': 'Strict detection mode - background noise filtered out'
        }
        
        emit('download_ready', {
            'content': json.dumps(content, indent=2),
            'filename': f'speech_strict_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        })
        
    except Exception as e:
        emit('error', {'message': f'Download failed: {str(e)}'})

if __name__ == '__main__':
    print("=" * 60)
    print("🎤 Strict Audio Detection Interface")
    print("=" * 60)
    print("📊 Features:")
    print("   ✅ Strict speech detection (filters background noise)")
    print("   ✅ Adaptive background noise filtering")
    print("   ✅ Multiple audio feature analysis")
    print("   ✅ Consecutive chunk requirement")
    print("   ❌ Whisper disabled (memory issues)")
    print("=" * 60)
    print("🌐 Starting server...")
    print("📱 Open: http://localhost:5000")
    print("🎙️ Speak CLEARLY and LOUDLY for detection")
    print("🔇 Background noise will be ignored")
    print("📊 Watch terminal for detailed audio analysis")
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"❌ Server failed: {e}")
        input("Press Enter to exit...")