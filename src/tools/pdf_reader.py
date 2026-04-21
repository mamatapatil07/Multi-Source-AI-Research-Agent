"""
PDF Reader Tool for ResearchFlow.
Extracts text from PDFs and performs simple keyword-based retrieval.
"""

import logging
import io

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

_MAX_PAGES = 50
_CHUNK_SIZE = 500  # characters per chunk


def extract_text_from_pdf(pdf_bytes: bytes, filename: str = "document.pdf") -> str:
    """
    Extract all text from a PDF file (bytes).
    Returns the concatenated text, limited to the first 50 pages.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = reader.pages[:_MAX_PAGES]
        text_parts: list[str] = []

        for i, page in enumerate(pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[Page {i + 1}] {page_text.strip()}")

        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            logger.warning("PDF '%s' contains no extractable text (possibly scanned)", filename)
            return ""

        logger.info("Extracted %d chars from '%s' (%d pages)", len(full_text), filename, len(pages))
        return full_text

    except Exception as exc:
        logger.error("Failed to extract text from PDF '%s': %s", filename, exc)
        return ""


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current))
            # 20% overlap
            overlap_start = max(0, len(current) - len(current) // 5)
            current = current[overlap_start:]
            current_len = sum(len(w) + 1 for w in current)

    if current:
        chunks.append(" ".join(current))

    return chunks


def search_pdf_text(
    pdf_text: str,
    question: str,
    filename: str = "document.pdf",
    max_chunks: int = 3,
) -> dict:
    """
    Simple keyword-based search over extracted PDF text.

    Returns a dict with keys: relevant_text, source_file, page_info.
    """
    empty = {"relevant_text": "", "source_file": filename, "page_info": ""}

    if not pdf_text.strip():
        return empty

    try:
        chunks = _chunk_text(pdf_text)
        if not chunks:
            return empty

        # Score chunks by keyword overlap with the question
        question_words = set(question.lower().split())
        scored: list[tuple[float, str]] = []

        for chunk in chunks:
            chunk_words = set(chunk.lower().split())
            overlap = len(question_words & chunk_words)
            score = overlap / max(len(question_words), 1)
            scored.append((score, chunk))

        # Sort by score descending, take top chunks
        scored.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for score, chunk in scored[:max_chunks] if score > 0]

        if not top_chunks:
            # Fallback: return the first few chunks
            top_chunks = [chunks[0]] if chunks else []

        relevant_text = "\n\n".join(top_chunks)

        # Truncate to ~500 tokens
        if len(relevant_text) > 1500:
            relevant_text = relevant_text[:1500] + "…"

        # Try to extract page numbers from the text
        page_info = ""
        import re
        page_numbers = re.findall(r"\[Page (\d+)\]", relevant_text)
        if page_numbers:
            page_info = f"Pages: {', '.join(set(page_numbers))}"

        result = {
            "relevant_text": relevant_text,
            "source_file": filename,
            "page_info": page_info,
        }

        logger.info(
            "search_pdf_text(%s, '%s') → %d chars from %d chunks",
            filename, question[:50], len(relevant_text), len(top_chunks),
        )
        return result

    except Exception as exc:
        logger.error("search_pdf_text failed: %s", exc)
        return empty
