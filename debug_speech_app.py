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
audio_chunk_count = 0

def save_debug_audio(audio_data, filename):
    """Save audio for debugging"""
    try:
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_data)
        print(f"🎵 Debug audio saved: {filename}")
    except Exception as e:
        print(f"❌ Failed to save debug audio: {e}")

def analyze_audio_chunk(audio_bytes):
    """Analyze audio chunk and provide detailed information"""
    try:
        print(f"\n{'='*50}")
        print(f"🎤 AUDIO CHUNK ANALYSIS #{audio_chunk_count}")
        print(f"{'='*50}")
        
        # Basic info
        print(f"📊 Raw bytes length: {len(audio_bytes)}")
        
        if len(audio_bytes) < 1024:
            print("⚠️ Audio chunk too short, skipping")
            return "", False
        
        # Convert bytes to numpy array
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            print(f"🔢 Audio array shape: {audio_array.shape}")
            print(f"🔢 Audio array dtype: {audio_array.dtype}")
            print(f"🔢 Audio array range: [{audio_array.min()}, {audio_array.max()}]")
        except Exception as e:
            print(f"❌ Failed to convert bytes to array: {e}")
            return "", False
        
        # Convert to float32
        audio_float = audio_array.astype(np.float32) / 32768.0
        print(f"🔢 Float array range: [{audio_float.min():.6f}, {audio_float.max():.6f}]")
        
        # Calculate various audio metrics
        rms = np.sqrt(np.mean(audio_float**2))
        max_amplitude = np.max(np.abs(audio_float))
        mean_amplitude = np.mean(np.abs(audio_float))
        
        print(f"📊 RMS Energy: {rms:.6f}")
        print(f"📊 Max Amplitude: {max_amplitude:.6f}")
        print(f"📊 Mean Amplitude: {mean_amplitude:.6f}")
        
        # Check for silence
        silence_threshold = 0.001
        speech_threshold = 0.01
        
        if rms < silence_threshold:
            print(f"🔇 SILENCE DETECTED (RMS {rms:.6f} < {silence_threshold})")
            return "", False
        elif rms < speech_threshold:
            print(f"⚠️ QUIET AUDIO (RMS {rms:.6f} < {speech_threshold}) - might be background noise")
            # Let's try to process it anyway for debugging
        else:
            print(f"🎯 SPEECH DETECTED (RMS {rms:.6f} >= {speech_threshold})")
        
        # Save debug audio file
        debug_filename = f"debug_audio_{audio_chunk_count:03d}.wav"
        save_debug_audio(audio_bytes, debug_filename)
        
        # Try Whisper transcription
        if whisper_model:
            print("🎯 Sending to Whisper...")
            try:
                segments, info = whisper_model.transcribe(
                    audio_float,
                    language="en",
                    vad_filter=False,  # Disable VAD to see raw results
                    word_timestamps=True
                )
                
                print(f"📋 Whisper info: {info}")
                
                transcription = ""
                segment_count = 0
                for segment in segments:
                    segment_count += 1
                    segment_text = segment.text.strip()
                    print(f"📝 Segment {segment_count}: '{segment_text}' (confidence: {segment.avg_logprob:.3f})")
                    transcription += segment_text + " "
                
                if transcription.strip():
                    print(f"✅ TRANSCRIPTION SUCCESS: '{transcription.strip()}'")
                    return transcription.strip(), True
                else:
                    print("❌ NO TRANSCRIPTION GENERATED")
                    # Let's try forcing a result for very quiet audio
                    if rms > silence_threshold:
                        print("🔄 Trying alternative processing...")
                        return f"[Audio detected but unclear - RMS: {rms:.4f}]", True
                    return "", False
                    
            except Exception as e:
                print(f"❌ Whisper error: {e}")
                return f"[Whisper error: {str(e)}]", True
        else:
            print("❌ Whisper model not available")
            return f"[Audio detected - RMS: {rms:.4f}] - Whisper not loaded", True
            
    except Exception as e:
        print(f"❌ Audio analysis error: {e}")
        return "", False
    finally:
        print(f"{'='*50}\n")

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
    emit('status', {'message': 'Connected! Ready to transcribe speech.'})

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
    
    print(f"\n📡 RECEIVED AUDIO DATA #{audio_chunk_count} from {session_id}")
    
    try:
        # Decode audio data
        audio_bytes = base64.b64decode(data['audio'])
        print(f"🔄 Decoded {len(audio_bytes)} bytes of audio data")
        
        # Analyze audio in detail
        transcription, has_speech = analyze_audio_chunk(audio_bytes)
        
        if has_speech and transcription:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to session
            if session_id in active_sessions:
                active_sessions[session_id]['transcription'] += f" {transcription}"
                
                print(f"📤 SENDING TRANSCRIPTION: '{transcription}'")
                
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
    print(f"\n🛑 STOP RECORDING requested by {session_id}")
    print(f"📊 Total audio chunks processed: {audio_chunk_count}")
    
    if session_id not in active_sessions:
        print("❌ Session not found")
        return
    
    try:
        full_text = active_sessions[session_id]['transcription'].strip()
        print(f"📄 FULL TRANSCRIPTION: '{full_text}'")
        
        if not full_text:
            print("❌ No transcription available")
            emit('error', {'message': 'No speech was detected. Check the debug audio files or try speaking louder.'})
            return
        
        # Simple summary
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
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_chunks_processed': audio_chunk_count
        }
        
        emit('download_ready', {
            'content': json.dumps(content, indent=2),
            'filename': f'speech_transcript_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        })
        
    except Exception as e:
        emit('error', {'message': f'Download failed: {str(e)}'})

if __name__ == '__main__':
    print("=" * 60)
    print("🔍 DEBUG Speech Analysis Interface")
    print("=" * 60)
    print("📊 Status:")
    print(f"   Whisper: {'✅ Available' if whisper_model else '❌ Not available'}")
    print(f"   Sentiment: {'✅ Available' if sentiment_analyzer else '❌ Not available'}")
    print("=" * 60)
    print("🌐 Starting server...")
    print("📱 Open your browser: http://localhost:5000")
    print("🎙️ Allow microphone access when prompted")
    print("🗣️ Speak clearly and loudly for best results")
    print("🔍 This version will show detailed audio analysis")
    print("🎵 Audio files will be saved as debug_audio_XXX.wav")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"❌ Server failed: {e}")
        input("Press Enter to exit...")