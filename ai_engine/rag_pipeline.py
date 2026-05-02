from __future__ import annotations

"""

File: ai_engine/rag_pipeline.py

Responsibility: The core "brain" of the project. This module:
  1. Accepts a user's question and runs a Hybrid Search (Vector + BM25 keyword).
  2. Applies Reciprocal Rank Fusion (RRF) to merge and re-rank the two result sets.
  3. Builds a context string from the top-ranked chunks.
  4. Sends the context + question to either:
       - Ollama (Llama 3) for LOCAL mode  — fully offline, data-sovereign
       - Gemini API for CLOUD mode        — for public demonstrations
  5. Returns the AI's answer along with grounded citations.

VIVA NOTE: This is the full RAG (Retrieval-Augmented Generation) pipeline.
"Retrieval" = Hybrid Search + RRF. "Augmented" = adding context to the prompt.
"Generation" = the LLM producing the final answer.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import google.generativeai as genai
from langchain_community.llms import Ollama
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

VECTOR_DB_DIR   = Path(__file__).parent.parent / "vector_db"
COLLECTION_NAME = "policy_documents"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
RE_RANK_MODEL    = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# How many top results to retrieve from each search method before fusion
VECTOR_TOP_K  = 15
KEYWORD_TOP_K = 15
# How many chunks to re-rank before selecting the final set
RE_RANK_TOP_K = 10
# Final number of chunks to include in the LLM's context window
FINAL_TOP_K   = 5

# ── Singleton Clients (initialised once) ──────────────────────────────────────
_chroma_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_embed_model: SentenceTransformer | None = None
_rerank_model: CrossEncoder | None = None

# BM25 Cache to avoid re-tokenising everything on every query
_cached_bm25: BM25Okapi | None = None
_cached_ids: List[str] = []
_cached_texts: List[str] = []
_cached_metas: List[Dict] = []


def _get_collection() -> Tuple[chromadb.Collection, SentenceTransformer]:
    """Lazily initialise ChromaDB and the embedding model (loaded once)."""
    global _chroma_client, _collection, _embed_model
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
        _collection = _chroma_client.get_collection(name=COLLECTION_NAME)
        logger.info(f"Connected to ChromaDB collection '{COLLECTION_NAME}'.")
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model '{EMBEDDING_MODEL}'.")
    return _collection, _embed_model


def _get_rerank_model() -> CrossEncoder:
    """Lazily initialise the Cross-Encoder re-ranking model."""
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = CrossEncoder(RE_RANK_MODEL)
        logger.info(f"Loaded re-ranking model '{RE_RANK_MODEL}'.")
    return _rerank_model


# ── Hybrid Search with Reciprocal Rank Fusion ─────────────────────────────────
def _reciprocal_rank_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    k: int = 60, 
) -> List[Dict]:
    """
    Merges vector and keyword search results using Reciprocal Rank Fusion (RRF).

    RRF Formula: score(d) = sum(1 / (k + rank_i))
    where rank_i is the position of document d in each ranked list.

    VIVA NOTE: RRF is a proven algorithm for combining multiple ranked lists.
    It rewards documents that consistently appear high in BOTH lists.
    The constant 'k=60' is the industry-standard default that balances
    precision vs recall.

    Args:
        vector_results : Ranked list from semantic vector search.
        keyword_results: Ranked list from BM25 keyword search.
        k              : RRF smoothing constant.

    Returns:
        A merged, re-ranked list of the best documents.
    """
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict] = {}

    for ranked_list in [vector_results, keyword_results]:
        for rank, doc in enumerate(ranked_list):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
            chunk_map[doc_id] = doc  # Keep the full document for later

    # Sort by fused score descending
    sorted_ids = sorted(scores, key=lambda d: scores[d], reverse=True)
    # Return more results for the re-ranker stage
    return [chunk_map[doc_id] for doc_id in sorted_ids[:RE_RANK_TOP_K]]


def hybrid_search(
    question: str,
    allowed_sources: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Performs a Hybrid Search combining vector similarity and BM25 keyword search.

    Args:
        question        : The user's natural language question.
        allowed_sources : Optional RBAC filter — only return chunks from these PDF filenames.
                          If None, all documents are searched (admin/analyst access).

    Returns:
        A list of the top FINAL_TOP_K chunks with metadata for citation.
    """
    collection, embed_model = _get_collection()

    # Build optional RBAC where filter for ChromaDB
    where_filter = {"source": {"$in": allowed_sources}} if allowed_sources else None

    # ── 1. Vector Search ────────────────────────────────────────────────────────
    query_embedding = embed_model.encode([question])[0].tolist()
    vector_response = collection.query(
        query_embeddings=[query_embedding],
        n_results=VECTOR_TOP_K,
        where=where_filter,
        include=["documents", "metadatas"],
    )
    vector_results = [
        {"id": id_, "text": doc, "metadata": meta}
        for id_, doc, meta in zip(
            vector_response["ids"][0],
            vector_response["documents"][0],
            vector_response["metadatas"][0],
        )
    ]

    # ── 2. BM25 Keyword Search (Optimised with Caching) ─────────────────────────
    global _cached_bm25, _cached_ids, _cached_texts, _cached_metas
    
    # Retrieve all documents for the corpus (respecting the filter)
    # NOTE: We specify a large n_results/limit to avoid the default 100-item cap
    all_docs_count = collection.count()
    if all_docs_count == 0:
        return []

    all_docs_response = collection.get(
        where=where_filter,
        include=["documents", "metadatas"],
        limit=all_docs_count  # Explicitly fetch ALL allowed chunks
    )
    current_ids = all_docs_response["ids"]

    # Only rebuild BM25 if the document set has changed
    if _cached_bm25 is None or set(current_ids) != set(_cached_ids):
        logger.info("Rebuilding BM25 corpus index...")
        _cached_ids = current_ids
        _cached_texts = all_docs_response["documents"]
        _cached_metas = all_docs_response["metadatas"]
        
        if _cached_texts:
            tokenised_corpus = [text.lower().split() for text in _cached_texts]
            _cached_bm25 = BM25Okapi(tokenised_corpus)
        else:
            _cached_bm25 = None

    keyword_results = []
    if _cached_bm25 and _cached_texts:
        # Strip conversational/intent words that break lexical extraction
        intent_stopwords = {
            "summarize", "summary", "explain", "tell", "me", "about", 
            "what", "is", "the", "are", "how", "do", "does", "can", 
            "you", "provide", "details", "on", "a", "an", "of", "for", "please"
        }
        bm25_query_tokens = [w for w in question.lower().split() if w not in intent_stopwords]
        
        # Fallback if query was ONLY stopwords
        if not bm25_query_tokens:
            bm25_query_tokens = question.lower().split()
            
        bm25_scores = _cached_bm25.get_scores(bm25_query_tokens)
        top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:KEYWORD_TOP_K]
        keyword_results = [
            {"id": _cached_ids[i], "text": _cached_texts[i], "metadata": _cached_metas[i]}
            for i in top_bm25_indices if bm25_scores[i] > 0
        ]

    # ── 3. Fuse Results with RRF ────────────────────────────────────────────────
    fused_results = _reciprocal_rank_fusion(vector_results, keyword_results)
    logger.info(f"Hybrid search returned {len(fused_results)} fused chunks.")
    return fused_results


# ── LLM Integration ───────────────────────────────────────────────────────────
def _build_prompt(question: str, context_chunks: List[Dict]) -> str:
    """
    Constructs a clear, structured prompt combining the question and retrieved context.
    """
    context_text = "\n\n---\n\n".join(
        f"[Source: {chunk['metadata']['source']}, Page {chunk['metadata']['page_number']}]\n{chunk['text']}"
        for chunk in context_chunks
    )
    return (
        "You are an expert Policy Analyst Assistant for the Ministry of Education. "
        "Your goal is to provide accurate, grounded answers based on the provided policy documents.\n\n"
        "INSTRUCTIONS:\n"
        "1. Use Markdown formatting heavily (bolding, headers, bullet points for lists).\n"
        "2. If the user asks for a summary or 'what is in the document', synthesize the key points.\n"
        "3. **CRITICAL**: DO NOT generate any URLs, HTML hyperlinks, or Markdown links `[text](url)` in your response under any circumstances. Reference document names as raw bold text.\n"
        "4. Maintain a professional, analytical tone.\n\n"
        f"CONTEXT:\n{context_text}\n\n"
        f"QUESTION: {question}\n\n"
        "ANSWER:"
    )


def query_llm(
    question: str, 
    context_chunks: List[Dict], 
    inference_mode: str = "local",
    history: List[Dict[str, str]] | None = None,
    gemini_api_key: str | None = None
) -> str:
    """
    Sends the augmented prompt to either Ollama (local) or Gemini API (cloud).
    Includes history for conversational awareness.
    """
    history_text = ""
    if history:
        # Only take the last 4 messages to avoid context overflow
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history[-4:]])
        
    prompt = _build_prompt(question, context_chunks)
    if history_text:
        prompt = f"RELEVANT CONVERSATION HISTORY:\n{history_text}\n\n" + prompt

    if inference_mode == "cloud":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in the server environment.")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    else:
        llm = Ollama(
            model="llama3", 
            base_url="http://localhost:11434", 
            timeout=180,
            temperature=0.1,
            num_predict=512,
            num_ctx=4096
        )
        return llm.invoke(prompt)


def _expand_query(question: str, history: List[Dict[str, str]] | None, inference_mode: str, gemini_api_key: str | None = None) -> str:
    """
    If there's conversation history, uses the LLM to rewrite the current
    question into a standalone query to improve retrieval.
    """
    if not history:
        return question

    last_history = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
    expansion_prompt = (
        "Given the following conversation history and the latest user question, "
        "rephrase the question to be a highly specific standalone query that explicitly resolves any pronouns (e.g., 'it', 'they', 'this rule') "
        "and implicitly references the core topic without requiring the history. "
        "If it is already standalone, return it verbatim without extra filler. Do not answer it.\n\n"
        f"HISTORY:\n{last_history}\n\n"
        f"USER QUESTION: {question}\n\n"
        "STANDALONE QUERY:"
    )

    try:
        if inference_mode == "cloud":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set in the server environment.")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            return model.generate_content(expansion_prompt).text.strip()
        else:
            llm = Ollama(
                model="llama3", 
                base_url="http://localhost:11434", 
                timeout=120,
                temperature=0.1,
                num_predict=100
            )
            return llm.invoke(expansion_prompt).strip()
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}. Using original question.")
        return question


# ── Public Entry Point ────────────────────────────────────────────────────────
def run_rag_query(
    question: str,
    inference_mode: str = "local",
    allowed_sources: List[str] | None = None,
    history: List[Dict[str, str]] | None = None,
    gemini_api_key: str | None = None
) -> Dict[str, Any]:
    """
    The main public function that orchestrates the full RAG pipeline.
    Updated to handle conversation history.
    """
    logger.info(f"RAG query — Mode: {inference_mode}, Question: '{question}'")

    # Step 0: Expand query based on history (Conversational Memory)
    search_query = _expand_query(question, history, inference_mode, gemini_api_key)
    if search_query != question:
        logger.info(f"Expanded query: '{search_query}'")

    # Step 1: Retrieve relevant chunks via Hybrid Search using the expanded query
    # Hybrid Search now returns RE_RANK_TOP_K candidates for the re-ranker
    candidate_chunks = hybrid_search(search_query, allowed_sources=allowed_sources)

    if not candidate_chunks:
        return {
            "answer": "No relevant documents were found. Please ensure PDFs have been ingested.",
            "citations": [],
        }

    # Step 1.5: Re-rank candidates using the Cross-Encoder for maximum analytical precision
    rerank_model = _get_rerank_model()
    # Prepare pairs for re-ranking: (Question, Chunk-Text)
    pairs = [[search_query, chunk["text"]] for chunk in candidate_chunks]
    scores = rerank_model.predict(pairs)
    
    # Attach scores and sort
    for i, chunk in enumerate(candidate_chunks):
        chunk["rerank_score"] = float(scores[i])
    
    context_chunks = sorted(candidate_chunks, key=lambda x: x["rerank_score"], reverse=True)[:FINAL_TOP_K]
    logger.info(f"Re-ranking complete. Top 5 selected from {len(candidate_chunks)} candidates.")

    # Step 2: Generate answer using the selected LLM (pass history for persona/context)
    answer = query_llm(question, context_chunks, inference_mode=inference_mode, history=history, gemini_api_key=gemini_api_key)

    # Step 3: Build grounded citations with "Surgical Quote Extraction"
    seen: set = set()
    citations: List[Dict[str, str]] = []
    
    # We'll use a small LLM call to extract the EXACT sentence/quote from the chunks
    # that supports the generated answer. This provides the "Surgical Highlighting".
    extraction_prompt = (
        f"GIVEN THE ANSWER: {answer}\n\n"
        f"EXTRACT the shortest exact quote (1-2 sentences) from the following context that "
        f"directly supports this answer. Return ONLY the quote verbatim. If multiple, pick the most relevant.\n\n"
        "CONTEXT:\n{context_text}"
    )
    
    surgical_quote = None
    try:
        if inference_mode == "cloud":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set in the server environment.")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            # Pass all context chunks to the extraction prompt
            full_context_for_extraction = "\n\n---\n\n".join([chunk['text'] for chunk in context_chunks])
            surgical_quote = model.generate_content(extraction_prompt.format(context_text=full_context_for_extraction)).text.strip().replace('"', '')
        else:
            llm = Ollama(model="llama3", base_url="http://localhost:11434", num_predict=100)
            # Pass all context chunks to the extraction prompt
            full_context_for_extraction = "\n\n---\n\n".join([chunk['text'] for chunk in context_chunks])
            surgical_quote = llm.invoke(extraction_prompt.format(context_text=full_context_for_extraction)).strip().replace('"', '')
    except Exception as e:
        logger.warning(f"Surgical quote extraction failed: {e}. Falling back to full chunk text for citations.")
        surgical_quote = None

    for chunk in context_chunks:
        meta = chunk["metadata"]
        key  = (meta["source"], meta["page_number"])
        if key not in seen:
            seen.add(key)
            # Use the surgical quote if it exists in this chunk, otherwise fallback to chunk text
            clause = surgical_quote if (surgical_quote and surgical_quote.lower() in chunk["text"].lower()) else chunk["text"]
            citations.append({
                "document_name": meta["source"],
                "page_number"  : meta["page_number"],
                "clause"       : clause,
            })

    return {"answer": answer, "citations": citations}


def compare_documents(doc_a: str, doc_b: str, inference_mode: str = "cloud") -> str:
    """
    Fetches chunks for two specific documents and asks the LLM to identify differences.
    """
    collection, _ = _get_collection()
    
    def get_doc_text(filename: str):
        results = collection.get(
            where={"source": filename},
            include=["documents"]
        )
        return "\n".join(results["documents"])

    text_a = get_doc_text(doc_a)
    text_b = get_doc_text(doc_b)

    prompt = (
        f"You are a Policy Auditor. Compare the following two versions of a policy document and output a clear, "
        f"bulleted list of major ADDITIONS, DELETIONS, and MODIFICATIONS.\n\n"
        f"DOCUMENT A ({doc_a}):\n{text_a[:4000]}\n\n"
        f"DOCUMENT B ({doc_b}):\n{text_b[:4000]}\n\n"
        f"DIFF ANALYSIS:"
    )

    if inference_mode == "cloud":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return "Gemini API key missing for diff analysis."
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model.generate_content(prompt).text
    else:
        llm = Ollama(model="llama3", base_url="http://localhost:11434")
        return llm.invoke(prompt)
