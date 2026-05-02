from __future__ import annotations

"""

File: backend/main.py

Responsibility: The main FastAPI application server.
Exposes all REST API endpoints and handles:
  - User authentication (login, register — with bcrypt password hashing)
  - JWT token issuance and validation (for protected routes)
  - RBAC filtering: restricts document access based on the user's role
  - Proxying the /api/v1/query endpoint to the AI engine (rag_pipeline.py)

Usage (from project root):
    uvicorn backend.main:app --reload --port 8000

VIVA NOTE: FastAPI automatically generates interactive API docs at
http://localhost:8000/docs — great for demonstrating during viva!
"""

import os
import sys
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import bcrypt
import jwt
import google.api_core.exceptions
import google.auth.exceptions
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

# Add the project root to sys.path so we can import ai_engine
sys.path.append(str(Path(__file__).parent.parent))
from ai_engine.rag_pipeline import run_rag_query
from backend.database import get_db_connection
from backend.services.ingestion_service import process_pdf_upload
from backend.services.cache_service import cache_service
from backend.services.diff_service import perform_document_diff

# ── Document Storage Configuration ──────────────────────────────────────────
# Define the path where PDFs are stored for background ingestion
RAW_PDF_DIR = Path(__file__).parent.parent / "data_pipeline" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── App Initialisation ─────────────────────────────────────────────────────────
app = FastAPI(
    title="AI-Based Policy Retrieval System API",
    description="RAG-powered API for querying government policy documents.",
    version="1.0.0",
)

# Allow the React frontend (localhost:5173 / 127.0.0.1:5173) to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── JWT Config ─────────────────────────────────────────────────────────────────
SECRET_KEY      = os.getenv("JWT_SECRET_KEY", "changeme_in_production")
ALGORITHM       = "HS256"
TOKEN_EXPIRE_HR = 8  # JWT tokens expire after 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Pydantic Models (Request / Response Schema) ─────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class Message(BaseModel):
    role: str     # 'user' | 'bot'
    content: str
    
class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class QueryRequest(BaseModel):
    question: str
    inference_mode: str = "local"  # 'local' (Ollama) or 'cloud' (Gemini)
    history: List[Dict[str, str]] = []
    session_id: Optional[int] = None
    # gemini_api_key field removed — key is server-side only (GEMINI_API_KEY env var)


class Citation(BaseModel):
    document_name: str
    page_number: int
    clause: str


class QueryResponse(BaseModel):
    status: str
    data: dict
    is_from_cache: bool = False

class ChatSession(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

class ChatMessage(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    citations: Optional[List[dict]] = None
    created_at: datetime


# ── Auth Helpers ───────────────────────────────────────────────────────────────
def _create_jwt_token(user_id: int, roles: List[str]) -> str:
    """Issues a signed JWT token encoding the user's ID and roles."""
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HR),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency: Decodes and validates the JWT token from the Authorization header.
    Raises 401 if the token is missing, expired, or tampered with.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": int(payload["sub"]), "roles": payload.get("roles", [])}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")


def _get_allowed_sources(roles: List[str]) -> List[str] | None:
    """
    RBAC Logic: Determines which document filenames the user can query.
    Returns None to allow all documents (admin/analyst), or a filtered list.

    VIVA NOTE: This runs in O(1) before any vector search, ensuring that
    unauthorized users cannot retrieve restricted document embeddings from ChromaDB.
    """
    if "admin" in roles or "analyst" in roles:
        return None  # No filter — full access to all documents
    
    # For general_user, query the DB to get only 'public' documents
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT filename FROM documents WHERE access_level = 'public'")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row["filename"] for row in rows]


# ── Auth Endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/v1/auth/register", tags=["Authentication"])
def register(req: RegisterRequest):
    """Registers a new user with 'general_user' role by default."""
    password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (req.username, req.email, password_hash),
        )
        user_id = cursor.lastrowid
        # Assign the default 'general_user' role
        cursor.execute(
            "INSERT INTO user_roles (user_id, role_id) SELECT %s, id FROM roles WHERE role_name = 'general_user'",
            (user_id,),
        )
        conn.commit()
        return {"status": "success", "message": f"User '{req.username}' registered successfully."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/api/v1/auth/login", tags=["Authentication"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Authenticates a user with username + password, returns a JWT token."""
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s AND is_active = TRUE", (form.username,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(form.password.encode(), user["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        # Fetch user's roles
        cursor.execute(
            "SELECT r.role_name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = %s",
            (user["id"],),
        )
        roles = [row["role_name"] for row in cursor.fetchall()]
        token = _create_jwt_token(user["id"], roles)
        return {"access_token": token, "token_type": "bearer", "roles": roles}
    except Exception as e:
        logger.error(f"Login error: {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail="An internal error occurred during login.")
    finally:
        cursor.close()
        conn.close()


def _get_current_user_optional(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    """Optional version of _get_current_user for token-bridge support."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        roles = payload.get("roles", [])
        if user_id is None:
            return None
        return {"user_id": int(user_id), "roles": roles}
    except:
        return None


# ── Chat Session Management ──────────────────────────────────────────────────
@app.post("/api/v1/chat/sessions", tags=["Chat"])
def create_chat_session(
    req: CreateSessionRequest, 
    current_user: dict = Depends(_get_current_user)
):
    """Creates a new independent chat session for the current user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (%s, %s)",
            (current_user["user_id"], req.title)
        )
        conn.commit()
        session_id = cursor.lastrowid
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session.")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/v1/chat/sessions", tags=["Chat"])
def list_chat_sessions(current_user: dict = Depends(_get_current_user)):
    """Lists all chat sessions for the current user (for the history sidebar)."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, title, updated_at FROM chat_sessions WHERE user_id = %s ORDER BY updated_at DESC",
            (current_user["user_id"],)
        )
        sessions = cursor.fetchall()
        return {"status": "success", "data": sessions}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/v1/chat/sessions/{session_id}", tags=["Chat"])
def get_session_history(session_id: int, current_user: dict = Depends(_get_current_user)):
    """Fetches the full message history for a specific chat session."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Security: verify user owns this session
        cursor.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (session_id,))
        session = cursor.fetchone()
        if not session or session["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Unauthorized session access.")

        cursor.execute(
            "SELECT role, content, citations, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
        messages = cursor.fetchall()
        # Parse citations JSON
        import json
        for msg in messages:
            if msg["citations"]:
                msg["citations"] = json.loads(msg["citations"])
        
        return {"status": "success", "data": messages}
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/v1/chat/sessions/{session_id}", tags=["Chat"])
def delete_chat_session(session_id: int, current_user: dict = Depends(_get_current_user)):
    """Deletes a chat session and all its associated messages."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Security: verify user owns this session
        cursor.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (session_id,))
        row = cursor.fetchone()
        if not row or row[0] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Unauthorized session access.")

        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        conn.commit()
        return {"status": "success", "message": "Session deleted."}
    finally:
        cursor.close()
        conn.close()


def _persist_chat_message(session_id: int, question: str, result: dict):
    """Helper to save user and bot messages to MySQL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        import json
        # Save User Message
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, "user", question)
        )
        # Save Bot Message
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content, citations) VALUES (%s, %s, %s, %s)",
            (session_id, "bot", result["answer"], json.dumps(result["citations"]))
        )
        # Update session timestamp
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (session_id,)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error persisting message: {e}")
    finally:
        cursor.close()
        conn.close()


# ── Core Query Endpoint ────────────────────────────────────────────────────────
@app.post("/api/v1/query", response_model=QueryResponse, tags=["Query"])
def query_policy(
    req: QueryRequest,
    current_user: dict = Depends(_get_current_user),
):
    """
    THE MAIN ENDPOINT — matches the API contract from the Onboarding document.

    1. Validates and decodes the user's JWT to determine their role.
    2. Applies RBAC to restrict which documents can be searched.
    3. Passes the question to the RAG pipeline.
    4. Returns the structured JSON response with answer and citations.
    """
    logger.info(f"Query from user_id={current_user['user_id']}, roles={current_user['roles']}")

    # Step 1: RBAC — determine which sources this user can access
    allowed_sources = _get_allowed_sources(current_user["roles"])
    
    # Session Focus Logic: If a session ID is provided, check if it has specific documents
    if req.session_id:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Security: verify user owns this session
            cursor.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (req.session_id,))
            session = cursor.fetchone()
            if not session or session["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Unauthorized session access.")

            cursor.execute("SELECT filename FROM documents WHERE session_id = %s", (req.session_id,))
            session_docs = [row["filename"] for row in cursor.fetchall()]
            if session_docs:
                # If the session has documents, RESTRICT to these only
                # If RBAC already restricted, intersect the lists. Otherwise, use session_docs.
                if allowed_sources is None: # Admin/Analyst, full access initially
                    allowed_sources = session_docs
                else: # General user, INCLUDE session docs alongside public docs
                    allowed_sources = list(set(allowed_sources) | set(session_docs))
        except HTTPException:
            raise # Re-raise 403
        except Exception as e:
            logger.error(f"Error fetching session docs: {e}")
            # Do not fail the query if session doc fetching fails, proceed with RBAC-only sources
        finally:
            cursor.close()
            conn.close()

    if allowed_sources is not None and len(allowed_sources) == 0:
        raise HTTPException(
            status_code=403,
            detail="No accessible documents found for your role or session. Contact your administrator.",
        )

    # Step 1.5: Check Cache
    cache_key = cache_service.generate_key(req.question, req.inference_mode, allowed_sources)
    cached_result = cache_service.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for key: {cache_key}")
        # Still persist to chat history if session_id provided
        if req.session_id:
            _persist_chat_message(req.session_id, req.question, cached_result)
        return {"status": "success", "data": cached_result, "is_from_cache": True}

    # Pre-flight check: ensure GEMINI_API_KEY is configured for cloud mode
    if req.inference_mode == "cloud" and not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Cloud mode is unavailable: GEMINI_API_KEY is not configured on the server."
        )

    try:
        # Step 2: Run the full RAG pipeline
        # Pass history to allow for follow-up questions
        result = run_rag_query(
            question=req.question,
            inference_mode=req.inference_mode,
            allowed_sources=allowed_sources,
            history=req.history,
            gemini_api_key=None
        )
        
        # Cache the result
        cache_service.set(cache_key, result)

        # Step 3: Persistence (if session_id provided)
        if req.session_id:
            _persist_chat_message(req.session_id, req.question, result)

        return {"status": "success", "data": result}
    except google.api_core.exceptions.Unauthenticated as e:
        logger.error(f"Gemini authentication error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Cloud mode error: Invalid Gemini API key.")
    except google.api_core.exceptions.ResourceExhausted as e:
        logger.error(f"Gemini quota exceeded: {e}", exc_info=True)
        raise HTTPException(status_code=429, detail="Cloud mode error: Gemini API quota exceeded.")
    except (google.auth.exceptions.TransportError, ConnectionError) as e:
        logger.error(f"Gemini network error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Cloud mode error: Network error reaching Gemini API.")
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI engine error: {str(e)}")


@app.get("/api/v1/pdf/{filename}", tags=["Documents"])
def get_pdf_file(
    filename: str,
    token: Optional[str] = None
):
    """
    Serves the actual PDF file. Relies exclusively on Query Param Token for iframe support.
    """
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
        except:
            pass
            
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated (Invalid or missing token)")
    
    file_path = RAW_PDF_DIR / filename
    if not file_path.exists():
        # Try to find it in the data_pipeline/raw_pdfs explicitly just in case
        file_path = Path(__file__).parent.parent / "data_pipeline" / "raw_pdfs" / filename
        
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file '{filename}' not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path, media_type="application/pdf")


# ── Admin: PDF Upload & Document Management ────────────────────────────────────
@app.post("/api/v1/admin/documents", tags=["Admin"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    display_name: str = "New Document",
    access_level: str = "public",
    current_user: dict = Depends(_get_current_user),
):
    """
    Admin-only endpoint: 
    1. Receives a multipart/form-data PDF file.
    2. Offloads the heavy ingestion (OCR/Embedding) to a background task.
    3. Returns immediate 202 Accepted response.
    """
    if "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Admin access required.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Step 1: Save the file immediately to disk (Asynchronous/Threaded)
    # This ensures the event loop is NOT blocked during large file writes
    file_path = RAW_PDF_DIR / file.filename
    logger.info(f"Saving admin upload to {file_path} (Async)")
    
    import anyio
    async def write_file():
        with open(file_path, "wb") as buffer:
            await anyio.to_thread.run_sync(shutil.copyfileobj, file.file, buffer)
    
    await write_file()

    # Step 2: Trigger background ingestion (Threaded)
    background_tasks.add_task(
        process_pdf_upload, 
        file_path, 
        display_name, 
        access_level, 
        current_user["user_id"]
    )

    return {
        "status": "success", 
        "message": f"Upload of '{file.filename}' started. Ingestion will complete in the background."
    }


@app.get("/api/v1/admin/documents", tags=["Admin"])
def list_documents(current_user: dict = Depends(_get_current_user)):
    """Returns a list of all documents currently indexed in the system."""
    if "admin" not in current_user["roles"] and "analyst" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, filename, display_name, access_level, uploaded_at FROM documents ORDER BY uploaded_at DESC")
    docs = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"status": "success", "data": docs}


@app.delete("/api/v1/admin/documents/{doc_id}", tags=["Admin"])
async def delete_document(doc_id: int, current_user: dict = Depends(_get_current_user)):
    """Removes a document metadata from MySQL. Does not delete physical file/vectors."""
    if "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
        return {"status": "success", "message": "Document removed from index."}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/v1/admin/users", tags=["Admin"])
async def list_users(current_user: dict = Depends(_get_current_user)):
    """Lists all registered users for role management dashboard."""
    if "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # We don't return passwords
        cursor.execute("SELECT id, username, email, role, created_at FROM users")
        users = cursor.fetchall()
        return {"status": "success", "data": users}
    finally:
        cursor.close()
        conn.close()


@app.put("/api/v1/admin/users/{user_id}/role", tags=["Admin"])
async def update_user_role(user_id: int, role_req: dict, current_user: dict = Depends(_get_current_user)):
    """Updates a user's role (admin, analyst, public)."""
    if "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    new_role = role_req.get("role")
    if new_role not in ["admin", "analyst", "public"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        return {"status": "success", "message": f"User role updated to {new_role}."}
    except Exception as e:
        logger.error(f"Error updating role: {e}")
        raise HTTPException(status_code=500, detail="Database update failed.")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/v1/admin/diff", tags=["Admin"])
async def compare_policy_versions(
    doc_a_id: int, 
    doc_b_id: int, 
    inference_mode: str = "cloud",
    current_user: dict = Depends(_get_current_user)
):
    """
    Admin-only: Compares two policy documents and returns a summarized list of changes.
    """
    if "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    try:
        result = perform_document_diff(doc_a_id, doc_b_id, inference_mode)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Diff error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Health Check  ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Policy Retrieval System API is running."}

@app.post("/api/v1/chat/upload", tags=["Chat"])
async def chat_upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    display_name: str = Form("User Uploaded Document"),
    session_id: Optional[int] = Form(None),
    current_user: dict = Depends(_get_current_user)
):
    """
    IN-CHAT UPLOAD — links the document to the current session for isolation.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = RAW_PDF_DIR / file.filename
    logger.info(f"Saving chat upload to {file_path} (Session: {session_id})")
    
    import anyio
    async def write_file():
        with open(file_path, "wb") as buffer:
            await anyio.to_thread.run_sync(shutil.copyfileobj, file.file, buffer)
            
    await write_file()

    # Synchronously register the document to prevent RAG fallback bugs
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO documents (filename, display_name, access_level, uploaded_by, session_id) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE display_name = %s, access_level = %s, uploaded_by = %s, session_id = %s",
            (file.filename, display_name, "public", current_user["user_id"], session_id, display_name, "public", current_user["user_id"], session_id)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    background_tasks.add_task(
        process_pdf_upload, 
        file_path, 
        display_name, 
        "public", 
        current_user["user_id"],
        session_id
    )

    return {"status": "success", "message": "File uploaded and indexing started."}
