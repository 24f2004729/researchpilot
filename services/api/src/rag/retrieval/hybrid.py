from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from .dense import CandidateChunk, dense_search
from .keyword import keyword_search
from ..embeddings import BaseEmbeddingProvider
from ...config import settings


class FusedCandidate:
    def __init__(
        self,
        candidate: CandidateChunk,
        dense_rank: Optional[int] = None,
        keyword_rank: Optional[int] = None,
        rrf_score: float = 0.0,
    ) -> None:
        self.candidate = candidate
        self.dense_rank = dense_rank
        self.keyword_rank = keyword_rank
        self.rrf_score = rrf_score

    @property
    def chunk_id(self) -> str:
        return self.candidate.chunk_id

    @property
    def document_id(self) -> str:
        return self.candidate.document_id

    @property
    def document_filename(self) -> str:
        return self.candidate.document_filename

    @property
    def content(self) -> str:
        return self.candidate.content

    @property
    def page_number(self) -> Optional[int]:
        return self.candidate.page_number

    @property
    def section_title(self) -> Optional[str]:
        return self.candidate.section_title

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_filename": self.document_filename,
            "content": self.content,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "dense_rank": self.dense_rank,
            "keyword_rank": self.keyword_rank,
            "rrf_score": self.rrf_score,
        }


def hybrid_search(
    db: Session,
    workspace_id: str,
    query_text: str,
    embedder: BaseEmbeddingProvider,
    document_ids: Optional[List[str]] = None,
    candidate_pool_size: int = settings.RETRIEVAL_TOP_K,
    top_k: int = settings.RERANK_TOP_K,
    k_constant: int = settings.RRF_K,
) -> List[FusedCandidate]:
    """
    Executes hybrid retrieval combining dense vector similarity with full-text keyword search
    using Reciprocal Rank Fusion (RRF):
        RRF(d) = sum over rankings r of 1 / (k + rank_r(d))
    Applies workspace-level filtering at the database layer.
    """
    # 1. Embed query for dense search
    query_vec = embedder.embed_query(query_text)

    # 2. Parallel candidate retrieval
    dense_candidates = dense_search(
        db=db,
        workspace_id=workspace_id,
        query_vector=query_vec,
        document_ids=document_ids,
        top_k=candidate_pool_size,
    )

    keyword_candidates = keyword_search(
        db=db,
        workspace_id=workspace_id,
        query_text=query_text,
        document_ids=document_ids,
        top_k=candidate_pool_size,
    )

    # 3. Reciprocal Rank Fusion
    scores: Dict[str, float] = {}
    dense_ranks: Dict[str, int] = {}
    keyword_ranks: Dict[str, int] = {}
    candidate_lookup: Dict[str, CandidateChunk] = {}

    for rank, cand in enumerate(dense_candidates, start=1):
        cid = cand.chunk_id
        dense_ranks[cid] = rank
        candidate_lookup[cid] = cand
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k_constant + rank))

    for rank, cand in enumerate(keyword_candidates, start=1):
        cid = cand.chunk_id
        keyword_ranks[cid] = rank
        if cid not in candidate_lookup:
            candidate_lookup[cid] = cand
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k_constant + rank))

    # 4. Sort by fused RRF score descending
    sorted_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    fused_results: List[FusedCandidate] = []
    for cid, rrf_score in sorted_items[:top_k]:
        cand = candidate_lookup[cid]
        fused_results.append(
            FusedCandidate(
                candidate=cand,
                dense_rank=dense_ranks.get(cid),
                keyword_rank=keyword_ranks.get(cid),
                rrf_score=rrf_score,
            )
        )

    return fused_results
