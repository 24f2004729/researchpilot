import re
from typing import List, Dict, Any, Optional
from ..config import settings


class Chunk:
    def __init__(
        self,
        chunk_index: int,
        content: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        token_count: int = 0,
    ) -> None:
        self.chunk_index = chunk_index
        self.content = content
        self.page_number = page_number
        self.section_title = section_title
        self.token_count = token_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_index": self.chunk_index,
            "content": self.content,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "token_count": self.token_count,
        }


class Chunker:
    def __init__(
        self,
        target_chunk_size: int = settings.CHUNK_SIZE,
        overlap: int = settings.CHUNK_OVERLAP,
    ) -> None:
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Approximates token count based on whitespace & punctuation boundaries."""
        words = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
        return len(words)

    def chunk_page_text(
        self,
        text: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        start_index: int = 0,
    ) -> List[Chunk]:
        """
        Chunks text within a page using a sliding window approach with configurable overlap.
        Preserves section titles and handles arbitrary paragraph or sentence lengths.
        """
        if not text.strip():
            return []

        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: List[Chunk] = []
        current_words: List[str] = []
        current_section = section_title
        current_chunk_idx = start_index

        for para in paragraphs:
            # Check if this paragraph looks like a new section heading
            if 3 <= len(para) <= 60 and (para.isupper() or para.istitle()) and "\n" not in para:
                current_section = para

            words = para.split()
            if not words:
                continue

            idx = 0
            while idx < len(words):
                remaining_slots = self.target_chunk_size - len(current_words)
                if remaining_slots <= 0:
                    chunk_str = " ".join(current_words)
                    chunks.append(
                        Chunk(
                            chunk_index=current_chunk_idx,
                            content=chunk_str,
                            page_number=page_number,
                            section_title=current_section,
                            token_count=self.estimate_tokens(chunk_str),
                        )
                    )
                    current_chunk_idx += 1
                    if self.overlap > 0 and len(current_words) > self.overlap:
                        current_words = current_words[-self.overlap:]
                    else:
                        current_words = []
                    remaining_slots = self.target_chunk_size - len(current_words)

                take = words[idx : idx + remaining_slots]
                current_words.extend(take)
                idx += len(take)

                if len(current_words) >= self.target_chunk_size and idx < len(words):
                    chunk_str = " ".join(current_words)
                    chunks.append(
                        Chunk(
                            chunk_index=current_chunk_idx,
                            content=chunk_str,
                            page_number=page_number,
                            section_title=current_section,
                            token_count=self.estimate_tokens(chunk_str),
                        )
                    )
                    current_chunk_idx += 1
                    if self.overlap > 0 and len(current_words) > self.overlap:
                        current_words = current_words[-self.overlap:]
                    else:
                        current_words = []

        if current_words:
            chunk_str = " ".join(current_words)
            chunks.append(
                Chunk(
                    chunk_index=current_chunk_idx,
                    content=chunk_str,
                    page_number=page_number,
                    section_title=current_section,
                    token_count=self.estimate_tokens(chunk_str),
                )
            )

        return chunks

    def chunk_document(self, pages: List[Dict[str, Any]]) -> List[Chunk]:
        """Chunks an entire parsed document across all pages."""
        all_chunks: List[Chunk] = []
        current_index = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            sections = page.get("sections", [])
            initial_section = sections[0] if sections else None
            page_text = page.get("text", "")

            page_chunks = self.chunk_page_text(
                text=page_text,
                page_number=page_num,
                section_title=initial_section,
                start_index=current_index,
            )
            all_chunks.extend(page_chunks)
            current_index += len(page_chunks)

        return all_chunks
