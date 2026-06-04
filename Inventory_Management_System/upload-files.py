from googleapiclient.discovery import build
from google.oauth2 import service_account

scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'key.json'
PARENT_FOLDER_ID = ''

def authenticate():
    credentials = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
    return credentials
def upload_file(file_path, file_name):
    credentials = authenticate()
    drive_service = build('drive', 'v3', credentials=credentials)
    file_metadata = {
        'name': file_name,
        'parents': [PARENT_FOLDER_ID]
    }
    media = drive_service.files().create(body=file_metadata, media_body=file_path).execute()
    # return media

upload_file('inventory.csv', 'inventory.csv')
