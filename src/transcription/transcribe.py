import speech_recognition as sr

def transcribe_audio(audio_path: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)  # read the entire audio file

    # Use Google's free speech recognition API (or replace with your preferred)
    try:
        text = recognizer.recognize_google(audio, language="fr-FR")  # change language as needed
        return text
    except sr.UnknownValueError:
        return "[Erreur] Impossible de comprendre l'audio."
    except sr.RequestError as e:
        return f"[Erreur] Problème de requête au service de reconnaissance vocale: {e}"
