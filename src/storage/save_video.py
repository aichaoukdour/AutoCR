from storage.db import collection
from datetime import datetime
from pymongo.errors import PyMongoError

def save_video_metadata(video):
    try:
        print(f"Début sauvegarde vidéo : {video['name']}")
        existing = collection.find_one({"file_id": video["id"]})
        if existing:
            print(f"Vidéo déjà enregistrée : {video['name']}")
            return
        
        doc = {
            "_id": video["id"],
            "file_id": video["id"],
            "name": video["name"],
            "webViewLink": video["webViewLink"],
            "mimeType": video.get("mimeType", ""),
            "createdTime": video.get("createdTime", ""),
            "status": {
                "downloaded": False,
                "transcribed": False,
                "summarized": False,
                "sent": False
            },
            "transcription": None,
            "summary": None,
            "participants": [],
            "notes": "",
            "last_updated": datetime.utcnow()
        }
        collection.insert_one(doc)
        print(f"Vidéo enregistrée avec succès : {video['name']}")
    except PyMongoError as e:
        print(f"Erreur lors de la sauvegarde MongoDB pour {video['name']}: {e}")
