import math
import re
from typing import List, Dict, Any, Optional


def match_gold_chunk(content: str, gold_keywords: List[str]) -> bool:
    """Checks whether a retrieved chunk contains the required gold keywords."""
    if not gold_keywords:
        return False
    content_lower = content.lower()
    # Check if at least 60% of gold keywords are present in the chunk
    present_count = sum(1 for kw in gold_keywords if kw.lower() in content_lower)
    return present_count >= max(1, math.ceil(len(gold_keywords) * 0.6))


def calculate_recall_at_k(retrieved_contents: List[str], gold_keywords: List[str], k: int) -> float:
    """
    Fraction of queries with at least one relevant passage retrieved in top-k.
    """
    if not gold_keywords:
        # For unanswerable queries, retrieval recall is not applicable (N/A)
        return 1.0

    top_k = retrieved_contents[:k]
    for content in top_k:
        if match_gold_chunk(content, gold_keywords):
            return 1.0
    return 0.0


def calculate_mrr(retrieved_contents: List[str], gold_keywords: List[str]) -> float:
    """
    Reciprocal rank of the first relevant chunk retrieved.
    """
    if not gold_keywords:
        return 1.0

    for rank, content in enumerate(retrieved_contents, start=1):
        if match_gold_chunk(content, gold_keywords):
            return 1.0 / rank
    return 0.0


def calculate_ndcg_at_k(retrieved_contents: List[str], gold_keywords: List[str], k: int = 5) -> float:
    """
    Normalized Discounted Cumulative Gain at k.
    """
    if not gold_keywords:
        return 1.0

    top_k = retrieved_contents[:k]
    dcg = 0.0
    idcg = 0.0

    for i, content in enumerate(top_k):
        rel = 1.0 if match_gold_chunk(content, gold_keywords) else 0.0
        dcg += (2.0 ** rel - 1.0) / math.log2(i + 2.0)

    # Ideal ranking has at least one relevant passage at rank 1
    idcg = (2.0 ** 1.0 - 1.0) / math.log2(0 + 2.0)

    return (dcg / idcg) if idcg > 0 else 0.0


def calculate_citation_metrics(citations: List[Any]) -> Dict[str, float]:
    """
    Distinguishes citation validity (resolving to context chunk) from citation support (quote match).
    """
    if not citations:
        return {"citation_validity": 1.0, "citation_support": 1.0}

    valid_count = sum(1 for c in citations if getattr(c, "is_valid", False))
    supported_count = sum(1 for c in citations if getattr(c, "is_supported", False))

    validity = valid_count / len(citations)
    support = (supported_count / valid_count) if valid_count > 0 else 0.0

    return {
        "citation_validity": validity,
        "citation_support": support,
    }


def calculate_answer_correctness(answer_text: str, gold_keywords: List[str], should_abstain: bool, is_abstained: bool) -> float:
    """
    Scores answer agreement:
    - If should_abstain: 1.0 if system abstains, 0.0 if system hallucinates an answer.
    - If answerable: checks recall of gold keywords in the generated answer.
    """
    if should_abstain:
        return 1.0 if is_abstained else 0.0

    if is_abstained and not should_abstain:
        # False abstention on answerable query
        return 0.0

    if not gold_keywords:
        return 1.0

    ans_lower = answer_text.lower()
    matched = sum(1 for kw in gold_keywords if kw.lower() in ans_lower)
    return matched / len(gold_keywords)
