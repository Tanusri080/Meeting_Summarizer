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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize models
print("Loading models...")
whisper_model = WhisperModel("base", compute_type="int8")
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
sentiment_analyzer = SentimentIntensityAnalyzer()
print("Models loaded successfully!")

# Global variables for audio processing
audio_buffer = queue.Queue()
is_recording = False
current_session = {}

class AudioProcessor:
    def __init__(self):
        self.sessions = {}
        
    def create_session(self, session_id):
        self.sessions[session_id] = {
            'audio_chunks': [],
            'transcripts': [],
            'speakers': {},
            'current_text': '',
            'is_speaking': False,
            'last_activity': time.time()
        }
    
    def add_audio_chunk(self, session_id, audio_data):
        if session_id not in self.sessions:
            self.create_session(session_id)
        
        self.sessions[session_id]['audio_chunks'].append(audio_data)
        self.sessions[session_id]['last_activity'] = time.time()
    
    def process_audio_chunk(self, session_id, audio_data):
        try:
            # Convert base64 audio to wav format
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
            
            # Save temporary file
            temp_path = f"temp_audio_{session_id}.wav"
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            
            # Transcribe
            segments, info = whisper_model.transcribe(temp_path)
            
            transcript_text = ""
            for segment in segments:
                transcript_text += segment.text + " "
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return transcript_text.strip()
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            return ""
    
    def analyze_sentiment(self, text):
        # Using VADER sentiment analyzer
        vader_scores = sentiment_analyzer.polarity_scores(text)
        
        # Using TextBlob for additional analysis
        blob = TextBlob(text)
        textblob_sentiment = blob.sentiment.polarity
        
        # Combine results
        sentiment_result = {
            'vader': {
                'compound': vader_scores['compound'],
                'positive': vader_scores['pos'],
                'neutral': vader_scores['neu'],
                'negative': vader_scores['neg']
            },
            'textblob_polarity': textblob_sentiment,
            'overall_sentiment': self.get_overall_sentiment(vader_scores['compound'])
        }
        
        return sentiment_result
    
    def get_overall_sentiment(self, compound_score):
        if compound_score >= 0.05:
            return "Positive"
        elif compound_score <= -0.05:
            return "Negative"
        else:
            return "Neutral"
    
    def generate_summary(self, text):
        if len(text.strip()) < 50:
            return "Text too short for meaningful summary."
        
        try:
            # Limit text length for the model
            max_length = 1024
            if len(text) > max_length:
                text = text[:max_length]
            
            summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            return f"Error generating summary: {str(e)}"

audio_processor = AudioProcessor()

@app.route('/')
def index():
    return render_template('realtime_interface.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_recording')
def handle_start_recording(data):
    session_id = data.get('session_id', 'default')
    audio_processor.create_session(session_id)
    print(f"Started recording session: {session_id}")
    emit('recording_started', {'session_id': session_id})

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    session_id = data.get('session_id', 'default')
    audio_data = data.get('audio_data')
    
    if audio_data:
        # Process audio in a separate thread to avoid blocking
        def process_and_emit():
            transcript = audio_processor.process_audio_chunk(session_id, audio_data)
            if transcript:
                # Emit real-time transcript
                socketio.emit('real_time_transcript', {
                    'session_id': session_id,
                    'transcript': transcript,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Store transcript for later processing
                if session_id in audio_processor.sessions:
                    audio_processor.sessions[session_id]['transcripts'].append({
                        'text': transcript,
                        'timestamp': datetime.now().isoformat()
                    })
        
        thread = threading.Thread(target=process_and_emit)
        thread.daemon = True
        thread.start()

@socketio.on('stop_recording')
def handle_stop_recording(data):
    session_id = data.get('session_id', 'default')
    
    if session_id in audio_processor.sessions:
        session_data = audio_processor.sessions[session_id]
        
        # Combine all transcripts
        full_text = " ".join([t['text'] for t in session_data['transcripts']])
        
        if full_text.strip():
            # Generate summary
            summary = audio_processor.generate_summary(full_text)
            
            # Analyze sentiment
            sentiment = audio_processor.analyze_sentiment(full_text)
            
            # Prepare final result
            result = {
                'session_id': session_id,
                'full_transcript': full_text,
                'summary': summary,
                'sentiment_analysis': sentiment,
                'transcript_segments': session_data['transcripts'],
                'timestamp': datetime.now().isoformat()
            }
            
            emit('processing_complete', result)
        else:
            emit('error', {'message': 'No speech detected in the recording'})

@socketio.on('download_transcript')
def handle_download_transcript(data):
    session_id = data.get('session_id', 'default')
    
    if session_id in audio_processor.sessions:
        session_data = audio_processor.sessions[session_id]
        full_text = " ".join([t['text'] for t in session_data['transcripts']])
        
        # Create downloadable content
        content = {
            'transcript': full_text,
            'summary': audio_processor.generate_summary(full_text),
            'sentiment': audio_processor.analyze_sentiment(full_text),
            'timestamp': datetime.now().isoformat()
        }
        
        emit('download_ready', {
            'filename': f'transcript_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            'content': json.dumps(content, indent=2)
        })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'models_loaded': True})

if __name__ == '__main__':
    os.makedirs("recordings", exist_ok=True)
    print("Starting Real-Time Speech Analysis Interface...")
    print("Access the interface at: http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)