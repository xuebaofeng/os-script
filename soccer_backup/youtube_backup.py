import argparse
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def get_youtube():
    credentials = None

    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE, SCOPES
        )

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES
            )
            credentials = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())

    return build("youtube", "v3", credentials=credentials)


def upload_video(file_path):
    youtube = get_youtube()

    filename = os.path.basename(file_path)

    body = {
        "snippet": {
            "title": filename,
            "description": (
                "Youth soccer game video backup.\n\n"
                f"Original filename: {filename}"
            ),
            "tags": [
                "soccer",
                "youth soccer",
                "game video",
                "backup"
            ],
            "categoryId": "17"
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        file_path,
        chunksize=8 * 1024 * 1024,
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print(f"Uploading: {file_path}")

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            print(
                f"Progress: {int(status.progress() * 100)}%",
                end="\r"
            )

    video_id = response["id"]

    print()
    print("Upload complete!")
    print(f"YouTube ID: {video_id}")
    print(f"https://www.youtube.com/watch?v={video_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload soccer video to YouTube Private"
    )

    parser.add_argument(
        "file",
        help="MP4 video file"
    )

    args = parser.parse_args()

    file_path = os.path.abspath(args.file)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    upload_video(file_path)


if __name__ == "__main__":
    main()