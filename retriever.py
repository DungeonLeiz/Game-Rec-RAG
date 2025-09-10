import os
import time
import pandas as pd
import shutil
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

DB_LOCATION = "./chroma_langchain_db"
CSV_PATH = "data/games.csv"
TIMESTAMP_FILE = os.path.join(DB_LOCATION, "csv_timestamp.txt")

def load_retriever():
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")

    csv_mtime = os.path.getmtime(CSV_PATH)
    needs_rebuild = True

    if os.path.exists(DB_LOCATION) and os.path.exists(TIMESTAMP_FILE):
        with open(TIMESTAMP_FILE, "r") as f:
            saved_mtime = float(f.read().strip())
        if abs(saved_mtime - csv_mtime) < 1:
            needs_rebuild = False

    if needs_rebuild:
        if os.path.exists(DB_LOCATION):
            shutil.rmtree(DB_LOCATION)

        vector_store = Chroma(
            collection_name="games",
            persist_directory=DB_LOCATION,
            embedding_function=embeddings,
        )

        df = pd.read_csv(CSV_PATH)
        documents, ids = [], []
        for i, row in df.iterrows():
            doc = Document(
                page_content=row["Name"],
                metadata={
                    "publisher": row.get("Publisher", ""),
                    "genre": row.get("Genre", ""),
                    "platform": row.get("Platform", ""),
                    "score": row.get("User_Score", ""),
                    "metascore": row.get("Metascore", ""),
                    "release_year": row.get("Release_Year", ""),
                },
                id=str(i)
            )
            documents.append(doc)
            ids.append(str(i))

        BATCH_SIZE = 5000
        for i in range(0, len(documents), BATCH_SIZE):
            batch_docs = documents[i:i+BATCH_SIZE]
            batch_ids = ids[i:i+BATCH_SIZE]
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)

        os.makedirs(DB_LOCATION, exist_ok=True)
        with open(TIMESTAMP_FILE, "w") as f:
            f.write(str(csv_mtime))

    else:
        vector_store = Chroma(
            collection_name="games",
            persist_directory=DB_LOCATION,
            embedding_function=embeddings,
        )

    return vector_store.as_retriever(search_kwargs={"k": 5})
