from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.models.history import SolveHistory
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.auth_service import get_current_user

router = APIRouter()


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(
    data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify the history entry exists and belongs to the user
    history_entry = (
        db.query(SolveHistory)
        .filter(
            SolveHistory.id == data.history_id,
            SolveHistory.user_id == current_user.id,
        )
        .first()
    )
    if not history_entry:
        raise HTTPException(status_code=404, detail="History entry not found")

    feedback = Feedback(
        history_id=data.history_id,
        user_id=current_user.id,
        rating=data.rating,
        correction_text=data.correction_text,
        feedback_type=data.feedback_type or "rating",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)


@router.get("/{history_id}", response_model=list[FeedbackResponse])
def get_feedback(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    feedbacks = (
        db.query(Feedback)
        .filter(Feedback.history_id == history_id)
        .order_by(Feedback.created_at.desc())
        .all()
    )
    return [FeedbackResponse.model_validate(f) for f in feedbacks]
