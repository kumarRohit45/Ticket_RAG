
from pathlib import Path
import hashlib
import os
import time

import chromadb
import pymupdf
import requests
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_DIR / "data" / "pdfs"
CHROMA_DIR = PROJECT_DIR / "data" / "chroma_db"

# Use a separate collection to protect the original data.
COLLECTION_NAME = "clouddesk_support_jina_test"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

JINA_MODEL = "jina-embeddings-v5-text-nano"
JINA_URL = "https://api.jina.ai/v1/embeddings"

# Number of texts sent in each API request.
BATCH_SIZE = 32

# Load backend/.env without displaying secrets.
load_dotenv(PROJECT_DIR / "backend" / ".env")


# --------------------------------------------------
# Jina API client
# --------------------------------------------------

def get_api_key():
    """Read the Jina API key from the environment."""
    api_key = os.getenv("JINA_API_KEY")

    if not api_key:
        raise RuntimeError(
            "JINA_API_KEY is missing. "
            "Add it to backend/.env before running this script."
        )

    return api_key


def generate_embeddings(texts, task):
    """Generate normalized embeddings using Jina's API."""
    if not texts:
        return []

    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": JINA_MODEL,
        "input": texts,
        "task": task,
        "normalized": True,
    }

    # Retry temporary errors and rate limits.
    for attempt in range(3):
        try:
            response = requests.post(
                JINA_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

            response.raise_for_status()
            result = response.json()

            # Keep vectors in the same order as their input texts.
            items = sorted(
                result["data"],
                key=lambda item: item["index"],
            )
            embeddings = [item["embedding"] for item in items]

            if len(embeddings) != len(texts):
                raise RuntimeError(
                    "Jina returned a different number of embeddings "
                    "than the number of input texts."
                )

            return embeddings

        except requests.RequestException as error:
            if attempt == 2:
                raise RuntimeError(
                    f"Jina embedding request failed: {error}"
                ) from error

            time.sleep(2 ** attempt)

    raise RuntimeError("Could not generate embeddings.")


# --------------------------------------------------
# PDF extraction
# --------------------------------------------------

def load_pdf_pages():
    """Extract PDF text while preserving source and page metadata."""
    documents = []
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in: {PDF_DIR}"
        )

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf_path in pdf_files:
        print(f"Reading: {pdf_path.name}")

        with pymupdf.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()

                if text:
                    documents.append({
                        "text": text,
                        "source": pdf_path.name,
                        "page": page_number,
                    })

    if not documents:
        raise ValueError(
            "No extractable text found in the PDF files."
        )

    return documents


# --------------------------------------------------
# Chunking
# --------------------------------------------------

def split_into_chunks(documents):
    """Split extracted page text into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = []

    for document in documents:
        pieces = splitter.split_text(document["text"])

        for chunk_index, piece in enumerate(pieces):
            piece = piece.strip()

            if not piece:
                continue

            raw_id = (
                f"{document['source']}|"
                f"{document['page']}|"
                f"{chunk_index}|{piece}"
            )

            chunk_id = hashlib.sha256(
                raw_id.encode("utf-8")
            ).hexdigest()

            chunks.append({
                "id": chunk_id,
                "text": piece,
                "metadata": {
                    "source": document["source"],
                    "page": document["page"],
                    "chunk_index": chunk_index,
                },
            })

    return chunks


# --------------------------------------------------
# ChromaDB storage
# --------------------------------------------------

def store_in_chromadb(chunks):
    """Create a separate test collection using Jina embeddings."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    # Only delete the dedicated Jina test collection.
    # The original clouddesk_support collection is untouched.
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = [item["text"] for item in batch]

        embeddings = generate_embeddings(
            texts,
            task="retrieval.passage",
        )

        collection.add(
            ids=[item["id"] for item in batch],
            documents=texts,
            metadatas=[item["metadata"] for item in batch],
            embeddings=embeddings,
        )

        print(
            f"Stored {min(start + BATCH_SIZE, len(chunks))}"
            f" / {len(chunks)} chunks."
        )

    return collection


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    print("\n=== CloudDesk Jina Ingestion Test ===\n")

    if not PDF_DIR.exists():
        raise FileNotFoundError(
            f"PDF directory does not exist: {PDF_DIR}"
        )

    # Validate the key before processing all documents.
    get_api_key()

    pages = load_pdf_pages()
    print(f"\nExtracted text from {len(pages)} pages.")

    chunks = split_into_chunks(pages)
    print(f"Created {len(chunks)} chunks.")

    print(f"\nEmbedding model: {JINA_MODEL}")
    print(f"Target collection: {COLLECTION_NAME}")

    collection = store_in_chromadb(chunks)

    print("\n=== Jina ingestion completed ===")
    print(f"Stored chunks: {collection.count()}")
    print(f"Database: {CHROMA_DIR}")
    print(f"Collection: {COLLECTION_NAME}")
    print("\nOriginal collection was not modified.")


if __name__ == "__main__":
    main()
