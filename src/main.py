from drive.auth import authenticate
from drive.fetch_videos import get_video_files

def main():
    service = authenticate()
    videos = get_video_files(service)
    if not videos:
        print("Aucune vidéo trouvée.")
    else:
        print("Vidéos trouvées :")
        for v in videos:
            print(f"{v['name']} - {v['webViewLink']}")

if __name__ == "__main__":
    main()
