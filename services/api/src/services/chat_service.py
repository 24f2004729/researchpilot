import time
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from sqlalchemy.orm import Session
from ..models.chat import Conversation, Message, MessageCitation
from ..models.document import Document
from ..rag.retrieval.hybrid import hybrid_search, FusedCandidate
from ..rag.embeddings import get_embedding_provider
from ..rag.generation import get_llm_provider, GroundedAnswer, Citation

logger = logging.getLogger(__name__)


class ChatService:
    @staticmethod
    def verify_documents_ready(
        db: Session,
        workspace_id: str,
        document_ids: List[str],
    ) -> List[Document]:
        """
        Ensures all requested documents belong to the workspace and are ready for querying.
        """
        if not document_ids:
            return []

        docs = (
            db.query(Document)
            .filter(Document.workspace_id == workspace_id)
            .filter(Document.id.in_(document_ids))
            .all()
        )

        found_ids = {d.id for d in docs}
        missing = set(document_ids) - found_ids
        if missing:
            raise ValueError(f"Documents not found or inaccessible: {list(missing)}")

        not_ready = [d for d in docs if d.status != "ready"]
        if not_ready:
            raise ValueError(
                f"Selected document '{not_ready[0].filename}' is not ready for search (status: {not_ready[0].status})."
            )

        return docs

    @classmethod
    def answer_question(
        cls,
        db: Session,
        workspace_id: str,
        user_id: str,
        conversation_id: str,
        question: str,
        document_ids: Optional[List[str]] = None,
    ) -> GroundedAnswer:
        """
        Executes end-to-end question answering:
        1. Authorize workspace and verify selected documents
        2. Record user message
        3. Execute hybrid retrieval
        4. Generate grounded answer
        5. Validate citations
        6. Persist assistant message and citation links
        """
        start_time = time.perf_counter()

        # 1. Authorize conversation
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .filter(Conversation.workspace_id == workspace_id)
            .first()
        )
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found in workspace.")

        # 2. Check documents
        if document_ids:
            cls.verify_documents_ready(db, workspace_id, document_ids)

        # 3. Persist user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
            status="completed",
        )
        db.add(user_msg)
        db.commit()

        # 4. Hybrid retrieval
        embedder = get_embedding_provider()
        candidates = hybrid_search(
            db=db,
            workspace_id=workspace_id,
            query_text=question,
            embedder=embedder,
            document_ids=document_ids,
        )

        # 5. LLM generation
        llm = get_llm_provider()
        grounded_answer = llm.generate(question=question, context_chunks=candidates)

        # Total latency
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 6. Persist assistant response
        asst_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=grounded_answer.answer,
            status="completed",
            model_name=grounded_answer.model_name or llm.model_name,
            input_tokens=grounded_answer.input_tokens,
            output_tokens=grounded_answer.output_tokens,
            latency_ms=total_latency_ms,
        )
        db.add(asst_msg)
        db.commit()
        db.refresh(asst_msg)

        # Persist citations
        for order, cit in enumerate(grounded_answer.citations, start=1):
            if cit.is_valid:
                db_cit = MessageCitation(
                    message_id=asst_msg.id,
                    chunk_id=cit.source_id,
                    citation_order=order,
                    quote=cit.quote,
                    page_number=cit.page,
                )
                db.add(db_cit)

        db.commit()
        grounded_answer.latency_ms = total_latency_ms
        return grounded_answer

    @classmethod
    async def stream_answer(
        cls,
        db: Session,
        workspace_id: str,
        user_id: str,
        conversation_id: str,
        question: str,
        document_ids: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams answer generation with SSE event semantics.
        Yields status, tokens, citations, and completion event.
        """
        start_time = time.perf_counter()

        # 1. Verification
        yield {"type": "status", "stage": "verifying_documents"}
        if document_ids:
            cls.verify_documents_ready(db, workspace_id, document_ids)

        # 2. Persist user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
            status="completed",
        )
        db.add(user_msg)
        db.commit()

        # 3. Retrieval
        yield {"type": "status", "stage": "retrieving"}
        embedder = get_embedding_provider()
        candidates = hybrid_search(
            db=db,
            workspace_id=workspace_id,
            query_text=question,
            embedder=embedder,
            document_ids=document_ids,
        )

        # 4. Stream tokens
        yield {"type": "status", "stage": "generating"}
        llm = get_llm_provider()
        full_text_parts = []
        citations_data = []
        metadata = {}

        async for event in llm.stream_generate(question, candidates):
            if event["type"] == "token":
                full_text_parts.append(event["text"])
                yield event
            elif event["type"] == "citations":
                citations_data = event["citations"]
                yield event
            elif event["type"] == "done":
                metadata = event

        full_answer = "".join(full_text_parts)
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 5. Persist assistant message
        asst_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_answer,
            status="completed",
            model_name=metadata.get("model_name", llm.model_name),
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
            latency_ms=total_latency_ms,
        )
        db.add(asst_msg)
        db.commit()
        db.refresh(asst_msg)

        # Persist citations
        for order, cit in enumerate(citations_data, start=1):
            if cit.get("is_valid", True):
                db_cit = MessageCitation(
                    message_id=asst_msg.id,
                    chunk_id=cit.get("source_id"),
                    citation_order=order,
                    quote=cit.get("quote"),
                    page_number=cit.get("page"),
                )
                db.add(db_cit)

        db.commit()

        yield {
            "type": "done",
            "message_id": asst_msg.id,
            "latency_ms": total_latency_ms,
        }
