from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from ..database import Base, PortableVector
from ..config import settings
from .user import generate_uuid, utc_now


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    embedding = Column(PortableVector(dimension=settings.EMBEDDING_DIMENSION), nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        Index("ix_chunks_doc_page", "document_id", "page_number"),
    )

    document = relationship("Document", back_populates="chunks")
    citations = relationship("MessageCitation", back_populates="chunk", cascade="all, delete-orphan")
