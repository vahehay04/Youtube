"""Complete, standalone upload script used by shorts-agent (YouTube Data API v3).

Uploads ONE approved video to the channel owner's own channel using
videos.insert with the youtube.upload scope, marked as Made for Kids and
as containing synthetic (AI-generated) media.

Requirements:
    pip install google-api-python-client google-auth

Environment variables (stored as encrypted GitHub Actions secrets):
    YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN

Usage:
    python scripts/upload_video.py video.mp4 "Title" "Description" --tags "kids songs,counting"
"""
import argparse
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def youtube_client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(path, title, description, tags, privacy="public", language="en"):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": "10",
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": True,
            "containsSyntheticMedia": True,
            "embeddable": True,
        },
    }
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=8 << 20)
    request = youtube_client().videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    return response["id"]


def main():
    parser = argparse.ArgumentParser(description="Upload one approved video to YouTube")
    parser.add_argument("video")
    parser.add_argument("title")
    parser.add_argument("description")
    parser.add_argument("--tags", default="")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--language", default="en")
    args = parser.parse_args()
    if not os.path.exists(args.video):
        sys.exit(f"File not found: {args.video}")
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    video_id = upload(args.video, args.title, args.description, tags, args.privacy, args.language)
    print(f"Done: https://youtube.com/shorts/{video_id}")


if __name__ == "__main__":
    main()
