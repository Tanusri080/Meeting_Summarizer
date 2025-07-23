# app.py
import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
import os
from audio_to_text import transcribe_audio
from summarizer import generate_summary

# Ensure recordings folder exists
os.makedirs("recordings", exist_ok=True)

# UI
st.title("🎤 Real-Time Meeting Summarizer - Step 2: Transcription")

# Set parameters
fs = 44100  # Sample rate
seconds = st.slider("Recording Duration (seconds)", min_value=3, max_value=20, value=5)  # Duration of recording

# UI
st.title("🎤 Real-Time Meeting Summarizer - Step 2: Transcription")

# Add this:
st.header("Step 1: Record Audio")

# Record button
if st.button("Start Recording"):
    st.write("Recording...")
    audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    file_path = "recordings/temp_audio.wav"
    
    # Fix: convert to int16 for Whisper compatibility
    write(file_path, fs, (audio * 32767).astype('int16'))
    st.success("Recording completed and saved!")

    # Play back audio (👂 optional)
    st.audio(file_path)

    # Transcribe
    with st.spinner("Transcribing..."):
        transcript = transcribe_audio(file_path)
        st.subheader("📄 Transcription Result")

        if not transcript.strip():
            st.warning("No speech detected in the recording. Please try again.")
        else:
            st.write(transcript)
            st.subheader("📝 Summary")
            summary = generate_summary(transcript)
            st.write(summary)

            # Download button (⬇️)
            st.download_button("Download Transcript", transcript, file_name="transcript.txt")

