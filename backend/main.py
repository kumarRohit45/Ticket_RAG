from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import RAGRetriever, RAGAnswerer

class AskRequest(BaseModel):
    question:str

app = FastAPI(title="Ticket RAG Demo API")
retriever = RAGRetriever()
answerer = RAGAnswerer(retriever)

# Allow the Sveltekit frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
         "http://localhost:5173",
         "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "Ticket RAG backend is running!"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }

@app.post("/ask")
def ask_question(request: AskRequest):
    return answerer.answer(request.question)