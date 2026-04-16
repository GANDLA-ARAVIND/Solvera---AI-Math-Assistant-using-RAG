from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("solve_history.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    correction_text = Column(Text, nullable=True)
    feedback_type = Column(String(20), default="rating")  # "rating", "correction", "flag"
    created_at = Column(DateTime, server_default=func.now())
