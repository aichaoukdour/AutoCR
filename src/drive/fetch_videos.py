def get_video_files(service, folder_id=None):
    query = "mimeType contains 'video/'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = service.files().list(
        q=query,
        pageSize=50,
        fields="files(id, name, mimeType, webViewLink)"
    ).execute()
    return results.get('files', [])
