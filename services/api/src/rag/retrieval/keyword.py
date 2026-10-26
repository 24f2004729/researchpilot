import re
import math
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...models.document import Document
from ...models.chunk import DocumentChunk
from .dense import CandidateChunk


def keyword_search(
    db: Session,
    workspace_id: str,
    query_text: str,
    document_ids: Optional[List[str]] = None,
    top_k: int = 15,
) -> List[CandidateChunk]:
    """
    Performs keyword full-text search with strict workspace authorization.
    Uses PostgreSQL FTS (to_tsvector) on Postgres, and BM25 token matching on SQLite.
    """
    if not query_text.strip():
        return []

    is_postgres = db.bind.dialect.name == "postgresql"

    query = (
        db.query(DocumentChunk, Document.filename)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.workspace_id == workspace_id)
        .filter(Document.status == "ready")
    )

    if document_ids:
        query = query.filter(DocumentChunk.document_id.in_(document_ids))

    if is_postgres:
        # Postgres full-text search using ts_rank_cd and plainto_tsquery
        clean_query = query_text.replace("'", "''")
        fts_filter = text(
            f"to_tsvector('english', document_chunks.content) @@ plainto_tsquery('english', :q)"
        )
        rank_expr = text(
            f"ts_rank_cd(to_tsvector('english', document_chunks.content), plainto_tsquery('english', :q))"
        )
        pg_query = (
            query.filter(fts_filter)
            .params(q=query_text)
            .order_by(rank_expr.desc())
            .limit(top_k)
        )
        try:
            results = pg_query.all()
            return [
                CandidateChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_filename=filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    score=1.0,
                    retrieval_method="keyword",
                )
                for chunk, filename in results
            ]
        except Exception:
            # Fallback if FTS index/table setup in postgres encounters syntax variation
            pass

    # Lightweight BM25 / token overlap scoring for Portable / SQLite mode
    chunks_with_filename = query.all()
    if not chunks_with_filename:
        return []

    # Clean query tokens
    query_terms = [t.lower() for t in re.findall(r"\w+", query_text) if len(t) > 2]
    if not query_terms:
        query_terms = [t.lower() for t in query_text.split() if t]

    # Calculate corpus document frequencies
    total_docs = len(chunks_with_filename)
    df: Dict[str, int] = {term: 0 for term in query_terms}
    doc_tokens_list = []

    for chunk, _ in chunks_with_filename:
        tokens = [t.lower() for t in re.findall(r"\w+", chunk.content)]
        doc_tokens_list.append(tokens)
        token_set = set(tokens)
        for term in query_terms:
            if term in token_set:
                df[term] += 1

    # Average document length
    avg_dl = sum(len(t) for t in doc_tokens_list) / max(1, total_docs)
    k1 = 1.5
    b = 0.75

    scored = []
    for (chunk, filename), doc_tokens in zip(chunks_with_filename, doc_tokens_list):
        doc_len = len(doc_tokens)
        score = 0.0
        # Count term frequencies
        tf: Dict[str, int] = {}
        for t in doc_tokens:
            if t in df:
                tf[t] = tf.get(t, 0) + 1

        for term in query_terms:
            t_count = tf.get(term, 0)
            if t_count > 0:
                # IDF
                doc_freq = df.get(term, 0)
                idf = math.log((total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                # BM25 TF component
                num = t_count * (k1 + 1.0)
                denom = t_count + k1 * (1.0 - b + b * (doc_len / max(1.0, avg_dl)))
                score += idf * (num / denom)

        if score > 0.0:
            scored.append((score, chunk, filename))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = scored[:top_k]

    return [
        CandidateChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_filename=filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            score=score,
            retrieval_method="keyword",
        )
        for score, chunk, filename in top_candidates
    ]
