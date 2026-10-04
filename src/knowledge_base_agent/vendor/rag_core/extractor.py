"""改编来源：https://github.com/tajwarchy/rag-from-scratch
原始文件：core/extractor.py
commit：4c4e039177ce2a7ac475339cff7a1187a6fd68bf
MIT License，完整版权声明见 licenses/。
修改：保留按页提取主体；保留数字；相对 source；递归 PDF/TXT；跳过空页。
"""
import re
import fitz  # PyMuPDF
from pathlib import Path


def extract_text_from_pdf(pdf_path: str, source_root: str | None = None) -> list[dict]:
    """
    Extract cleaned text from every page of a PDF.

    Returns a list of page dicts:
        [{"source_file": "paper.pdf", "page": 1, "text": "..."}, ...]

    Cleaning steps applied per page:
        1. Collapse runs of whitespace / newlines into single spaces.
        2. Preserve numbers, years, amounts and identifiers.
        3. Strip leading/trailing whitespace.
    Pages that are empty after cleaning are skipped.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path.resolve()}")

    pages = []
    doc = fitz.open(str(path))

    for page_num, page in enumerate(doc, start=1):
        raw = page.get_text("text")
        cleaned = _clean(raw)
        if cleaned:
            pages.append({
                "source_file": path.resolve().relative_to(Path(source_root).resolve()).as_posix() if source_root else path.name,
                "page": page_num,
                "text": cleaned,
            })

    doc.close()
    return pages


def extract_text_from_dir(pdf_dir: str) -> list[dict]:
    """
    Extract text from every PDF in a directory.
    Returns a flat list of page dicts across all files.
    """
    dir_path = Path(pdf_dir)
    if not dir_path.exists():
        raise FileNotFoundError(f"PDF directory not found: {dir_path.resolve()}")

    pdf_files = sorted(dir_path.rglob("*.pdf"))
    if not pdf_files:
        raise ValueError(f"No PDF files found in: {dir_path.resolve()}")

    all_pages = []
    for pdf_file in pdf_files:
        print(f"  Extracting: {pdf_file.name}")
        pages = extract_text_from_pdf(str(pdf_file), str(dir_path))
        all_pages.extend(pages)
        print(f"    → {len(pages)} pages extracted")

    return all_pages


# ── Internal helpers ──────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    # Collapse all whitespace (tabs, newlines, multiple spaces) into single space
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text

def extract_text_from_txt(path: str, source_root: str) -> list[dict]:
    # TXT 不做复杂清洗，保留 UTF-8 原文。
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    return [{"source_file": file.resolve().relative_to(Path(source_root).resolve()).as_posix(),
             "page": None, "text": text}] if text.strip() else []


def extract_documents(source_root: str) -> list[dict]:
    directory = Path(source_root)
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    pages = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() == ".pdf":
            pages.extend(extract_text_from_pdf(str(path), str(directory)))
        elif path.is_file() and path.suffix.lower() == ".txt":
            pages.extend(extract_text_from_txt(str(path), str(directory)))
    return pages
