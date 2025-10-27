from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import base64
import io
import wave
import numpy as np
from faster_whisper import WhisperModel
from transformers import pipeline
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json
import os
from datetime import datetime
import threading
import queue
import time
import librosa

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize models
print("Loading models...")
whisper_model = WhisperModel("base", compute_type="int8")
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
sentiment_analyzer = SentimentIntensityAnalyzer()

# Global variables for session management
active_sessions = {}
transcription_buffer = {}

class SimpleVAD:
    """Simple Voice Activity Detection using energy threshold"""
    def __init__(self, threshold=0.01, frame_duration=30):
        self.threshold = threshold
        self.frame_duration = frame_duration
    
    def is_speech(self, audio_data, sample_rate=16000):
        """Simple energy-based voice activity detection"""
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > self.threshold

class AudioProcessor:
    def __init__(self):
        self.vad = SimpleVAD()
        self.sample_rate = 16000
        self.chunk_duration = 2.0  # seconds
        
    def process_audio_chunk(self, audio_data):
        """Process audio chunk and return transcription if speech detected"""
        try:
            # Convert to numpy array if needed
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio_array = audio_data
            
            # Check if speech is detected
            if self.vad.is_speech(audio_array):
                # Transcribe using Whisper
                segments, info = whisper_model.transcribe(audio_array, language="en")
                
                transcription = ""
                for segment in segments:
                    transcription += segment.text + " "
                
                return transcription.strip(), True
            
            return "", False
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            return "", False

class SpeakerManager:
    def __init__(self):
        self.speakers = {}
        self.current_speaker_id = 0
        
    def identify_speaker(self, audio_features):
        """Simple speaker identification based on audio features"""
        # For now, return a default speaker. In a more advanced version,
        # you could implement speaker diarization
        return "Speaker_1"
    
    def add_speaker_text(self, speaker_id, text, timestamp):
        """Add text for a specific speaker"""
        if speaker_id not in self.speakers:
            self.speakers[speaker_id] = {
                'texts': [],
                'timestamps': [],
                'full_text': ""
            }
        
        self.speakers[speaker_id]['texts'].append(text)
        self.speakers[speaker_id]['timestamps'].append(timestamp)
        self.speakers[speaker_id]['full_text'] += " " + text

# Initialize processors
audio_processor = AudioProcessor()
speaker_manager = SpeakerManager()

@app.route('/')
def index():
    return render_template('realtime_interface.html')

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    active_sessions[session_id] = {
        'transcription': "",
        'speakers': {},
        'start_time': datetime.now()
    }
    print(f"Client connected: {session_id}")
    emit('status', {'message': 'Connected to speech analysis server'})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in active_sessions:
        del active_sessions[session_id]
    print(f"Client disconnected: {session_id}")

@socketio.on('audio_data')
def handle_audio_data(data):
    session_id = request.sid
    
    try:
        # Decode audio data
        audio_bytes = base64.b64decode(data['audio'])
        
        # Process audio
        transcription, has_speech = audio_processor.process_audio_chunk(audio_bytes)
        
        if has_speech and transcription:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Identify speaker (simplified)
            speaker_id = "Speaker_1"  # For now, single speaker
            
            # Add to session
            if session_id in active_sessions:
                active_sessions[session_id]['transcription'] += f" {transcription}"
                
                # Add to speaker manager
                speaker_manager.add_speaker_text(speaker_id, transcription, timestamp)
                
                # Emit real-time transcription
                emit('transcription', {
                    'text': transcription,
                    'speaker': speaker_id,
                    'timestamp': timestamp,
                    'full_text': active_sessions[session_id]['transcription']
                })
    
    except Exception as e:
        print(f"Error handling audio data: {e}")
        emit('error', {'message': f'Error processing audio: {str(e)}'})

@socketio.on('stop_recording')
def handle_stop_recording():
    session_id = request.sid
    
    if session_id not in active_sessions:
        return
    
    try:
        full_text = active_sessions[session_id]['transcription']
        
        if not full_text.strip():
            emit('error', {'message': 'No speech detected to process'})
            return
        
        # Generate summary
        if len(full_text.split()) > 10:  # Only summarize if enough content
            try:
                summary_result = summarizer(full_text, max_length=150, min_length=30, do_sample=False)
                summary = summary_result[0]['summary_text']
            except:
                summary = "Summary generation failed. Text might be too short or unclear."
        else:
            summary = full_text  # Use original text if too short
        
        # Perform sentiment analysis
        sentiment_scores = sentiment_analyzer.polarity_scores(full_text)
        
        # Determine overall sentiment
        if sentiment_scores['compound'] >= 0.05:
            overall_sentiment = 'Positive'
        elif sentiment_scores['compound'] <= -0.05:
            overall_sentiment = 'Negative'
        else:
            overall_sentiment = 'Neutral'
        
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
            'speakers': dict(speaker_manager.speakers),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        emit('analysis_complete', results)
        
    except Exception as e:
        print(f"Error in analysis: {e}")
        emit('error', {'message': f'Analysis failed: {str(e)}'})

@socketio.on('download_results')
def handle_download_results():
    session_id = request.sid
    
    if session_id not in active_sessions:
        return
    
    try:
        full_text = active_sessions[session_id]['transcription']
        
        # Create downloadable content
        content = {
            'transcription': full_text,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'speakers': dict(speaker_manager.speakers)
        }
        
        emit('download_ready', {
            'content': json.dumps(content, indent=2),
            'filename': f'speech_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        })
        
    except Exception as e:
        emit('error', {'message': f'Download preparation failed: {str(e)}'})

if __name__ == '__main__':
    print("Starting Real-Time Speech Analysis Interface...")
    print("Open your browser and go to: http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)