import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from neo4j import GraphDatabase

# If modifying these scopes, delete the file token.json.
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "password"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
API_KEY = 'AIzaSyDeHlpiRM03MorwPk_fLmS-E3FkYG0HoVs'

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    kbFiles = None
    exportFileList = []

    try:
        driveService = build("drive", "v3", credentials=creds, developerKey=API_KEY)
        kbFiles = (
            driveService.files()
            .list(
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                includeTeamDriveItems=True,
                supportsTeamDrives=True,
                q="'1ouXS9TcWWEsorxooU_-wbrtvIcdIaWzI' in parents",
                fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime, shortcutDetails)"
            )
            .execute()
        )

    except HttpError as error:
        print(f"An error occurred: {error}")
    

    for file in kbFiles.get('files', []):
        if file['mimeType'] == 'application/vnd.google-apps.shortcut':
            target_file_id = file.get('shortcutDetails', {}).get('targetId')
            try: 
                if target_file_id:
                    target_file = driveService.files().get(fileId=target_file_id, fields='id, name, mimeType').execute()
                    if target_file['mimeType'] in ['application/vnd.google-apps.document', 'application/vnd.google-apps.presentation']:
                        try:
                            if target_file_id not in exportFileList:
                                exportFileList.append({'id': target_file_id, 'name': target_file['name']})
                        except HttpError as error:
                            print(f"An error occurred while retrieving metadata for file with ID {target_file_id}: {error}")
                    else:
                        print(f"Shortcut file with ID {file['id']} has a target file with ID {target_file_id} that is not a Google Document or Presentation")
                else :
                    print(f"Shortcut file with ID {file['id']} does not have a target file ID")
            except HttpError as error:
                print(f"An error occurred while retrieving metadata for file with ID {target_file_id}: {error}")
        elif file['mimeType'] in ['application/vnd.google-apps.document', 'application/vnd.google-apps.presentation']:
            if file['id'] not in exportFileList:
                exportFileList.append({'id': file['id'], 'name': file['name']})

    dbArrayList = []
    for file_info in exportFileList:
        try:
            fileContent = driveService.files().export(fileId=file_info['id'], mimeType='text/plain').execute().decode('utf-8')
            dbArrayList.append({
                'id': file_info['id'],
                'name': file_info['name'],
                'content': fileContent
            })
        except HttpError as error:
            print(f"An error occurred while retrieving content for file with ID {file_info['id']}: {error}")

    with driver.session() as session:
        result = session.run(
            "UNWIND $fileList as file "
            "MERGE (f:KB {id: file.id}) "
            "SET f.name = file.name "
            "MERGE (c:Content {content: file.content}) "
            "MERGE (f)-[:HAS_CONTENT]->(c) "
            "RETURN f.id, f.name, c.content",
            fileList=dbArrayList
        )

    driver.close()

if __name__ == "__main__":
    main()


