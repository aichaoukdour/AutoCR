from moviepy.editor import VideoFileClip


def extract_audio(video_path, audio_path):
    print(f"Conversion en audio : {video_path}")
    try:
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            print("❌ Pas de piste audio détectée.")
        else:
            print(f"🎵 Audio trouvé (durée : {clip.audio.duration}s), extraction en cours...")
            clip.audio.write_audiofile(audio_path)
            print(f"✅ Audio extrait dans : {audio_path}")
        clip.close()
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction audio : {e}")
