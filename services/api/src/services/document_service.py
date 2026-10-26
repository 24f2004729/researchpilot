import hashlib
import logging
import uuid
import threading
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from ..models.document import Document, IngestionJob
from ..models.chunk import DocumentChunk
from ..storage import get_storage
from .ingestion_worker import process_document
from ..config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class DocumentService:
    @staticmethod
    def validate_file(filename: str, content: bytes, mime_type: Optional[str] = None) -> None:
        if not filename or "." not in filename:
            raise ValueError("Invalid filename: missing extension.")

        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '.{ext}'. Supported: {list(ALLOWED_EXTENSIONS)}")

        if len(content) == 0:
            raise ValueError("Uploaded file is empty.")

        if len(content) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum limit of 25 MB (was {len(content)} bytes).")

        # Signature check for PDF: magic bytes %PDF
        if ext == "pdf" and not content.startswith(b"%PDF"):
            raise ValueError("Invalid PDF file: missing %PDF header magic bytes.")

    @staticmethod
    def compute_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def upload_document(
        cls,
        db: Session,
        workspace_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "application/pdf",
    ) -> Tuple[Document, bool]:
        """
        Validates, saves to object storage, creates database records,
        and triggers background ingestion.
        Returns (document, is_duplicate).
        """
        cls.validate_file(filename, content, mime_type)
        content_hash = cls.compute_hash(content)

        # Check for existing duplicate document in same workspace
        existing = (
            db.query(Document)
            .filter(Document.workspace_id == workspace_id)
            .filter(Document.content_hash == content_hash)
            .first()
        )
        if existing and existing.status in ["ready", "processing", "queued"]:
            return existing, True

        # Generate unique storage key
        storage_key = f"{uuid.uuid4().hex}_{hashlib.md5(filename.encode()).hexdigest()[:8]}"
        storage = get_storage()
        storage.save(storage_key, content)

        doc = Document(
            workspace_id=workspace_id,
            filename=filename,
            storage_key=storage_key,
            content_hash=content_hash,
            mime_type=mime_type,
            size_bytes=len(content),
            status="queued",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        job = IngestionJob(
            document_id=doc.id,
            status="queued",
            attempts=0,
        )
        db.add(job)
        db.commit()

        # Enqueue task
        cls.enqueue_ingestion(doc.id)

        return doc, False

    @classmethod
    def enqueue_ingestion(cls, document_id: str) -> None:
        """Enqueues document ingestion either in a background thread or Celery."""
        if settings.TASK_EXECUTION_MODE == "celery":
            try:
                from ..worker import celery_app
                celery_app.send_task("tasks.process_document", args=[document_id])
                return
            except Exception as e:
                logger.warning(f"Failed to enqueue to Celery ({e}). Running in background thread.")

        # In-process asynchronous thread
        t = threading.Thread(target=process_document, args=(document_id,), daemon=True)
        t.start()

    @classmethod
    def retry_ingestion(cls, db: Session, document_id: str, workspace_id: str) -> Document:
        doc = (
            db.query(Document)
            .filter(Document.id == document_id)
            .filter(Document.workspace_id == workspace_id)
            .first()
        )
        if not doc:
            raise ValueError(f"Document {document_id} not found in workspace.")

        if doc.status not in ["failed", "queued"]:
            raise ValueError(f"Document status '{doc.status}' is not eligible for retry.")

        doc.status = "queued"
        doc.error_code = None
        db.commit()

        cls.enqueue_ingestion(doc.id)
        return doc

    @classmethod
    def delete_document(cls, db: Session, document_id: str, workspace_id: str) -> bool:
        doc = (
            db.query(Document)
            .filter(Document.id == document_id)
            .filter(Document.workspace_id == workspace_id)
            .first()
        )
        if not doc:
            return False

        # 1. Remove from object storage
        storage = get_storage()
        try:
            storage.delete(doc.storage_key)
        except Exception as e:
            logger.warning(f"Failed to delete storage file {doc.storage_key}: {e}")

        # 2. Delete database records (chunks cascade deleted via FK)
        db.delete(doc)
        db.commit()
        return True
