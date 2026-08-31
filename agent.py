from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from agents.agent_loop import run_agent
from utils.file_utils import ensure_dirs

SPREADSHEET_ID = "1gBg7RYDNm9reas-n5FDoYn3Hv1-wBvAZIslUPYIqWCo"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_credentials(token_path="token.json", secret_path="credentials.json"):
    creds = None
    token_file = Path(token_path)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    return creds


def main():
    ensure_dirs()
    creds = get_credentials()
    sheet_service = build("sheets", "v4", credentials=creds).spreadsheets()
    drive_service = build("drive", "v3", credentials=creds)

    run_agent(sheet_service, drive_service, SPREADSHEET_ID)


if __name__ == "__main__":
    main()