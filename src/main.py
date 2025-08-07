from drive.auth import authenticate
from drive.fetch_videos import get_video_files
from storage.save_video import save_video_metadata
from storage.db import collection
from download import download_video
from audio.convert import extract_audio
from datetime import datetime
import os
import time

CHECK_INTERVAL_SECONDS = 30
DOWNLOADS_DIR = "downloads"
AUDIOS_DIR = "audios"

def main():
    print("Démarrage du service de surveillance Google Drive...")
    service = authenticate()
    print("Authentification réussie.")

    # Crée les dossiers s’ils n’existent pas
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(AUDIOS_DIR, exist_ok=True)

    while True:
        print("\n--- Nouvelle vérification ---")
        videos = get_video_files(service)
        print(f"{len(videos)} vidéos trouvées.")

        for v in videos:
            print(f"\nVérification vidéo : {v['name']}")
            save_video_metadata(v)

            file_path = os.path.join(DOWNLOADS_DIR, v['name'])
            audio_name = os.path.splitext(v['name'])[0] + ".wav"
            audio_path = os.path.join(AUDIOS_DIR, audio_name)

            doc = collection.find_one({"file_id": v["id"]})

            if os.path.exists(file_path):
                print(f"✅ Vidéo déjà téléchargée : {v['name']}")

                if not doc["status"].get("audio_extracted", False):
                    if os.path.getsize(file_path) > 0:
                        print(f"🔊 Extraction audio pour : {file_path}")
                        extract_audio(file_path, audio_path)

                        # Mise à jour MongoDB
                        collection.update_one(
                            {"file_id": v["id"]},
                            {"$set": {
                                "status.downloaded": True,
                                "status.audio_extracted": True,
                                "audio_path": audio_path,
                                "last_updated": datetime.utcnow()
                            }}
                        )
                continue  # On passe à la vidéo suivante

            try:
                print("⬇️ Téléchargement en cours...")
                download_video(service, v['id'], v['name'])
                time.sleep(2)  # Pause pour éviter les corruptions disque

                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    print(f"🔊 Extraction audio pour : {file_path}")
                    extract_audio(file_path, audio_path)

                    collection.update_one(
                        {"file_id": v["id"]},
                        {"$set": {
                            "status.downloaded": True,
                            "status.audio_extracted": True,
                            "audio_path": audio_path,
                            "last_updated": datetime.utcnow()
                        }}
                    )
                else:
                    print(f"❌ Fichier non trouvé ou vide : {file_path}")

            except Exception as e:
                print(f"❌ Erreur lors du téléchargement ou de la conversion : {e}")


        print(f"🕒 Pause de {CHECK_INTERVAL_SECONDS} secondes...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
