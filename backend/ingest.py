from pathlib import Path
import hashlib

import chromadb
import pymupdf
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_DIR / "data" / "pdfs"
CHROMA_DIR = PROJECT_DIR / "data" / "chroma_db"

COLLECTION_NAME = "clouddesk_support"

# Chunking confugration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def load_pdf_pages():
    """Extract text from each PDF page and preserve page metadata."""
    documents = []

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in: {PDF_DIR}"
        )
    print(f"Found {len(pdf_files)} PDF files.")

    for pdf_path in pdf_files:
        print(f"Reading: {pdf_path.name}")

        try:
            with pymupdf.open(pdf_path) as pdf:
                for page_number, page in enumerate(pdf, start=1):
                    text = page.get_text("text").strip()

                    if not text:
                        continue

                    documents.append({
                        "text":text,
                        "source": pdf_path.name,
                        "page": page_number,
                    })
        except Exception as error:
            raise RuntimeError(
                f"Could not read {pdf_path.name}: {error}"
            ) from error

    if not documents:
        raise ValueError("No extractable text found in any PDF files.")

    return documents

def split_into_chunks(documents):
    """Split page text into smaller overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len
    )

    chunks = []

    for document in documents:
        pieces = splitter.split_text(document["text"])

        for chunk_index, piece in enumerate(pieces):
            piece = piece.strip()

            if not piece:
                continue

            # Stable ID based on source, page, position and text.
            raw_id = (
                f"{document['source']}|"
                f"{document['page']}|"
                f"{chunk_index}|{piece}"
            )
            chunk_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()

            chunks.append({
                "id": chunk_id,
                "text": piece,
                "metadata": {
                    "source": document["source"],
                    "page": document["page"],
                    "chunk_index": chunk_index,
                }
            })
    return chunks

def store_in_chromadb(chunks, model):
    """Generate embeddings and persist chunks in ChromaDB."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Rebuild this demo collection each time ingestion run.
    # This prevents duplicate records after repeated runs.
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    batch_size = 100

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]

        texts = [item["text"] for item in batch]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        collection.add(
            ids=[item["id"] for item in batch],
            documents=texts,
            metadatas=[item["metadata"] for item in batch],
            embeddings=embeddings,
        )

        print(
            f"Stored {min(start + batch_size, len(chunks))}"
            f" / {len(chunks)} chunks."
        )
    return collection

def main():
    print("\n=== CloudDesk PDF Ingestion ===\n")

    if not PDF_DIR.exists():
        raise FileNotFoundError(
            f"PDF directory does not exist: {PDF_DIR}"
        )

    #1. Extract PDF text
    pages =  load_pdf_pages()
    print(f"\nExtracted text from {len(pages)} pages.")

    #2. Split text into chunks
    chunks = split_into_chunks(pages)
    print(f"Created {len(chunks)} chunks.")

    #3. Load the embedding model
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    print("The first run may take some time to download the model.")

    model = SentenceTransformer(EMBEDDING_MODEL)

    #4. Generate embeddings and save to ChromaDB
    collection = store_in_chromadb(chunks, model)

    print("\n=== Ingestion completed successfully ===")
    print(f"PDF directory: {PDF_DIR}")
    print(f"ChromaDB directory: {CHROMA_DIR}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total stored chunks: {collection.count()}")

if __name__ == "__main__":
    main()