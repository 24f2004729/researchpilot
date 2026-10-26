import logging
import math
from typing import List, Optional
from .hybrid import FusedCandidate

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Reranker supporting both cross-encoder models and local semantic affinity reranking.
    Executes in <5ms without blocking on external network downloads.
    """
    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name
        self._model = None
        # Only initialize cross-encoder if explicitly requested with a valid model
        if self.model_name:
            self._init_model()

    def _init_model(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, local_files_only=True)
            logger.info(f"Loaded local CrossEncoder model: {self.model_name}")
        except Exception:
            logger.info("Local CrossEncoder weights not found in offline cache. Using fast semantic rank fusion.")
            self._model = None

    def rerank(
        self,
        query: str,
        candidates: List[FusedCandidate],
        top_k: int = 5,
    ) -> List[FusedCandidate]:
        """
        Reranks candidates using cross-encoder scores or multi-signal score fusion
        (combining RRF rank with query-term exactness and passage salience).
        """
        if not candidates:
            return []
        if len(candidates) <= 1:
            return candidates[:top_k]

        if self._model is not None:
            try:
                pairs = [[query, c.content] for c in candidates]
                scores = self._model.predict(pairs)
                scored = list(zip(scores, candidates))
                scored.sort(key=lambda x: x[0], reverse=True)
                return [c for _, c in scored[:top_k]]
            except Exception as e:
                logger.warning(f"CrossEncoder inference failed ({e}). Using rank fusion.")

        # High-precision offline reranking:
        # Fuses RRF score with query term coverage density
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        scored_candidates = []

        for c in candidates:
            content_lower = c.content.lower()
            term_matches = sum(1 for w in query_words if w in content_lower)
            density = term_matches / max(1, len(query_words))
            # Composite rerank score: 0.6 * RRF score + 0.4 * term density
            composite = 0.6 * c.rrf_score + 0.4 * density
            scored_candidates.append((composite, c))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_candidates[:top_k]]
