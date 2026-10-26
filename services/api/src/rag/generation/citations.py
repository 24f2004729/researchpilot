import re
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str = Field(description="UUID of the chunk cited")
    document_id: Optional[str] = Field(default=None, description="UUID of the parent document")
    document_filename: Optional[str] = Field(default=None, description="Filename of the cited document")
    page: Optional[int] = Field(default=None, description="Page number of the citation")
    quote: Optional[str] = Field(default=None, description="Exact or near-exact supporting quote from text")
    is_valid: bool = Field(default=True, description="Whether citation resolved to context chunk")
    is_supported: bool = Field(default=True, description="Whether quote is verified in chunk text")


class GroundedAnswer(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    insufficient_evidence: bool = False
    model_name: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class CitationValidator:
    INSUFFICIENT_PATTERNS = [
        r"insufficient evidence",
        r"(not have|no) sufficient evidence",
        r"not enough information",
        r"cannot be answered",
        r"do not contain information",
        r"does not contain information",
        r"the provided (documents|context|text) (does|do) not contain",
        r"no information provided",
        r"does not mention",
    ]

    @classmethod
    def is_abstention(cls, text: str) -> bool:
        """Determines if the answer text indicates honest abstention due to lack of evidence."""
        text_lower = text.lower()
        for pat in cls.INSUFFICIENT_PATTERNS:
            if re.search(pat, text_lower):
                return True
        return False

    @staticmethod
    def normalize_quote(quote: str) -> str:
        """Removes punctuation and normalizes spacing for quote matching."""
        return re.sub(r"\W+", " ", quote.lower()).strip()

    @classmethod
    def validate_citation_quote(cls, quote: Optional[str], chunk_content: str) -> bool:
        """Verifies whether the cited quote exists in the source chunk."""
        if not quote or not quote.strip():
            return False

        norm_quote = cls.normalize_quote(quote)
        norm_content = cls.normalize_quote(chunk_content)

        if not norm_quote:
            return False

        # Check direct substring
        if norm_quote in norm_content:
            return True

        # Check if 75% of quote words exist consecutively
        quote_words = norm_quote.split()
        if len(quote_words) >= 4:
            half_len = max(3, int(len(quote_words) * 0.75))
            sub_quote = " ".join(quote_words[:half_len])
            if sub_quote in norm_content:
                return True

        return False

    @classmethod
    def validate_citations(
        cls,
        raw_citations: List[Dict[str, Any]],
        context_chunks: List[Any],
        answer_text: str,
    ) -> List[Citation]:
        chunk_map = {getattr(c, "chunk_id", None) or getattr(c, "id", None): c for c in context_chunks}
        validated: List[Citation] = []
        seen_sources = set()

        for raw in raw_citations:
            source_id = raw.get("source_id") or raw.get("chunk_id")
            if not source_id:
                continue

            chunk = chunk_map.get(str(source_id))
            quote = raw.get("quote", "").strip() if raw.get("quote") else None

            if chunk is None:
                validated.append(
                    Citation(
                        source_id=str(source_id),
                        document_id=raw.get("document_id"),
                        document_filename=raw.get("document_filename", "Unknown"),
                        page=raw.get("page"),
                        quote=quote,
                        is_valid=False,
                        is_supported=False,
                    )
                )
                continue

            doc_id = getattr(chunk, "document_id", None)
            doc_filename = getattr(chunk, "document_filename", None) or "Document"
            page = getattr(chunk, "page_number", None)
            content = getattr(chunk, "content", "")

            is_supported = cls.validate_citation_quote(quote, content) if quote else False

            dedup_key = (str(source_id), quote)
            if dedup_key in seen_sources:
                continue
            seen_sources.add(dedup_key)

            validated.append(
                Citation(
                    source_id=str(source_id),
                    document_id=str(doc_id) if doc_id else None,
                    document_filename=doc_filename,
                    page=page,
                    quote=quote,
                    is_valid=True,
                    is_supported=is_supported,
                )
            )

        return validated
