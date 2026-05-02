"""

File: data_pipeline/embed_and_store.py

Responsibility: Takes extracted page-level text from ingestion.py,
chunks it into smaller overlapping pieces for better semantic search,
generates vector embeddings using HuggingFace, and stores everything
persistently in ChromaDB.

Usage:
    python embed_and_store.py
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
import torch # Import PyTorch
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Import our extraction function from the sibling module
try:
    from data_pipeline.ingestion import load_all_pdfs
except ImportError:
    try:
        from ingestion import load_all_pdfs
    except ImportError:
        # If both fail, we might be running as a module from the parent
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        from ingestion import load_all_pdfs

# ── Configuration ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Path for the persistent ChromaDB vector database on disk (no server needed)
VECTOR_DB_DIR = Path(__file__).parent.parent / "vector_db"

# The embedding model from Hugging Face — specified in the SRS document
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ChromaDB collection name — all policy vectors go into one searchable collection
COLLECTION_NAME = "policy_documents"

# LangChain Text Splitter settings
# CHUNK_SIZE: How many chars per chunk. Smaller = more precise, larger = more context.
# CHUNK_OVERLAP: Overlap between adjacent chunks to avoid losing context at boundaries.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


# ── Helper Functions ───────────────────────────────────────────────────────────
def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes page-level text objects and splits them into smaller, overlapping chunks.
    Each resulting chunk retains the original page_number and source (for citations).

    VIVA NOTE: We use RecursiveCharacterTextSplitter from LangChain because it
    tries to split on paragraph breaks, then sentences, then words — preserving
    semantic coherence as much as possible.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # Updated separators to prioritize semantic document structure
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
    )

    chunks: List[Dict[str, Any]] = []
    for page in pages:
        sub_texts = splitter.split_text(page["text"])
        for idx, sub_text in enumerate(sub_texts):
            chunks.append({
                "text": sub_text,
                "page_number": page["page_number"],
                "source": page["source"],
                # Unique ID for ChromaDB: filename + page + chunk index
                "chunk_id": f"{page['source']}_page{page['page_number']}_chunk{idx}",
            })

    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages.")
    return chunks


def embed_and_store(chunks: List[Dict[str, Any]]) -> chromadb.Collection:
    """
    Generates vector embeddings for all text chunks using SentenceTransformer
    and stores them persistently in ChromaDB with associated metadata.

    Returns the ChromaDB collection object for querying.

    VIVA NOTE: SentenceTransformer converts text into a dense 384-dimensional
    vector (a list of 384 floats). ChromaDB stores these vectors so we can
    later find semantically similar chunks with cosine similarity.
    """
    # Ensure the vector_db directory exists
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

    # Initialise the persistent ChromaDB client
    logger.info(f"Initialising ChromaDB at: {VECTOR_DB_DIR}")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    # Get or create the collection (idempotent — safe to re-run)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # Use cosine similarity for semantic search
    )

    # Load the HuggingFace embedding model (downloads once, then cached locally)
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # Prepare data for batch insertion into ChromaDB
    ids: List[str] = []
    embeddings: List[List[float]] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    logger.info("Generating embeddings for all chunks (this may take a moment)...")
    texts = [chunk["text"] for chunk in chunks]
    # Generate all embeddings in one batch for efficiency
    all_embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    for i, chunk in enumerate(chunks):
        ids.append(chunk["chunk_id"])
        embeddings.append(all_embeddings[i].tolist())
        documents.append(chunk["text"])
        metadatas.append({
            "source": chunk["source"],
            "page_number": chunk["page_number"],
        })

    # ChromaDB upsert — adds new, updates existing (safe to re-run without duplicates)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info(f"Successfully stored {len(chunks)} vectors in ChromaDB collection '{COLLECTION_NAME}'.")
    logger.info(f"Total items in collection: {collection.count()}")
    return collection


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Step 1: Extract text from all PDFs in raw_pdfs/
    all_pages = load_all_pdfs()

    if not all_pages:
        logger.warning("No pages extracted. Please add PDFs to data_pipeline/raw_pdfs/ and re-run.")
    else:
        # Step 2: Chunk the pages into smaller, overlapping segments
        all_chunks = chunk_pages(all_pages)

        # Step 3: Generate embeddings and store in ChromaDB
        collection = embed_and_store(all_chunks)

        # Step 4: Quick verification query to confirm everything is working
        logger.info("\n--- VERIFICATION: Running a test query ---")
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        test_query = "scholarship eligibility criteria"
        query_embedding = model.encode([test_query])[0].tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )

        print("\n--- TOP 3 RESULTS FOR TEST QUERY ---")
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            print(f"\n[Result {i+1}]")
            print(f"  Source   : {meta['source']}, Page {meta['page_number']}")
            print(f"  Distance : {dist:.4f}")
            print(f"  Preview  : {doc[:200]}...")
