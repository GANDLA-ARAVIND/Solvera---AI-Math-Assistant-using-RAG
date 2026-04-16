from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class SolveHistory(Base):
    __tablename__ = "solve_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    query_image_path = Column(String(500), nullable=True)
    topic = Column(String(50), nullable=True)
    solution_text = Column(Text, nullable=False)
    sympy_verified = Column(Integer, default=0)  # 0=not verified, 1=correct, -1=mismatch
    rag_sources_used = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, server_default=func.now())
