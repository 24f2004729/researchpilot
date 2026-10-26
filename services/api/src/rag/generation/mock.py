import asyncio
import re
import time
from typing import List, Any, AsyncGenerator, Dict
from .base import BaseLLMProvider
from .citations import GroundedAnswer, CitationValidator, Citation

STOP_WORDS = {
    "the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "to",
    "of", "for", "with", "as", "by", "that", "this", "it", "from", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "what", "how", "why", "when", "where", "who", "whom", "will",
    "can", "could", "would", "should", "about", "according", "mentioned"
}


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic grounded generation provider for local testing and zero-cost benchmarks.
    Extracts high-salience factual sentences from the provided context chunks,
    attaches verifiable citations with exact quotes, and abstains honestly when evidence is missing.
    """
    def __init__(self, model_name: str = "mock-grounded-v1") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        question: str,
        context_chunks: List[Any],
    ) -> GroundedAnswer:
        start_time = time.perf_counter()

        if not context_chunks:
            return GroundedAnswer(
                answer="I do not have sufficient evidence from the provided documents to answer this question.",
                citations=[],
                insufficient_evidence=True,
                model_name=self._model_name,
                input_tokens=len(question.split()),
                output_tokens=15,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )

        q_lower = question.lower()
        # Filter stopwords to capture true informative semantic query terms
        all_words = re.findall(r"\w+", q_lower)
        informative_terms = set(w for w in all_words if len(w) > 2 and w not in STOP_WORDS)

        if not informative_terms:
            return GroundedAnswer(
                answer="I do not have sufficient evidence from the provided documents to answer this question.",
                citations=[],
                insufficient_evidence=True,
                model_name=self._model_name,
                input_tokens=len(all_words),
                output_tokens=15,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )

        matched_sentences = []
        raw_citations = []

        for chunk in context_chunks:
            content = getattr(chunk, "content", "")
            sentences = re.split(r"(?<=[.!?])\s+", content)

            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) < 20:
                    continue
                s_words = set(re.findall(r"\w+", s_clean.lower())) - STOP_WORDS
                overlap = len(informative_terms.intersection(s_words))
                # Must match at least 2 informative terms or >= 40% of informative terms
                min_threshold = max(2, int(len(informative_terms) * 0.4))
                if overlap >= min_threshold:
                    matched_sentences.append((overlap, s_clean, chunk))

        # Sort sentences by keyword relevance
        matched_sentences.sort(key=lambda x: x[0], reverse=True)

        if not matched_sentences:
            return GroundedAnswer(
                answer="I do not have sufficient evidence from the provided documents to answer this question.",
                citations=[],
                insufficient_evidence=True,
                model_name=self._model_name,
                input_tokens=sum(len(getattr(c, "content", "").split()) for c in context_chunks),
                output_tokens=15,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Synthesize top 1-3 sentences into an answer
        selected = matched_sentences[:3]
        answer_parts = []
        for _, s_text, chunk in selected:
            chunk_id = getattr(chunk, "chunk_id", None) or getattr(chunk, "id", None)
            answer_parts.append(s_text)
            raw_citations.append({
                "source_id": str(chunk_id),
                "quote": s_text,
            })

        answer_text = " ".join(answer_parts)
        validated_citations = CitationValidator.validate_citations(
            raw_citations=raw_citations,
            context_chunks=context_chunks,
            answer_text=answer_text,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return GroundedAnswer(
            answer=answer_text,
            citations=validated_citations,
            insufficient_evidence=False,
            model_name=self._model_name,
            input_tokens=sum(len(getattr(c, "content", "").split()) for c in context_chunks),
            output_tokens=len(answer_text.split()),
            latency_ms=max(1, latency_ms),
        )

    async def stream_generate(
        self,
        question: str,
        context_chunks: List[Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        res = self.generate(question, context_chunks)
        words = res.answer.split(" ")

        for i, word in enumerate(words):
            yield {"type": "token", "text": word + (" " if i < len(words) - 1 else "")}
            await asyncio.sleep(0.01)

        yield {
            "type": "citations",
            "citations": [c.model_dump() for c in res.citations],
            "insufficient_evidence": res.insufficient_evidence,
        }

        yield {
            "type": "done",
            "model_name": res.model_name,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "latency_ms": res.latency_ms,
        }
