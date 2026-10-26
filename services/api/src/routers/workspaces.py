from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.workspace import Workspace
from ..schemas.api import WorkspaceCreateRequest, WorkspaceResponse
from .deps import get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    req: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = Workspace(
        name=req.name.strip(),
        owner_id=user.id,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        owner_id=ws.owner_id,
        created_at=ws.created_at,
    )


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspaces = (
        db.query(Workspace)
        .filter(Workspace.owner_id == user.id)
        .order_by(Workspace.created_at.asc())
        .all()
    )
    return [
        WorkspaceResponse(
            id=w.id,
            name=w.name,
            owner_id=w.owner_id,
            created_at=w.created_at,
        )
        for w in workspaces
    ]
