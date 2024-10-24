# Google Drive File Ingestion to Neo4j Database

This script pulls files from the Neo4j google drive directories and uploads documents to the specified Neo4j database providing they are google docs or slides. The google drive API cannot export non-native file formats. The contents of excel and word documents will therefore not be loaded to the Neo4j database.

If a file is referenced as a shortcut in a directory, there is provision for this in the script. The file ID will be gotten through the shortcut and if in the correct format, it will be loaded to the Neo4j database.

If a directory is selected, for which all contents should be copied to the Neo4j database, there is a function to iteravely go through subfolders in order to get all files in the chosen location.

For this script to work, a token.json file must be used to provide verify the connection throught the google drive API. This token expires and must be renewed regularly to ensure the script continues to work. More information on this can be found at: https://developers.google.com/drive/api/guides/about-sdk



