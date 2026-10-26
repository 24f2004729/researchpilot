from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...models.document import Document
from ...models.chunk import DocumentChunk
from ...database import cosine_similarity


class CandidateChunk:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        document_filename: str,
        chunk_index: int,
        content: str,
        page_number: Optional[int],
        section_title: Optional[str],
        score: float,
        retrieval_method: str = "dense",
    ) -> None:
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.document_filename = document_filename
        self.chunk_index = chunk_index
        self.content = content
        self.page_number = page_number
        self.section_title = section_title
        self.score = score
        self.retrieval_method = retrieval_method

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_filename": self.document_filename,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "score": self.score,
            "retrieval_method": self.retrieval_method,
        }


def dense_search(
    db: Session,
    workspace_id: str,
    query_vector: List[float],
    document_ids: Optional[List[str]] = None,
    top_k: int = 15,
) -> List[CandidateChunk]:
    """
    Performs dense vector retrieval with strict workspace-level isolation.
    Uses native pgvector cosine distance on PostgreSQL, and cosine_similarity on SQLite.
    """
    is_postgres = db.bind.dialect.name == "postgresql"

    # Base query joining document to verify workspace and ready status
    query = (
        db.query(DocumentChunk, Document.filename)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.workspace_id == workspace_id)
        .filter(Document.status == "ready")
    )

    if document_ids:
        query = query.filter(DocumentChunk.document_id.in_(document_ids))

    if is_postgres:
        # PostgreSQL pgvector native cosine distance <=>
        # 1 - (embedding <=> query_vector) is cosine similarity
        results = (
            query.order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
            .all()
        )
        candidates = []
        for chunk, filename in results:
            # Distance: 0 = identical, 2 = opposite. Sim = 1 - distance
            dist = 0.0
            sim = 1.0 - dist
            candidates.append(
                CandidateChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_filename=filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    score=sim,
                    retrieval_method="dense",
                )
            )
        return candidates

    # SQLite / Portable Fallback
    chunks_with_filename = query.all()
    scored_candidates = []
    for chunk, filename in chunks_with_filename:
        if chunk.embedding is not None:
            sim = cosine_similarity(query_vector, chunk.embedding)
            scored_candidates.append((sim, chunk, filename))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = scored_candidates[:top_k]

    return [
        CandidateChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_filename=filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            score=sim,
            retrieval_method="dense",
        )
        for sim, chunk, filename in top_candidates
    ]
