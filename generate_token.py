import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Tentukan scope/izin (sesuaikan dengan kebutuhan Google Sheets Anda)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def generate():
    # Pastikan file credentials.json ada di folder yang sama
    if not os.path.exists('credentials.json'):
        print("Error: File credentials.json tidak ditemukan! Download dulu dari Google Cloud Console.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Simpan token untuk digunakan nanti
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("Berhasil! File token.json telah dibuat.")

if __name__ == '__main__':
    generate()