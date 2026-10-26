import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.workspace import Workspace
from ..services.auth_service import AuthService


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authorization header."},
        )

    token = authorization.split(" ")[1]
    payload = AuthService.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Token expired or malformed."},
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found."},
        )
    return user


def verify_workspace_access(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    ws = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .filter(Workspace.owner_id == user.id)
        .first()
    )
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "WORKSPACE_ACCESS_DENIED", "message": "Access to workspace denied."},
        )
    return ws
