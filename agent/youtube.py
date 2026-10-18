"""Uploads a Short to YouTube via the Data API v3 (OAuth refresh token)."""
from __future__ import annotations

from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .common import env, log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _client():
    creds = Credentials(
        token=None,
        refresh_token=env("YOUTUBE_REFRESH_TOKEN"),
        client_id=env("YOUTUBE_CLIENT_ID"),
        client_secret=env("YOUTUBE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(cfg: dict, item: dict, video: Path) -> str:
    ch = cfg["channel"]
    title = item["title"]
    if "#shorts" not in title.lower() and len(title) <= 90:
        title = f"{title} #Shorts"
    body = {
        "snippet": {
            "title": title[:100],
            "description": item["yt_description"][:4900],
            "tags": item.get("tags", []),
            "categoryId": str(ch.get("category_id", "10")),
            "defaultLanguage": ch["language"],
            "defaultAudioLanguage": ch["language"],
        },
        "status": {
            "privacyStatus": ch.get("privacy", "public"),
            "selfDeclaredMadeForKids": True,      # детский контент — обязательно
            "containsSyntheticMedia": True,       # честная пометка ИИ-контента
            "embeddable": True,
        },
    }
    yt = _client()

    def do_upload(b: dict) -> str:
        media = MediaFileUpload(str(video), mimetype="video/mp4", resumable=True, chunksize=8 << 20)
        req = yt.videos().insert(part="snippet,status", body=b, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return resp["id"]

    log("⬆️  Загружаю на YouTube…")
    try:
        video_id = do_upload(body)
    except HttpError as e:
        if "containsSyntheticMedia" in str(e):
            body["status"].pop("containsSyntheticMedia")
            video_id = do_upload(body)
        else:
            raise
    log(f"   готово: https://youtube.com/shorts/{video_id}")
    return video_id
