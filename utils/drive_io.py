from googleapiclient.http import MediaFileUpload

def upload_to_drive(file_path, folder_id, drive_service):
    file_metadata = {"name": file_path.split('/')[-1], "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    request = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response.get("id")
