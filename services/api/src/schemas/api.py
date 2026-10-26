from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


# Workspace Schemas
class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime


# Document Schemas
class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str
    filename: str
    message: Optional[str] = "Document uploaded and queued for processing."


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    filename: str
    size_bytes: int
    page_count: int
    status: str
    error_code: Optional[str] = None
    created_at: datetime


# Conversation & Message Schemas
class ConversationCreateRequest(BaseModel):
    workspace_id: str
    title: Optional[str] = "New Research Session"


class ConversationResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class CitationResponse(BaseModel):
    source_id: str
    document_id: Optional[str] = None
    document_filename: Optional[str] = None
    page: Optional[int] = None
    quote: Optional[str] = None
    is_valid: bool = True
    is_supported: bool = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    status: str
    model_name: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    created_at: datetime
    citations: List[CitationResponse] = []


class ConversationDetailResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    created_at: datetime
    messages: List[MessageResponse] = []


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    document_ids: Optional[List[str]] = None
    stream: bool = False


# Error Envelope
class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
