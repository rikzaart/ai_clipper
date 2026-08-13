from agents.agent_loop import run_agent
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.file_utils import ensure_dirs

SPREADSHEET_ID = "1lsPrcG9LX2XZhqsQ1eImYB1MtRNGbcC3uUhb-8SFkJM"

def main():
    ensure_dirs()

    creds = Credentials.from_authorized_user_file("token.json")
    sheet_service = build("sheets", "v4", credentials=creds).spreadsheets()
    drive_service = build("drive", "v3", credentials=creds)

    run_agent(sheet_service, drive_service, SPREADSHEET_ID)


if __name__ == "__main__":
    main()
