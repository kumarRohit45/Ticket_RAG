import os
import logging
from uuid import UUID
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_service import RAGRetriever, RAGAnswerer

from conversation_db import (
    initialize_database,
    create_conversation,
    get_conversation,
    list_conversations,
    get_conversation_messages,
    save_message,
    delete_conversation,
    update_conversation_title,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_DIR / "data" / "pdfs"

app = FastAPI(title="Ticket RAG Demo API")

# ==================== CORS ====================

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

# ==================== REQUEST MODELS ====================

class AskRequest(BaseModel):
    question: str
    conversation_id: UUID | None = None

class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"

# ==================== RAG INITIALIZATION ====================

retriever = RAGRetriever()
answerer = RAGAnswerer(retriever)

# ==================== DATABASE INITIALIZATION ====================

@app.on_event("startup")
def startup_event():
    initialize_database()
    logging.info("Conversation database initialized")

# ==================== GENERAL ENDPOINTS ====================

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

# ==================== DOCUMENT ENDPOINTS ====================

@app.get("/documents")
def list_documents(filename: str | None = None):
    if filename:
        # Only allow a filename, not a directory path.
        if Path(filename).name != filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename."
            )

        if Path(filename).suffix.lower() != ".pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed."
            )

        file_path = PDF_DIR / filename

        if not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="PDF not found."
            )

        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            content_disposition_type="inline",
        )

    if not PDF_DIR.exists():
        return {"documents": []}

    documents = sorted(
        pdf.name
        for pdf in PDF_DIR.glob("*.pdf")
        if pdf.is_file()
    )

    return {"documents": documents}

# ==================== CONVERSATION ENDPOINTS ====================

@app.post("/conversations")
def create_new_conversation(request: CreateConversationRequest):

    try:
        conversation_id = create_conversation(request.title)

        return {
            "conversation_id": conversation_id,
            "title": request.title,
            "message": "Conversation created successfully."
        }

    except Exception:
        logging.exception("Conversation creation failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to create conversation."
        )

@app.get("/conversations")
def get_all_conversations():

    try: 
        return {
            "conversations": list_conversations()
        }

    except Exception:
        logging.exception("Fetching conversations failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve conversations."
        )

@app.get("/conversations/{conversation_id}")
def get_conversation_details(conversation_id: UUID):

    try:
        conversation = get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found."
            )

        messages = get_conversation_messages(conversation_id)

        return {
            "conversation": conversation,
            "messages": messages
        }
    except HTTPException:
        raise

    except Exception:
        logging.exception("Fetching conversation failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve conversation."
        )

@app.delete("/conversation/{conversation_id}")
def remove_conversation(conversation_id: UUID):

    try:
        deleted = delete_conversation(conversation_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found."
            )

        return {
            "message": "Conversation deleted successfully."
        }

    except HTTPException:
        raise

    except Exception:
        logging.exception("Conversation deletion failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to delete conversation."
        )
    
@app.post("/ask")
def ask_question(request: AskRequest):
    try:
        question = request.question.strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty."
            )

        #1. Create a new conversation if no ID was provided.
        if request.conversation_id is None:

            conversation_id = create_conversation()

            # Use the first question as the conversation title.
            title = question[:60]

            update_conversation_title(conversation_id, title)

        else:
            conversation_id = request.conversation_id

        # Verfiy that the conversation exists.
        conversation = get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found."
            )

        # 2. Retrieve previous messages BEFORE saving
        # the current question.
        previous_messages = get_conversation_messages(conversation_id)

        conversation_history = [
            {
                "role": message["role"],
                "content": message["content"]
            }
            for message in previous_messages
        ]

        # 3. Save the current user question.
        save_message(
            conversation_id,
            "user",
            question
        )

        # 4. Generate the answer using previous history.
        result = answerer.answer(question, conversation_history=conversation_history)

        # 5. Save the generated assistant response.
        save_message(
            conversation_id,
            "assistant",
            result["answer"]
        )

        # 6. Return existing RAG response + conversation ID.
        return {
            **result,
            "conversation_id": str(conversation_id)
        }

    except HTTPException:
        raise

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