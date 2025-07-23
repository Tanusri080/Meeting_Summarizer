from faster_whisper import WhisperModel

model = WhisperModel("base", compute_type="int8")  # use "small" if you want better accuracy

def transcribe_audio(file_path):
    segments, _ = model.transcribe(file_path)
    full_text = " ".join([segment.text for segment in segments])
    return full_text
