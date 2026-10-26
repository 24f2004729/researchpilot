import io
import re
from typing import List, Dict, Any, Optional
import pymupdf


class DocumentParseResult:
    def __init__(self, full_text: str, pages: List[Dict[str, Any]], page_count: int) -> None:
        self.full_text = full_text
        self.pages = pages  # list of {"page_number": int, "text": str, "sections": List[str]}
        self.page_count = page_count


class DocumentParser:
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizes excessive whitespace while preserving paragraph and line structure."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace 3 or more newlines with 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Normalize multiple spaces/tabs within a line
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @classmethod
    def parse_pdf(cls, file_bytes: bytes) -> DocumentParseResult:
        """Extracts text and page-level metadata from a PDF file using PyMuPDF."""
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Corrupt or invalid PDF file: {e}")

        page_count = len(doc)
        if page_count == 0:
            raise ValueError("PDF contains no pages.")

        pages_data: List[Dict[str, Any]] = []
        total_text_chars = 0

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_text = page.get_text("text")
            clean_text = cls.normalize_text(page_text)
            total_text_chars += len(clean_text)

            # Heuristic heading detection: look for short uppercase or Title Case lines
            sections: List[str] = []
            for line in clean_text.split("\n"):
                stripped = line.strip()
                if 3 <= len(stripped) <= 60 and (stripped.isupper() or stripped.istitle()):
                    if not re.match(r"^Page \d+$", stripped, re.IGNORECASE):
                        sections.append(stripped)

            pages_data.append({
                "page_number": page_idx + 1,
                "text": clean_text,
                "sections": sections,
            })

        if total_text_chars == 0:
            raise ValueError("Document contains no extractable text. Scanned PDFs without OCR are not supported in MVP.")

        full_text = "\n\n".join(
            f"--- Page {p['page_number']} ---\n{p['text']}" for p in pages_data if p["text"]
        )

        return DocumentParseResult(
            full_text=full_text,
            pages=pages_data,
            page_count=page_count,
        )

    @classmethod
    def parse_txt(cls, file_bytes: bytes) -> DocumentParseResult:
        """Extracts text from plain text or markdown files."""
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as e:
                raise ValueError(f"Unable to decode text file: {e}")

        clean_text = cls.normalize_text(text)
        if not clean_text:
            raise ValueError("Text file is empty.")

        sections: List[str] = []
        for line in clean_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                sections.append(stripped.lstrip("#").strip())

        pages_data = [{
            "page_number": 1,
            "text": clean_text,
            "sections": sections,
        }]

        return DocumentParseResult(
            full_text=clean_text,
            pages=pages_data,
            page_count=1,
        )

    @classmethod
    def parse(cls, filename: str, file_bytes: bytes) -> DocumentParseResult:
        ext = filename.lower().split(".")[-1]
        if ext == "pdf":
            return cls.parse_pdf(file_bytes)
        elif ext in ["txt", "md", "markdown", "text"]:
            return cls.parse_txt(file_bytes)
        else:
            raise ValueError(f"Unsupported file format '.{ext}'. Supported formats are: PDF, TXT, MD.")
