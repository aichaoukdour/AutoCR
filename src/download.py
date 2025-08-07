from googleapiclient.http import MediaIoBaseDownload
import io

def download_video(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(f"downloads/{file_name}", 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Téléchargement {file_name} : {int(status.progress() * 100)}%")
    print(f"Téléchargement terminé : {file_name}")
