# from langchain_community.document_loaders import UnstructuredFileIOLoader
from langchain_google_community import GoogleDriveLoader
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_neo4j import Neo4jVector, Neo4jGraph
from langchain_openai import OpenAIEmbeddings
import hashlib

from dotenv import load_dotenv
import os

def sha1(str):
    h = hashlib.new('sha256')
    h.update(str.encode())
    return h.hexdigest()

load_dotenv()

loader = GoogleDriveLoader(
    folder_id=os.getenv("FOLDER_ID"),
    token_path="token.json",
    credentials_path = "credentials.json",
    file_types=["document", "sheet"],
    # Optional: configure whether to recursively fetch files from subfolders. Defaults to False.
    recursive=True,
#    file_loader_cls=UnstructuredFileIOLoader,
#    file_loader_kwargs={"mode": "elements"},
)

documents = loader.load()
print(len(documents))

for d in documents:
    print(d.metadata, len(d.page_content))

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(documents)

for d in chunks:
    d.metadata['id'] = sha1(d.page_content)
    print(d.metadata, len(d.page_content))

print(len(chunks))

graph = Neo4jGraph(url=os.getenv("NEO4J_URL"), 
    username=os.getenv("NEO4J_USERNAME"), 
    password=os.getenv("NEO4J_PASSWORD"))

graph.query("""
  UNWIND $rows as row
  MERGE (d:Document {source:row.source}) 
  ON CREATE SET d.date = datetime(row.when), d.title = row.title
""", {"rows" : [d.metadata for d in documents]})

db = Neo4jVector.from_documents(
    chunks, OpenAIEmbeddings(), 
    graph = graph,
    ids=[d.metadata['id'] for d in chunks],
    search_type='hybrid'
)
# graph.query("""
#             UNWIND rows as row
#             MATCH (c:Chunk {id:row.id}) WHERE NOT exists { (c)<-[:PART_OF]-() }  
#             MERGE (d:Document {source:row.source}) 
#             MERGE (c)-[:PART_OF]->(d)
#             """, {"rows": [{"id":d.id, "source":d.source} for d in chunks]})

graph.query("""
            MATCH (c:Chunk) WHERE NOT exists { (c)-[:PART_OF]->() }  
            MERGE (d:Document {source:c.source}) 
            ON CREATE SET d.date = datetime(c.when), d.title = c.title
            MERGE (c)-[:PART_OF]->(d)
            REMOVE c.when, c.title, c.source
            """)

query = "What are GraphRAG patterns"
docs_with_score = db.similarity_search_with_score(query, k=5)

print(docs_with_score)
