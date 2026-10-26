from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db
from ..storage import get_storage

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def liveness():
    return {"status": "ok", "service": "researchpilot-api"}


@router.get("/ready")
def readiness(db: Session = Depends(get_db)):
    # 1. Database check
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": f"Database health check failed: {e}"},
        )

    # 2. Storage check
    try:
        storage = get_storage()
        # Verify base path / connection
        if hasattr(storage, "base_dir") and not storage.base_dir.exists():
            storage.base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "STORAGE_UNAVAILABLE", "message": f"Storage health check failed: {e}"},
        )

    return {"status": "ready", "database": "connected", "storage": "available"}
