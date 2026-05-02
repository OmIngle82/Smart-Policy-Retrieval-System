"""

File: data_pipeline/ingestion.py

Responsibility: Reads raw PDF files from the 'raw_pdfs/' directory,
extracts clean text page-by-page, and returns structured page objects
with metadata (filename, page_number) for the embedding step.

Usage:
    python ingestion.py
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor

# ── Configuration ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# The directory where raw government policy PDFs are placed by the admin
RAW_PDF_DIR = Path(__file__).parent / "raw_pdfs"


# ── Core Extraction Logic ──────────────────────────────────────────────────────
_ocr_reader = None

def get_ocr_reader():
    """Lazily initialize the EasyOCR reader (loads models once)."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            # Initialize reader for English (can add more languages as needed)
            # Use gpu=False for better compatibility on student laptops without NVIDIA GPUs
            _ocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR Engine initialized (CPU Mode).")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
    return _ocr_reader

def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts text from every page of a single PDF file (Hybrid OCR).
    1. Try Ultra-Fast Digital extraction (fitz / PyMuPDF)
    2. Fallback to EasyOCR if page is empty (Scanned)
    """
    pages_content = []
    
    try:
        doc = fitz.open(str(pdf_path))
        num_pages = len(doc)
        logger.info(f"Processing '{pdf_path.name}' ({num_pages} pages)...")

        for page_num in range(num_pages):
            page = doc.load_page(page_num)
            raw_text = page.get_text("text")
            
            # Path B: OCR Fallback (if no text found)
            if not raw_text or len(raw_text.strip()) < 5:
                reader = get_ocr_reader()
                if reader:
                    logger.info(f"  [OCR] Scanned page detected (Page {page_num + 1}). Running computer vision...")
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72)) # Render at 300 DPI
                    img_bytes = pix.tobytes("png")
                    result = reader.readtext(img_bytes, detail=0)
                    raw_text = " ".join(result)
                else:
                    raw_text = ""
                    
            if raw_text and len(raw_text.strip()) > 5:
                # Optimized cleaning: Collapse multiple spaces/tabs while preserving vertical \n
                # This ensures the RecursiveCharacterTextSplitter can detect semantic boundaries.
                import re
                clean_text = re.sub(r'[ \t]+', ' ', raw_text).strip()
                pages_content.append({"page_number": page_num + 1, "text": clean_text, "source": pdf_path.name})
                
        return pages_content

    except Exception as e:
        logger.error(f"Failed to process '{pdf_path.name}': {e}")
        return []


def load_all_pdfs(directory: Path = RAW_PDF_DIR) -> List[Dict[str, Any]]:
    """
    Scans the 'raw_pdfs' directory and extracts text from all PDF files.

    Returns:
        A flat list of all page-level dictionaries from all PDFs.
    """
    if not directory.exists():
        raise FileNotFoundError(
            f"raw_pdfs directory not found at: {directory}\n"
            "Please create it and add your policy PDFs."
        )

    pdf_files = list(directory.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in '{directory}'. Add PDFs to begin.")
        return []

    all_pages: List[Dict[str, Any]] = []
    for pdf_path in pdf_files:
        pages = extract_text_from_pdf(pdf_path)
        all_pages.extend(pages)
        logger.info(f"  Extracted {len(pages)} pages from '{pdf_path.name}'.")

    logger.info(f"\nTotal pages extracted: {len(all_pages)} from {len(pdf_files)} PDF(s).")
    return all_pages


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pages = load_all_pdfs()
    if pages:
        # Print a preview of the first page to verify extraction is working
        print("\n--- EXTRACTION PREVIEW (Page 1 of first PDF) ---")
        print(f"Source    : {pages[0]['source']}")
        print(f"Page Num  : {pages[0]['page_number']}")
        print(f"Text Preview: {pages[0]['text'][:300]}...")
