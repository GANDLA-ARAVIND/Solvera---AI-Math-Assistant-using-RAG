from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.history import SolveHistory
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/")
def get_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(SolveHistory)
        .filter(SolveHistory.user_id == current_user.id)
        .order_by(SolveHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "query_text": e.query_text,
            "topic": e.topic,
            "sympy_verified": e.sympy_verified,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.get("/{history_id}")
def get_history_detail(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(SolveHistory)
        .filter(SolveHistory.id == history_id, SolveHistory.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    return {
        "id": entry.id,
        "query_text": entry.query_text,
        "query_image_path": entry.query_image_path,
        "topic": entry.topic,
        "solution_text": entry.solution_text,
        "sympy_verified": entry.sympy_verified,
        "rag_sources_used": entry.rag_sources_used,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.delete("/{history_id}")
def delete_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(SolveHistory)
        .filter(SolveHistory.id == history_id, SolveHistory.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted successfully"}
