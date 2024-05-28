import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from neo4j import GraphDatabase

# If modifying these scopes, delete the file token.json.

NEO4J_URI="bolt://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="password"
# Update the list of scopes to include the one for exporting files
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
API_KEY = 'AIzaSyDeHlpiRM03MorwPk_fLmS-E3FkYG0HoVs'


def main():
  """Shows basic usage of the Drive v3 API.
  Prints the names and ids of the first 10 files the user has access to.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  # driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
  kbFiles = None

  try:
    driveService = build("drive", "v3", credentials=creds, developerKey=API_KEY)

    # Call the Drive v3 API
    # This retrieves an object with all the files in the parent folder and their metadata
    kbFiles = (
        driveService.files()
        .list(pageSize=1000, supportsAllDrives=True, includeItemsFromAllDrives=True, includeTeamDriveItems=True, supportsTeamDrives=True, q="'1VyJnjVQxTA6PtvZUtzXI0liWz1Vb4SVk' in parents", fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime, shortcutDetails)")
        .execute()
    )
    
    print (kbFiles)
    
  except HttpError as error:
    print(f"An error occurred: {error}") 

  # initialise count and fileList
  count = 0
  fileList = []
  
  # Loop through the files and print their names and IDs
  for file in kbFiles.get('files'):
    count = count + 1
    # fileContent = driveService.files().export(fileId=file['id'], mimeType='text/plain').execute().decode('utf-8')
    # Check if the file is a shortcut
    if file['mimeType'] == 'application/vnd.google-apps.shortcut':
    # Fetch the target file ID from the shortcut
      target_file_id = file.get('shortcutDetails', {}).get('targetId')
      print("Target file ID: " + str(target_file_id))
    
      if target_file_id:
        # Make a request to fetch the content of the target file
        try:
          target_file_request = driveService.files().export(fileId='1N8ts499ObXwoyZCvU-FA9K_zYRFx7yX7', mimeType='text/plain').execute().decode('utf-8')
          print("Target file content: " + str(target_file_request))
        except HttpError as error:
          if error.resp.status == 404:
            print(f"File with ID {target_file_id} was not able to be retrieved")
          else:
            print(f"An error occurred while retrieving file with ID {target_file_id}: {error}")
    else:
    # If it's not a shortcut, fetch the content as usual
      try:
        if file['mimeType'] == 'application/vnd.google-apps.document' or file['mimeType'] == 'application/vnd.google-apps.presentation':
          fileContent = driveService.files().export(fileId=file['id'], mimeType='text/plain', prettyPrint=True).execute().decode('utf-8')
        else: 
          fileContent = "Not a document or presentation"
      except HttpError as error:
          print(f"An error occurred while retrieving content for file with ID {file['id']}: {error}")
          fileContent = None  # Set content to None if an error occurs
    
    nextFile = {"id":file['id'],"name":file['name'],"content":fileContent,"modifiedTime":file['modifiedTime']}
    fileList.append(nextFile)
  # # session = driver.session()
  for file in fileList:
    print(file)
  # result = session.run("UNWIND $fileList as file MERGE (f:BrainFile:KB{id: file.id}) SET f.name = file.name MERGE (c:Content{content: file.content}) MERGE (f)-[:HAS_CONTENT]->(c) RETURN f.id, f.name, c.content",fileList=fileList)
  # session.close()
  
  # driver.close()
  
if __name__ == "__main__":
  main()

