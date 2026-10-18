"""Run ONCE on your own computer to get the YouTube refresh token.

    pip install google-auth-oauthlib
    python scripts/get_youtube_token.py client_secret.json

A browser window opens: sign in with the Google account that owns the channel,
choose the channel, allow access. The script prints three values — paste them
into GitHub → Settings → Secrets and variables → Actions. Don't send them to anyone.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Использование: python scripts/get_youtube_token.py client_secret.json")
    path = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    with open(path, encoding="utf-8") as f:
        info = json.load(f).get("installed") or {}
    print("\nДобавьте в GitHub Secrets:\n")
    print(f"YOUTUBE_CLIENT_ID     = {info.get('client_id', creds.client_id)}")
    print(f"YOUTUBE_CLIENT_SECRET = {info.get('client_secret', creds.client_secret)}")
    print(f"YOUTUBE_REFRESH_TOKEN = {creds.refresh_token}")


if __name__ == "__main__":
    main()
