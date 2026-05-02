import logging
from pathlib import Path
from typing import Dict, Any
from ai_engine.rag_pipeline import compare_documents
from backend.database import get_db_connection

logger = logging.getLogger(__name__)

def perform_document_diff(doc_a_id: int, doc_b_id: int, inference_mode: str = "cloud") -> Dict[str, Any]:
    """
    Fetches text for two documents and generates a diff analysis.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch metadata for both documents
        cursor.execute("SELECT filename, display_name FROM documents WHERE id = %s", (doc_a_id,))
        doc_a = cursor.fetchone()
        cursor.execute("SELECT filename, display_name FROM documents WHERE id = %s", (doc_b_id,))
        doc_b = cursor.fetchone()

        if not doc_a or not doc_b:
            raise ValueError("One or both documents not found in database.")

        # 2. Extract full text (or key summaries) from ChromaDB for both
        # For simplicity in this mini-project, we'll let the AI Engine handle the text retrieval
        # or we could fetch all chunks for these files from ChromaDB.
        
        # 3. Call AI Engine for comparison
        diff_result = compare_documents(
            doc_a["filename"], 
            doc_b["filename"], 
            inference_mode=inference_mode
        )

        return {
            "doc_a": doc_a["display_name"],
            "doc_b": doc_b["display_name"],
            "analysis": diff_result
        }
    finally:
        cursor.close()
        conn.close()
