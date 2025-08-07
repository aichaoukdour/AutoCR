import whisper
import os

model = whisper.load_model("tiny")

def transcribe_audio(audio_path):
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        print(f"Erreur de transcription : {e}")
        return None

def save_transcription_to_txt(text, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
