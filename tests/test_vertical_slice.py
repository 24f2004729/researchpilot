import os
import io
import pytest
import pymupdf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.api.src.database import Base
from services.api.src.models.user import User
from services.api.src.models.workspace import Workspace
from services.api.src.models.document import Document
from services.api.src.models.chunk import DocumentChunk
from services.api.src.models.chat import Conversation, Message
from services.api.src.services.document_service import DocumentService
from services.api.src.services.ingestion_worker import process_document
from services.api.src.services.chat_service import ChatService
from services.api.src.rag.retrieval.hybrid import hybrid_search
from services.api.src.rag.embeddings import get_embedding_provider
from services.api.src.rag.generation.citations import CitationValidator

TEST_DB_URL = "sqlite:///./test_slice.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    # Create test user and workspace
    user = User(email="researcher@example.com", hashed_password="hashed_test_password")
    db.add(user)
    db.commit()
    db.refresh(user)

    ws = Workspace(name="Distributed Systems Lab", owner_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    yield db, user, ws

    db.close()
    test_engine.dispose()
    if os.path.exists("./test_slice.db"):
        try:
            os.remove("./test_slice.db")
        except Exception:
            pass


def create_sample_pdf_bytes() -> bytes:
    """Creates an in-memory test PDF with structured paragraphs and headings."""
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text(
        pymupdf.Point(50, 72),
        "CONSENSUS IN DISTRIBUTED SYSTEMS\n\n"
        "Abstract\n"
        "Distributed consensus requires all non-faulty nodes to agree on a sequence of state machine actions.\n"
        "Raft is a consensus algorithm designed as an alternative to Multi-Paxos.\n"
        "It divides consensus into leader election, log replication, and safety invariants.\n\n"
        "Leader Election Protocol\n"
        "In Raft, a leader is elected through randomized election timeouts between 150ms and 300ms.\n"
        "When a follower receives no heartbeat within the timeout window, it transitions to candidate state.\n"
        "The candidate increments its current term and votes for itself before requesting votes from peers.\n",
        fontsize=11,
    )
    page2 = doc.new_page()
    page2.insert_text(
        pymupdf.Point(50, 72),
        "Log Replication and Latency\n"
        "Once a leader is elected, it manages client requests and replicates entries to all follower logs.\n"
        "Synchronous replication can increase write latency across geo-distributed nodes.\n"
        "An entry is considered committed once it has been replicated on a majority of cluster nodes.\n"
        "Heartbeats are transmitted periodically at 50ms intervals to maintain leadership authority.\n",
        fontsize=11,
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_vertical_slice_end_to_end(setup_test_db, monkeypatch):
    db, user, ws = setup_test_db
    monkeypatch.setattr("services.api.src.services.ingestion_worker.SessionLocal", TestSessionLocal)

    # 1. Upload Document
    pdf_bytes = create_sample_pdf_bytes()
    doc, is_dup = DocumentService.upload_document(
        db=db,
        workspace_id=ws.id,
        filename="raft_consensus.pdf",
        content=pdf_bytes,
        mime_type="application/pdf",
    )
    assert doc.id is not None
    assert doc.status == "queued"
    assert doc.size_bytes == len(pdf_bytes)
    assert not is_dup

    # 2. Ingestion Processing (Synchronous execution for deterministic verification)
    success = process_document(doc.id, db=db)
    assert success is True

    # Verify document status updated to 'ready'
    db.refresh(doc)
    assert doc.status == "ready"
    assert doc.page_count == 2

    # Verify chunks extracted and stored
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    assert len(chunks) >= 2
    chunk_ids = [c.id for c in chunks]
    for c in chunks:
        assert c.content is not None
        assert len(c.content) > 20
        assert c.page_number in [1, 2]

    # 3. Hybrid Retrieval Verification
    embedder = get_embedding_provider()
    fused = hybrid_search(
        db=db,
        workspace_id=ws.id,
        query_text="What are the randomized election timeouts in Raft?",
        embedder=embedder,
        document_ids=[doc.id],
        top_k=3,
    )
    assert len(fused) > 0
    top_chunk_content = fused[0].content
    assert "150ms" in top_chunk_content or "timeout" in top_chunk_content.lower()

    # 4. End-to-End Chat & Citation Generation
    conv = Conversation(workspace_id=ws.id, user_id=user.id, title="Raft Research")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    answer = ChatService.answer_question(
        db=db,
        workspace_id=ws.id,
        user_id=user.id,
        conversation_id=conv.id,
        question="What are the election timeouts and how does leader election work?",
        document_ids=[doc.id],
    )

    assert answer.answer is not None
    assert len(answer.answer) > 20
    assert answer.insufficient_evidence is False
    assert len(answer.citations) > 0

    # 5. Citation Validation Checks
    for cit in answer.citations:
        assert cit.is_valid is True
        assert cit.document_filename == "raft_consensus.pdf"
        assert cit.source_id in chunk_ids
        if cit.quote:
            # Verified quote support
            assert cit.is_supported is True

    # 6. Honest Abstention on Unanswerable Query
    unanswerable = ChatService.answer_question(
        db=db,
        workspace_id=ws.id,
        user_id=user.id,
        conversation_id=conv.id,
        question="What is the stock price of Apple xyznotfound in 2040?",
        document_ids=[doc.id],
    )
    assert unanswerable.insufficient_evidence is True
    assert CitationValidator.is_abstention(unanswerable.answer) is True

    # 7. Document Deletion and Clean-up Verification
    deleted = DocumentService.delete_document(db, doc.id, ws.id)
    assert deleted is True

    # Confirm chunks deleted
    remaining_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    assert remaining_chunks == 0
