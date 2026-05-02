import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_engine.rag_pipeline import _reciprocal_rank_fusion, _build_prompt, run_rag_query

# ── Test: Reciprocal Rank Fusion (RRF) ────────────────────────────────────────
def test_rrf_logic():
    """
    Ensures that RRF correctly merges two ranked lists.
    Document 'A' appears in both, 'B' only in vector, 'C' only in keyword.
    """
    vector_results = [
        {"id": "doc_A", "text": "Content A", "metadata": {"source": "p1.pdf"}},
        {"id": "doc_B", "text": "Content B", "metadata": {"source": "p1.pdf"}},
    ]
    keyword_results = [
        {"id": "doc_C", "text": "Content C", "metadata": {"source": "p2.pdf"}},
        {"id": "doc_A", "text": "Content A", "metadata": {"source": "p1.pdf"}},
    ]

    # Run RRF with k=60 (default)
    fused = _reciprocal_rank_fusion(vector_results, keyword_results, k=60)

    # doc_A should be rank 1 because it appears in both lists
    assert fused[0]["id"] == "doc_A"
    assert len(fused) >= 1


# ── Test: Prompt Engineering ──────────────────────────────────────────────────
def test_prompt_building():
    """Ensures the LLM prompt contains the expected structure and context."""
    chunks = [
        {"text": "Policy detail 1", "metadata": {"source": "u.pdf", "page_number": 1}},
        {"text": "Policy detail 2", "metadata": {"source": "g.pdf", "page_number": 10}},
    ]
    question = "How to apply?"
    
    prompt = _build_prompt(question, chunks)
    
    assert "u.pdf" in prompt
    assert "g.pdf" in prompt
    assert "How to apply?" in prompt
    assert "CONTEXT:" in prompt


# ── Test: Full RAG Pipeline Orchestration ─────────────────────────────────────
@patch("ai_engine.rag_pipeline.hybrid_search")
@patch("ai_engine.rag_pipeline.query_llm")
@patch("ai_engine.rag_pipeline._expand_query")
def test_run_rag_query_flow(mock_expand, mock_llm, mock_search):
    """
    Verifies that run_rag_query correctly calls its sub-components.
    """
    # Mock return values
    mock_expand.return_value = "Standalone Question"
    mock_search.return_value = [
        {"id": "1", "text": "Chunk 1", "metadata": {"source": "s.pdf", "page_number": 1}}
    ]
    mock_llm.return_value = "The AI Answer"

    result = run_rag_query("Original Question", inference_mode="local")

    # Assert coordination
    mock_expand.assert_called_once()
    mock_search.assert_called_once_with("Standalone Question", allowed_sources=None)
    mock_llm.assert_called_once()
    
    assert result["answer"] == "The AI Answer"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_name"] == "s.pdf"

def test_run_rag_query_no_results():
    """If no documents found, should return a friendly error message."""
    with patch("ai_engine.rag_pipeline.hybrid_search", return_value=[]):
        result = run_rag_query("Will I find anything?")
        assert "No relevant documents" in result["answer"]
        assert result["citations"] == []
