from __future__ import annotations
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import UploadFile

# Add the project root to sys.path to import data_pipeline and ai_engine
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from data_pipeline.ingestion import extract_text_from_pdf
from data_pipeline.embed_and_store import chunk_pages, embed_and_store
from backend.database import get_db_connection

logger = logging.getLogger(__name__)

# Directory where raw PDFs are stored
RAW_PDF_DIR = project_root / "data_pipeline" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

def process_pdf_upload(
    file_path: Path, 
    display_name: str, 
    access_level: str, 
    user_id: int,
    session_id: Optional[int] = None
):
    """
    Background Task: Handles the entire ingestion pipeline for a new PDF.
    """
    
    try:
        logger.info(f"Extracting text from {file_path.name}...")
        pages = extract_text_from_pdf(file_path)
        if not pages:
            return

        # Chunk and Embed
        chunks = chunk_pages(pages)
        embed_and_store(chunks)
        
        # Register in MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO documents (filename, display_name, access_level, uploaded_by, session_id) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE display_name = %s, access_level = %s, uploaded_by = %s, session_id = %s",
            (file_path.name, display_name, access_level, user_id, session_id, display_name, access_level, user_id, session_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✅ Ingestion complete for '{file_path.name}' (Session: {session_id}).")
        
    except Exception as e:
        logger.error(f"❌ Critical error during ingestion of {file_path.name}: {e}", exc_info=True)
        if file_path.exists():
            file_path.unlink()
