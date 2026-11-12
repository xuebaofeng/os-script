import argparse
import os
import re
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"
TARGET_FOLDER = r"C:\shared\lehan - U15 MLS Next Tier 2"
TARGET_PLAYLIST_TITLE = "BUSC 2011/2012 MLS Next Academy games"
TITLE_PHRASE = "Ballistic United Soccer Club"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


def get_youtube():
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def get_uploaded_videos(youtube):
    channel_response = (
        youtube.channels()
        .list(part="contentDetails", mine=True)
        .execute()
    )
    channels = channel_response.get("items", [])
    if not channels:
        raise RuntimeError("No YouTube channel found for the authorized account.")

    uploads_playlist = (
        channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    video_ids = []
    page_token = None
    while True:
        response = (
            youtube.playlistItems()
            .list(
                part="contentDetails",
                playlistId=uploads_playlist,
                maxResults=50,
                pageToken=page_token
            )
            .execute()
        )
        video_ids.extend(
            item.get("contentDetails", {}).get("videoId")
            for item in response.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        )
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    videos_by_id = {}
    for start in range(0, len(video_ids), 50):
        batch_ids = video_ids[start:start + 50]
        response = (
            youtube.videos()
            .list(
                part="snippet,status",
                id=",".join(batch_ids),
                maxResults=50
            )
            .execute()
        )
        videos_by_id.update(
            (video["id"], video)
            for video in response.get("items", [])
        )

    return [
        videos_by_id[video_id]
        for video_id in video_ids
        if video_id in videos_by_id
    ]


def source_path_from_description(description):
    for line in (description or "").splitlines():
        stripped_line = line.strip()
        label = "Full local path:"
        if stripped_line.casefold().startswith(label.casefold()):
            return stripped_line[len(label):].strip()
    return None


def is_in_target_folder(source_path):
    if not source_path:
        return False

    folder = os.path.normcase(
        os.path.normpath(os.path.abspath(TARGET_FOLDER))
    )
    video_path = os.path.normcase(
        os.path.normpath(os.path.abspath(source_path))
    )

    try:
        return os.path.commonpath([folder, video_path]) == folder
    except ValueError:
        return False


def ensure_title_phrase(title):
    title = (title or "").strip()
    remainder = re.sub(re.escape(TITLE_PHRASE), "", title, flags=re.IGNORECASE)
    remainder = re.sub(r"\s*\|\s*", " | ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip(" |-").strip()
    normalized = TITLE_PHRASE if not remainder else f"{TITLE_PHRASE} | {remainder}"
    return normalized[:100].rstrip()


def find_playlist(youtube, title):
    page_token = None
    while True:
        response = (
            youtube.playlists()
            .list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=page_token
            )
            .execute()
        )
        for item in response.get("items", []):
            if item.get("snippet", {}).get("title") == title:
                return item["id"]

        page_token = response.get("nextPageToken")
        if not page_token:
            return None


def get_playlist_video_ids(youtube, playlist_id):
    video_ids = set()
    page_token = None

    while True:
        response = (
            youtube.playlistItems()
            .list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token
            )
            .execute()
        )
        video_ids.update(
            item.get("contentDetails", {}).get("videoId")
            for item in response.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        )

        page_token = response.get("nextPageToken")
        if not page_token:
            return video_ids


def add_video_to_playlist(youtube, playlist_id, video_id):
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    ).execute()


def update_video(youtube, video, title):
    current_snippet = video["snippet"]
    snippet = {
        key: current_snippet[key]
        for key in (
            "description",
            "tags",
            "categoryId",
            "defaultLanguage",
            "defaultAudioLanguage",
            "localized"
        )
        if key in current_snippet
    }
    snippet["title"] = title

    localized = snippet.get("localized")
    if localized and localized.get("title"):
        localized = dict(localized)
        localized["title"] = ensure_title_phrase(localized["title"])
        snippet["localized"] = localized

    youtube.videos().update(
        part="snippet,status",
        body={
            "id": video["id"],
            "snippet": snippet,
            "status": {
                "privacyStatus": "public"
            }
        }
    ).execute()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Find matching videos among all uploads on the authorized "
            "YouTube channel."
        )
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all videos in the channel's uploads playlist."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show intended changes without changing YouTube."
    )
    args = parser.parse_args()

    youtube = get_youtube()
    videos = get_uploaded_videos(youtube)
    matching_videos = [
        video for video in videos
        if is_in_target_folder(
            source_path_from_description(
                video.get("snippet", {}).get("description", "")
            )
        )
    ]

    print(f"Scanned {len(videos)} uploaded videos.")
    print(f"Found {len(matching_videos)} videos from the target folder.")

    if not matching_videos:
        print(
            "No matching videos found. Videos without a recognizable "
            "source path in their YouTube description cannot be matched "
            "to the local folder."
        )
        return

    playlist_id = find_playlist(youtube, TARGET_PLAYLIST_TITLE)
    if not playlist_id:
        raise RuntimeError(
            f"YouTube playlist not found: {TARGET_PLAYLIST_TITLE}"
        )

    playlist_video_ids = get_playlist_video_ids(youtube, playlist_id)

    for video in matching_videos:
        video_id = video["id"]
        current_title = video.get("snippet", {}).get("title", "")
        updated_title = ensure_title_phrase(current_title)

        print()
        print(f"Video ID: {video_id}")
        print(f"Title: {current_title}")

        if video_id in playlist_video_ids:
            print("Playlist: already contains video.")
        elif args.dry_run:
            print("Playlist: would add video.")
        else:
            add_video_to_playlist(youtube, playlist_id, video_id)
            playlist_video_ids.add(video_id)
            print("Playlist: added video.")

        if updated_title == current_title:
            print("Title: already normalized.")
        elif args.dry_run:
            print(f"Title: would change to {updated_title}")

        current_visibility = video.get("status", {}).get(
            "privacyStatus",
            "unknown"
        )
        needs_visibility_update = current_visibility != "public"
        if needs_visibility_update and args.dry_run:
            print("Visibility: would change to public.")
        elif not needs_visibility_update:
            print("Visibility: already public.")

        if not args.dry_run and (
                updated_title != current_title
                or needs_visibility_update
        ):
            update_video(youtube, video, updated_title)
        if not args.dry_run and updated_title != current_title:
            print(f"Title: updated to {updated_title}")
        if not args.dry_run and needs_visibility_update:
            print("Visibility: updated to public.")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
