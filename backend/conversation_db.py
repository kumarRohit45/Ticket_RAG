import os
import uuid
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# Load environments variables from backend/.env
load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from backend/.env")

def get_connection():
    """Create a PostgreSQL database connection."""
    return psycopg.connect(DATABASE_URL)

def initialize_database():
    """Create conversation and message tables if they don't exist."""

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New Conversation',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NULL NULL DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages(
                    id UUID PRIMARY KEY,
                    conversation_id UUID NOT NULL
                       REFERENCES conversations(id)
                       ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL
                       CHECK (role IN ('user', 'assisstant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            conn.commit()

def create_conversation(title="New Conversation"):
    """Create a new conversation and return its ID."""

    conversation_id = uuid.uuid4()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (id, title)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (conversation_id, title)
            )

            result = cursor.fetchone()
    return str(result[0])

def save_message(conversation_id, role, content):
    """Save a user or assistant message."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content)
                VALUES (%s, %s, %s, %s);
                """,
                (uuid.uuid4(), conversation_id, role, content)
            )

            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (conversation_id,)
            )

def get_conversation_messages(conversation_id):
    """Retrieve all messages belonging to a conversation."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content, created_at FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC, id ASC;
                """,
                (conversation_id,)
            )

            rows = cursor.fetchall()

    return [
        {
            "role": row[0],
            "content": row[1],
            "created_at": row[2].isoformat()
        }
        for row in rows
    ]

def list_conversations():
    """Retrieve all conversations, newest activity first."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, created_at, updated_at FROM conversations
                ORDER BY updated_at DESC;
                """
            )

            rows = cursor.fetchall()

    return [
        {
            "id": str(row[0]),
            "title": row[1],
            "created_at": row[2].isoformat(),
            "updated_at": row[3].isoformat()
        }
        for row in rows
    ]

def delete_conversation(conversation_id):
    """Delete a conversation and its messages."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM conversations WHERE id = %s RETURNING id;",
                (conversation_id,)
            )

            deleted = cursor.fetchone()

    return deleted is not None

def get_conversation(conversation_id):
    """Retrieve a conversation by its ID."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, created_at, updated_at FROM conversations 
                WHERE id = %s;
                """,
                (conversation_id,)
            )

            row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": str(row[0]),
        "title": row[1],
        "created_at": row[2].isoformat(),
        "updated_at": row[3].isoformat()
    }

def update_conversation_title(conversation_id, title):
    """Update a conversation's title."""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversations
                SET title = %s, updated_at = NOW()
                WHERE id = %s;
                """,
                (title, conversation_id)
            )