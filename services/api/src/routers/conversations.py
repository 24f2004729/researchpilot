import json
from typing import List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.workspace import Workspace
from ..models.chat import Conversation, Message
from ..services.chat_service import ChatService
from ..schemas.api import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
    CitationResponse,
    QuestionRequest,
)
from .deps import get_current_user, verify_workspace_access

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: ConversationCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_workspace_access(workspace_id=req.workspace_id, user=user, db=db)
    conv = Conversation(
        workspace_id=req.workspace_id,
        user_id=user.id,
        title=req.title or "New Research Session",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse(
        id=conv.id,
        workspace_id=conv.workspace_id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_history(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .filter(Conversation.id == conversation_id)
        .filter(Workspace.owner_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONVERSATION_NOT_FOUND", "message": "Conversation not found or inaccessible."},
        )

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    msg_responses = []
    for m in messages:
        cits = [
            CitationResponse(
                source_id=c.chunk_id,
                document_id=c.chunk.document_id if c.chunk else None,
                document_filename=c.chunk.document.filename if c.chunk and c.chunk.document else "Document",
                page=c.page_number,
                quote=c.quote,
                is_valid=True,
                is_supported=True,
            )
            for c in m.citations
        ]
        msg_responses.append(
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                status=m.status,
                model_name=m.model_name,
                input_tokens=m.input_tokens,
                output_tokens=m.output_tokens,
                latency_ms=m.latency_ms,
                created_at=m.created_at,
                citations=cits,
            )
        )

    return ConversationDetailResponse(
        id=conv.id,
        workspace_id=conv.workspace_id,
        title=conv.title,
        created_at=conv.created_at,
        messages=msg_responses,
    )


@router.post("/{conversation_id}/messages")
async def ask_question(
    conversation_id: str,
    req: QuestionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .filter(Conversation.id == conversation_id)
        .filter(Workspace.owner_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONVERSATION_NOT_FOUND", "message": "Conversation not found or inaccessible."},
        )

    if req.stream:
        async def sse_event_stream() -> AsyncGenerator[str, None]:
            # Each SSE stream requires its own session
            from ..database import SessionLocal
            stream_db = SessionLocal()
            try:
                async for event in ChatService.stream_answer(
                    db=stream_db,
                    workspace_id=conv.workspace_id,
                    user_id=user.id,
                    conversation_id=conv.id,
                    question=req.question,
                    document_ids=req.document_ids,
                ):
                    event_type = event.get("type", "message")
                    event_payload = json.dumps(event)
                    yield f"event: {event_type}\ndata: {event_payload}\n\n"
            except Exception as e:
                err_data = json.dumps({"code": "STREAM_ERROR", "message": str(e)})
                yield f"event: error\ndata: {err_data}\n\n"
            finally:
                stream_db.close()

        return StreamingResponse(
            sse_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Synchronous JSON response
    try:
        answer = ChatService.answer_question(
            db=db,
            workspace_id=conv.workspace_id,
            user_id=user.id,
            conversation_id=conv.id,
            question=req.question,
            document_ids=req.document_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "QUESTION_FAILED", "message": str(e)},
        )

    # Fetch newly created message
    asst_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .first()
    )

    cits = [
        CitationResponse(
            source_id=c.source_id,
            document_id=c.document_id,
            document_filename=c.document_filename,
            page=c.page,
            quote=c.quote,
            is_valid=c.is_valid,
            is_supported=c.is_supported,
        )
        for c in answer.citations
    ]

    return MessageResponse(
        id=asst_msg.id if asst_msg else "tmp",
        role="assistant",
        content=answer.answer,
        status="completed",
        model_name=answer.model_name,
        input_tokens=answer.input_tokens,
        output_tokens=answer.output_tokens,
        latency_ms=answer.latency_ms,
        created_at=asst_msg.created_at if asst_msg else conv.created_at,
        citations=cits,
    )
