import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_service import RAGRetriever, RAGAnswerer

app = FastAPI(title="Ticket RAG Demo API")

frontend_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

vercel_url = os.getenv("FRONTEND_URL")
if vercel_url:
    frontend_origins.append(vercel_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


retriever = RAGRetriever()
answerer = RAGAnswerer(retriever)


@app.get("/")
def home():
    return {"message": "Ticket RAG backend is running!"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "collection": retriever.collection.name,
        "stored_chunks": retriever.collection.count(),
    }


@app.post("/ask")
def ask_question(request: AskRequest):
    try:
        return answerer.answer(request.question)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        # Log full exception details on the server, not in the response.
        import logging
        logging.exception("Question answering failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to answer the question right now.",
        )





# =========Using sentence-transformer=============

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from rag_service import RAGRetriever, RAGAnswerer

# class AskRequest(BaseModel):
#     question:str

# app = FastAPI(title="Ticket RAG Demo API")
# retriever = RAGRetriever()
# answerer = RAGAnswerer(retriever)

# # Allow the Sveltekit frontend to communicate with this backend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#          "http://localhost:5173",
#          "http://127.0.0.1:5173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/")
# def home():
#     return {
#         "message": "Ticket RAG backend is running!"
#     }

# @app.get("/health")
# def health_check():
#     return {
#         "status": "healthy"
#     }

# @app.post("/ask")
# def ask_question(request: AskRequest):
#     return answerer.answer(request.question)