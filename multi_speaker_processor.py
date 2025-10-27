import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import librosa
import webrtcvad
import io
import wave
from collections import defaultdict
import time

class MultiSpeakerProcessor:
    def __init__(self):
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2
        self.speakers = {}
        self.speaker_counter = 0
        self.speaker_embeddings = []
        self.speaker_labels = []
        
    def extract_speaker_features(self, audio_data, sample_rate=16000):
        """Extract speaker-specific features from audio"""
        try:
            # Extract MFCC features for speaker identification
            mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=13)
            
            # Extract spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sample_rate)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
            
            # Combine features
            features = np.concatenate([
                np.mean(mfccs, axis=1),
                np.mean(spectral_centroids),
                np.mean(spectral_rolloff),
                np.mean(zero_crossing_rate)
            ])
            
            return features
            
        except Exception as e:
            print(f"Error extracting speaker features: {e}")
            return np.zeros(16)  # Return zero vector if extraction fails
    
    def detect_voice_activity(self, audio_data, sample_rate=16000, frame_duration=30):
        """Detect voice activity in audio"""
        try:
            # Convert to 16-bit PCM if needed
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # VAD requires specific sample rates
            if sample_rate not in [8000, 16000, 32000, 48000]:
                # Resample to 16000 Hz
                audio_data = librosa.resample(audio_data.astype(float), 
                                            orig_sr=sample_rate, 
                                            target_sr=16000).astype(np.int16)
                sample_rate = 16000
            
            frame_size = int(sample_rate * frame_duration / 1000)
            frames = []
            
            for i in range(0, len(audio_data) - frame_size, frame_size):
                frame = audio_data[i:i + frame_size]
                is_speech = self.vad.is_speech(frame.tobytes(), sample_rate)
                frames.append(is_speech)
            
            return frames
            
        except Exception as e:
            print(f"Error in voice activity detection: {e}")
            return [True]  # Assume speech if VAD fails
    
    def identify_speaker(self, features):
        """Identify speaker based on extracted features"""
        if len(self.speaker_embeddings) == 0:
            # First speaker
            speaker_id = f"Speaker_{self.speaker_counter + 1}"
            self.speakers[speaker_id] = {
                'features': [features],
                'count': 1,
                'first_seen': time.time()
            }
            self.speaker_embeddings.append(features)
            self.speaker_labels.append(speaker_id)
            self.speaker_counter += 1
            return speaker_id
        
        # Calculate similarity with existing speakers
        similarities = []
        for existing_features in self.speaker_embeddings:
            similarity = np.dot(features, existing_features) / (
                np.linalg.norm(features) * np.linalg.norm(existing_features)
            )
            similarities.append(similarity)
        
        max_similarity = max(similarities)
        threshold = 0.7  # Similarity threshold for speaker identification
        
        if max_similarity > threshold:
            # Existing speaker
            best_match_idx = similarities.index(max_similarity)
            speaker_id = self.speaker_labels[best_match_idx]
            self.speakers[speaker_id]['features'].append(features)
            self.speakers[speaker_id]['count'] += 1
            return speaker_id
        else:
            # New speaker
            speaker_id = f"Speaker_{self.speaker_counter + 1}"
            self.speakers[speaker_id] = {
                'features': [features],
                'count': 1,
                'first_seen': time.time()
            }
            self.speaker_embeddings.append(features)
            self.speaker_labels.append(speaker_id)
            self.speaker_counter += 1
            return speaker_id
    
    def process_audio_segment(self, audio_data, sample_rate=16000):
        """Process audio segment and identify speaker"""
        try:
            # Detect voice activity
            vad_frames = self.detect_voice_activity(audio_data, sample_rate)
            
            if not any(vad_frames):
                return None, False  # No speech detected
            
            # Extract speaker features
            features = self.extract_speaker_features(audio_data, sample_rate)
            
            # Identify speaker
            speaker_id = self.identify_speaker(features)
            
            return speaker_id, True
            
        except Exception as e:
            print(f"Error processing audio segment: {e}")
            return "Unknown_Speaker", True
    
    def get_speaker_stats(self):
        """Get statistics about detected speakers"""
        stats = {}
        total_segments = sum(speaker_data['count'] for speaker_data in self.speakers.values())
        
        for speaker_id, speaker_data in self.speakers.items():
            stats[speaker_id] = {
                'segments': speaker_data['count'],
                'percentage': (speaker_data['count'] / total_segments * 100) if total_segments > 0 else 0,
                'first_seen': speaker_data['first_seen']
            }
        
        return stats
    
    def reset(self):
        """Reset speaker detection"""
        self.speakers = {}
        self.speaker_counter = 0
        self.speaker_embeddings = []
        self.speaker_labels = []

class AudioUtils:
    @staticmethod
    def convert_webm_to_wav(webm_data):
        """Convert WebM audio data to WAV format"""
        try:
            # This is a simplified conversion
            # In production, you might want to use ffmpeg or similar
            return webm_data
        except Exception as e:
            print(f"Error converting audio: {e}")
            return webm_data
    
    @staticmethod
    def normalize_audio(audio_data):
        """Normalize audio data"""
        try:
            # Normalize to [-1, 1] range
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                return audio_data / max_val
            return audio_data
        except Exception as e:
            print(f"Error normalizing audio: {e}")
            return audio_data
    
    @staticmethod
    def remove_silence(audio_data, sample_rate=16000, threshold=0.01):
        """Remove silence from audio"""
        try:
            # Simple silence removal based on amplitude threshold
            non_silent_indices = np.where(np.abs(audio_data) > threshold)[0]
            if len(non_silent_indices) > 0:
                start_idx = non_silent_indices[0]
                end_idx = non_silent_indices[-1]
                return audio_data[start_idx:end_idx + 1]
            return audio_data
        except Exception as e:
            print(f"Error removing silence: {e}")
            return audio_data