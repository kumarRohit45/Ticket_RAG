import os
from pathlib import Path

import chromadb
import requests
from dotenv import load_dotenv
from groq import Groq

PROJECT_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = PROJECT_DIR / "data" / "chroma_db"
COLLECTION_NAME = "clouddesk_support_jina_test"

JINA_MODEL = "jina-embeddings-v5-text-nano"
JINA_URL = "https://api.jina.ai/v1/embeddings"
GROQ_MODEL = "openai/gpt-oss-20b"
TOP_K = 5

load_dotenv(Path(__file__).resolve().parent / ".env")


class RAGRetriever:
    def __init__(self):
        self.api_key = os.getenv("JINA_API_KEY")

        if not self.api_key:
            raise RuntimeError("JINA_API_KEY is missing.")

        print("Connecting to ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )
        self.collection = self.chroma_client.get_collection(
            name=COLLECTION_NAME
        )
        print("Connected. Stored chunks:", self.collection.count())

    def embed_question(self, question):
        response = requests.post(
            JINA_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": JINA_MODEL,
                "input": [question],
                "task": "retrieval.query",
                "normalized": True,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    def retrieve(self, question, top_k=TOP_K):
        question = question.strip()

        if not question:
            raise ValueError("Question cannot be empty.")

        count = self.collection.count()

        if count == 0:
            return []

        embedding = self.embed_question(question)

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        retrieved_chunks = []

        for document, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            retrieved_chunks.append({
                "text": document,
                "source": metadata["source"],
                "page": metadata["page"],
                "chunk_index": metadata["chunk_index"],
                "distance": float(distance),
            })

        return retrieved_chunks


class RAGAnswerer:
    def __init__(self, retriever):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing.")

        self.retriever = retriever
        self.client = Groq(api_key=api_key)

   
    def answer(self, question):
        question = question.strip()

        if not question:
            raise ValueError("Question cannot be empty.")

        chunks = self.retriever.retrieve(question)

        if not chunks:
            return {
                "answer": "I couldn't find relevant information in the support documents.",
                "sources": [],
                "chunks": [],
                "source_contributions": [],
            }

        # Build the context used by the LLM.
        context = "\n\n".join(
            f"[Source: {chunk['source']}, Page: {chunk['page']}]\n"
            f"{chunk['text']}"
            for chunk in chunks
        )

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a CloudDesk support assistant. "
                        "Answer using only the supplied documents. "
                        "Do not invent facts or policies. "
                        "If the documents do not contain enough evidence, "
                        "clearly say so. Be concise and helpful."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Documents:\n{context}"
                    ),
                },
            ],
            temperature=0.1,
        )

        answer_text = response.choices[0].message.content or ""

        # Keep the existing source list, grouped by filename and page.
        sources = []
        seen = set()

        for chunk in chunks:
            key = (chunk["source"], chunk["page"])

            if key not in seen:
                seen.add(key)
                sources.append({
                    "filename": chunk["source"],
                    "page": chunk["page"],
                })

        # Return the top 5 chunks with their retrieval distances.
        top_chunks = chunks[:5]

        returned_chunks = [
            {
                "rank": rank,
                "filename": chunk["source"],
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "distance": chunk["distance"],
            }
            for rank, chunk in enumerate(top_chunks, start=1)
        ]

        # Calculate a rank-weighted evidence share for each PDF.
        # Rank 1 receives weight 1, rank 2 receives 1/2, etc.
        # This is a retrieval-evidence estimate, NOT exact answer attribution.
        source_weights = {}

        for rank, chunk in enumerate(top_chunks, start=1):
            filename = chunk["source"]
            weight = 1.0 / rank

            source_weights[filename] = (
                source_weights.get(filename, 0.0) + weight
            )

        total_weight = sum(source_weights.values())

        source_contributions = [
            {
                "filename": filename,
                "percentage": round(weight / total_weight * 100, 2),
            }
            for filename, weight in source_weights.items()
        ]

        source_contributions.sort(
            key=lambda item: item["percentage"],
            reverse=True,
        )

        return {
            "answer": answer_text,
            "sources": sources,
            "chunks": returned_chunks,
            "source_contributions": source_contributions,
        }















# ===========================Using sentence transformer===============

# import os
# from dotenv import load_dotenv
# from groq import Groq
# from pathlib import Path
# import chromadb
# from sentence_transformers import SentenceTransformer

# # Project configuration
# PROJECT_DIR = Path(__file__).resolve().parent.parent
# CHROMA_DIR = PROJECT_DIR / "data" / "chroma_db"

# COLLECTION_NAME = "clouddesk_support"
# EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# TOP_K = 5

# BACKEND_DIR = Path(__file__).resolve().parent
# load_dotenv(BACKEND_DIR / ".env")

# GROQ_MODEL = "openai/gpt-oss-20b"

# class RAGRetriever:
#     def __init__(self):
#         print("Loading embedding model...")

#         # Load the same model used during ingestion.
#         self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)

#         print("Connecting to ChromaDB...")
#         self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

#         self.collection = self.chroma_client.get_collection(
#             name=COLLECTION_NAME
#         )

#         print("Connected. Stored chunks:", self.collection.count());
    
#     def retrieve(self, question: str, top_k: int = TOP_K):
#         question = question.strip()

#         if not question:
#             raise ValueError("Question cannot be empty.")

#         # Convert the question into a numericl vector.
#         question_embedding = self.embedding_model.encode(
#             question,
#             normalize_embeddings=True
#         ).tolist()

#         # Search the vector database.
#         results = self.collection.query(
#             query_embeddings = [question_embedding],
#             n_results=min(top_k, self.collection.count()),
#             include=["documents", "metadatas", "distances"]
#         )

#         retrieved_chunks = []

#         documents = results["documents"][0]
#         metadatas = results["metadatas"][0]
#         distances = results["distances"][0]

#         for document, metadata, distance in zip(documents, metadatas, distances):
#             retrieved_chunks.append({
#                 "text":document,
#                 "source":metadata["source"],
#                 "page":metadata["page"],
#                 "chunk_index":metadata["chunk_index"],
#                 "distance":float(distance),
#             })

#         return retrieved_chunks

# class RAGAnswerer:
#     def __init__(self, retriever):
#         api_key = os.getenv("GROQ_API_KEY")

#         if not api_key:
#             raise RuntimeError("GROQ_API_KEY is missing. Check backend/.env.")

#         self.retriever = retriever
#         self.client = Groq(api_key=api_key)

#     def answer(self, question):
#         chunks = self.retriever.retrieve(question)
#         chunks = [
#             chunk for chunk in chunks
#             if chunk["distance"] <= 0.55
#         ]

#         if not chunks:
#             return {
#                 "answer": "I couldn't find relevant information.",
#                 "sources": [],
#             }

#         context = "\n\n".join(
#             f"[Source: {chunk['source']}, "
#             f"Page: {chunk['page']}]\n{chunk['text']}"
#             for chunk in chunks
#         )

#         response = self.client.chat.completions.create(
#             model=GROQ_MODEL,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are a CloudDesk support assisstant. "
#                         "Answer using only the supplied documents. "
#                         "Do not invent facts or policies. "
#                         "If the documents do not contain enough "
#                         "evidence, clearly say so."
#                     ),
#                 },
#                 {
#                     "role": "user",
#                     "content": (
#                         f"Question: {question}\n\n"
#                         f"Documents:\n{context}"
#                     ),
#                 },
#             ],
#             temperature=0.1,
#         )

#         answer_text = (
#             response.choices[0].message.content or ""
#         )

#         sources = []
#         seen = set()

#         for chunk in chunks:
#             key = (chunk["source"], chunk["page"])

#             if key not in seen:
#                 seen.add(key)
#                 sources.append({
#                     "filename": chunk["source"],
#                     "page": chunk["page"],
#                 })
#         return {
#             "answer": answer_text,
#             "sources": sources,
#         }
        
# if __name__ == "__main__":
#     retriever = RAGRetriever()
#     answerer = RAGAnswerer(retriever)

#     while True:
#         question = input("\nAsk a question (or type 'exit' to quit): ").strip()

#         if question.lower() == "exit":
#             break

        
#         try:
#             chunks = retriever.retrieve(question)
#             print("\n=== Retrieved Text ===")
#             for chunk in chunks:
#                 print(f"\nSource: {chunk['source']}")
#                 print(f"Distance: {chunk['distance']:.4f}")
#                 print(chunk["text"])
#                 print("-" * 50)

#             print("\n=== Retrieval Scores ===")
#             for chunk in chunks:
#                 print(
#                     f"Distance: {chunk['distance']:.4f} | "
#                     f"Source: {chunk['source']} | "
#                     f"Page: {chunk['page']}"
#                 )

#             result = answerer.answer(question)

#             print("\n=== Answer ===")
#             print(result["answer"])

#             print("\n=== Sources ===")
#             for source in result["sources"]:
#                 print(
#                     f"- {source['filename']} "
#                     f"(page {source['page']})"
#                 )

#         except Exception as error:
#             print(f"Request failed: {error}")

#         # try:
#         #     chunks = retriever.retrieve(question)

#         #     print("\n=== Retrieved Results ===")

#         #     for rank, chunk in enumerate(chunks, start=1):
#         #         print(f"\n--- Result {rank} ---")
#         #         print(f"Source: {chunk['source']}")
#         #         print(f"Page: {chunk['page']}")
#         #         print(f"Chunk: {chunk['chunk_index']}")
#         #         print(f"Cosine distance: {chunk['distance']:.4f}")
#         #         print(f"Text: {chunk['text']}")

#         # except ValueError as error:
#         #     print(f"Input error: {error}")

    