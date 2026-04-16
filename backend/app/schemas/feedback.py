from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FeedbackCreate(BaseModel):
    history_id: int
    rating: int  # 1-5
    correction_text: Optional[str] = None
    feedback_type: Optional[str] = "rating"


class FeedbackResponse(BaseModel):
    id: int
    history_id: int
    user_id: int
    rating: int
    correction_text: Optional[str] = None
    feedback_type: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
