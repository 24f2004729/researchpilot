import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.document import Document, IngestionJob
from ..models.chunk import DocumentChunk
from ..storage import get_storage
from ..rag.parser import DocumentParser
from ..rag.chunker import Chunker
from ..rag.embeddings import get_embedding_provider
from ..config import settings

logger = logging.getLogger(__name__)


def process_document(document_id: str, db: Optional[Session] = None) -> bool:
    """
    Executes the ingestion pipeline for a single document:
    1. Read binary from storage
    2. Extract text & page metadata
    3. Chunk content
    4. Generate embeddings
    5. Persist chunks & vectors in DB
    6. Transition status to 'ready'
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    storage = get_storage()
    embedder = get_embedding_provider()
    chunker = Chunker(
        target_chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return False

        job = (
            db.query(IngestionJob)
            .filter(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc())
            .first()
        )

        doc.status = "processing"
        if job:
            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)
            job.attempts += 1
        db.commit()

        # 1. Fetch file bytes
        file_bytes = storage.get(doc.storage_key)

        # 2. Parse text & page structure
        parse_result = DocumentParser.parse(doc.filename, file_bytes)

        # 3. Chunk text
        chunks = chunker.chunk_document(parse_result.pages)
        if not chunks:
            raise ValueError("No text chunks generated from document.")

        # 4. Generate embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = embedder.embed_documents(chunk_texts)

        # 5. Persist chunks
        # Clean any old chunks if this is a retry
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()

        db_chunks = []
        for i, chunk in enumerate(chunks):
            vec = embeddings[i] if i < len(embeddings) else None
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                embedding=vec,
            )
            db_chunks.append(db_chunk)

        db.bulk_save_objects(db_chunks)

        # 6. Mark ready
        doc.status = "ready"
        doc.page_count = parse_result.page_count
        doc.error_code = None

        if job:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_code = None

        db.commit()
        logger.info(f"Successfully indexed document {doc.id} ({len(db_chunks)} chunks).")
        return True

    except Exception as e:
        db.rollback()
        logger.exception(f"Ingestion failed for document {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            doc.error_code = str(e)[:100]
        if job:
            job.status = "failed"
            job.error_code = str(e)[:100]
            job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return False
    finally:
        if should_close_db:
            db.close()
