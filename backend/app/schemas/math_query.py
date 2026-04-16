from pydantic import BaseModel
from typing import Optional


class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class MathQueryRequest(BaseModel):
    query: str
    include_plot: Optional[bool] = False
    conversation_history: Optional[list[ConversationMessage]] = None


class RAGSource(BaseModel):
    title: str
    topic: str
    relevance: float


class ValidationResult(BaseModel):
    attempted: Optional[bool] = None
    verified: Optional[bool] = None
    sympy_answer: Optional[str] = None
    match: Optional[bool] = None
    details: Optional[str] = None
    reason: Optional[str] = None


class MathQueryResponse(BaseModel):
    success: bool
    query: Optional[str] = None
    topic: Optional[str] = None
    solution: Optional[str] = None
    validation: Optional[ValidationResult] = None
    rag_sources: Optional[list[RAGSource]] = None
    history_id: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    plot_url: Optional[str] = None
    difficulty: Optional[str] = None
    follow_up_suggestions: Optional[list[str]] = None
