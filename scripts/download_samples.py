"""
Utility script: Downloads 3 sample government/education-related PDFs
into the data_pipeline/raw_pdfs/ directory for testing the ingestion pipeline.

Run with: python download_samples.py
"""

import urllib.request
import os
from pathlib import Path

RAW_PDF_DIR = Path(__file__).parent / "data_pipeline" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Sample Government / Academic Policy PDFs (public domain, freely downloadable)
SAMPLE_PDFS = [
    {
        "url": "https://www.ugc.gov.in/pdfnews/6100466_UGC-Act.pdf",
        "filename": "UGC_Act.pdf"
    },
    {
        "url": "https://www.ugc.gov.in/pdfnews/9741901_UGC_NEP_Circular.pdf",
        "filename": "UGC_NEP_Policy.pdf"
    },
    {
        "url": "https://scholarships.gov.in/public/documents/NSP_guideline.pdf",
        "filename": "NSP_Scholarship_Guidelines.pdf"
    },
]

def download_pdf(url, dest_path):
    print(f"  Downloading: {dest_path.name} ...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            with open(dest_path, "wb") as f:
                f.write(response.read())
        size_kb = dest_path.stat().st_size // 1024
        print(f"  ✅ Saved: {dest_path.name} ({size_kb} KB)")
        return True
    except Exception as e:
        print(f"  ⚠️  Failed to download {dest_path.name}: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Downloading Sample Policy PDFs ===\n")
    success = 0
    for item in SAMPLE_PDFS:
        dest = RAW_PDF_DIR / item["filename"]
        if dest.exists():
            print(f"  ⏭️  Skipping (already exists): {item['filename']}")
            success += 1
            continue
        if download_pdf(item["url"], dest):
            success += 1
    
    existing = list(RAW_PDF_DIR.glob("*.pdf"))
    print(f"\n=== Done! {len(existing)} PDF(s) ready in raw_pdfs/ ===")
    for f in existing:
        print(f"  📄 {f.name} ({f.stat().st_size // 1024} KB)")
    
    if existing:
        print("\n✅ You can now run: python data_pipeline/embed_and_store.py")
    else:
        print("\n⚠️  Please manually place at least one PDF in data_pipeline/raw_pdfs/")
