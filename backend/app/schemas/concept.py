"""Pydantic schemas for the Concept Learning Mode."""

from pydantic import BaseModel, Field
from typing import Optional


# ── Concept Learning (topic-based) ──────────────────────────────────────

class ConceptRequest(BaseModel):
    topic: str = Field(..., description="Main topic (e.g. algebra, calculus)")
    subtopic: str = Field(..., description="Subtopic (e.g. quadratic_equations)")


class ConceptTopicRequest(BaseModel):
    """Request for the single-call /concept-mode endpoint."""
    topic: str = Field(..., description="Math topic (e.g. integration, algebra, derivatives)")


class PracticeAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Practice session ID")
    answer: str = Field(..., description="User's answer")


# ── Concept Assistant (free-form Q&A) ───────────────────────────────────

class ConceptAssistantRequest(BaseModel):
    question: str = Field(..., description="Any math concept question")


# ── Response models ─────────────────────────────────────────────────────

class ConceptExplanationResponse(BaseModel):
    topic: str
    subtopic: str
    explanation: str


class FormulaResponse(BaseModel):
    topic: str
    subtopic: str
    formulas: str


class ExampleResponse(BaseModel):
    topic: str
    subtopic: str
    example: str
    plot_url: Optional[str] = None


class PracticeQuestionResponse(BaseModel):
    session_id: Optional[str] = None
    question: str
    hint: Optional[str] = None
    difficulty: Optional[str] = None
    topic: str
    subtopic: str


class EvaluationResponse(BaseModel):
    session_id: str
    is_correct: Optional[bool] = None
    already_answered: Optional[bool] = None
    message: str
    user_answer: Optional[str] = None
    correct_answer: str
    solution: str
    feedback: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None


class ConceptBundleResponse(BaseModel):
    """Response from the single-call POST /concept-mode endpoint."""
    concept: str = ""
    formula: str = ""
    example: str = ""
    graph: Optional[str] = None
    practice_question: str = ""


class ConceptAssistantResponse(BaseModel):
    """Response from POST /concept-assistant."""
    answer: str = ""
    formula: str = ""
    example: str = ""
    steps: str = ""
    key_takeaway: str = ""


class PracticeEvalResponse(BaseModel):
    """Response from practice evaluation via the agent."""
    result: str  # "correct" | "incorrect" | "already_answered"
    correct_answer: str
    explanation: str
