from pydantic import BaseModel
from typing import Optional


class StartExamRequest(BaseModel):
    level: str  # "basic", "medium", "hard"


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str


class NextQuestionRequest(BaseModel):
    session_id: str


class ExamQuestionResponse(BaseModel):
    session_id: str
    question_number: int
    total_questions: int
    question: str
    topic: str
    difficulty: str
    score: int
    correct_count: int


class AnswerResultResponse(BaseModel):
    is_correct: bool
    message: str
    correct_answer: str
    user_answer: str
    solution: str
    time_taken_seconds: float
    score: int
    correct_count: int
    total_attempted: int
    accuracy_percent: float
    session_id: str


class ExamSessionInfo(BaseModel):
    session_id: str
    difficulty: str
    score: int
    correct_count: int
    total_attempted: int
    accuracy_percent: float
    total_time_seconds: float
    weak_topics: list[str]
