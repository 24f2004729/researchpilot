from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.workspace import Workspace
from ..models.document import Document
from ..services.document_service import DocumentService
from ..schemas.api import DocumentUploadResponse, DocumentResponse
from .deps import get_current_user, verify_workspace_access

router = APIRouter(tags=["Documents"])


@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify user owns workspace
    verify_workspace_access(workspace_id=workspace_id, user=user, db=db)

    content = await file.read()
    try:
        doc, is_dup = DocumentService.upload_document(
            db=db,
            workspace_id=workspace_id,
            filename=file.filename or "unknown.pdf",
            content=content,
            mime_type=file.content_type or "application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_DOCUMENT", "message": str(e)},
        )

    msg = "Duplicate document detected; existing record reused." if is_dup else "Document queued for ingestion."
    return DocumentUploadResponse(
        document_id=doc.id,
        status=doc.status,
        filename=doc.filename,
        message=msg,
    )


@router.get("/workspaces/{workspace_id}/documents", response_model=List[DocumentResponse])
def list_workspace_documents(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_workspace_access(workspace_id=workspace_id, user=user, db=db)
    docs = (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        DocumentResponse(
            id=d.id,
            workspace_id=d.workspace_id,
            filename=d.filename,
            size_bytes=d.size_bytes,
            page_count=d.page_count,
            status=d.status,
            error_code=d.error_code,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_details(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .join(Workspace, Document.workspace_id == Workspace.id)
        .filter(Document.id == document_id)
        .filter(Workspace.owner_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found or inaccessible."},
        )
    return DocumentResponse(
        id=doc.id,
        workspace_id=doc.workspace_id,
        filename=doc.filename,
        size_bytes=doc.size_bytes,
        page_count=doc.page_count,
        status=doc.status,
        error_code=doc.error_code,
        created_at=doc.created_at,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .join(Workspace, Document.workspace_id == Workspace.id)
        .filter(Document.id == document_id)
        .filter(Workspace.owner_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found or inaccessible."},
        )

    deleted = DocumentService.delete_document(db, doc.id, doc.workspace_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DELETE_FAILED", "message": "Failed to delete document."},
        )
    return None


@router.post("/documents/{document_id}/retry", response_model=DocumentResponse)
def retry_document_ingestion(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .join(Workspace, Document.workspace_id == Workspace.id)
        .filter(Document.id == document_id)
        .filter(Workspace.owner_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found or inaccessible."},
        )

    try:
        retried = DocumentService.retry_ingestion(db, doc.id, doc.workspace_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "RETRY_NOT_ALLOWED", "message": str(e)},
        )

    return DocumentResponse(
        id=retried.id,
        workspace_id=retried.workspace_id,
        filename=retried.filename,
        size_bytes=retried.size_bytes,
        page_count=retried.page_count,
        status=retried.status,
        error_code=retried.error_code,
        created_at=retried.created_at,
    )
