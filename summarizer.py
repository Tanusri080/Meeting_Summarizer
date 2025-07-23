# summarizer.py
from transformers import pipeline

# Load the summarization pipeline
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def generate_summary(text):
    # Hugging Face has token limits, so clip text if too long
    max_input_length = 1024
    text = text[:max_input_length]

    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']
