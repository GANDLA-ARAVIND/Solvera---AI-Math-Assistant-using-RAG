"""JEE Exam Mode API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.services.auth_service import get_current_user
from app.schemas.exam import (
    StartExamRequest,
    SubmitAnswerRequest,
    NextQuestionRequest,
)
from app.services import exam_service

router = APIRouter()


@router.post("/start")
def start_exam(
    request: StartExamRequest,
    current_user: User = Depends(get_current_user),
):
    """Start a new JEE exam session with the specified difficulty level."""
    try:
        result = exam_service.start_exam(request.level, current_user.id)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start exam: {str(e)}")


@router.post("/submit")
def submit_answer(
    request: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit an answer for the current question."""
    try:
        result = exam_service.submit_answer(request.session_id, request.answer)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answer: {str(e)}")


@router.post("/next")
def next_question(
    request: NextQuestionRequest,
    current_user: User = Depends(get_current_user),
):
    """Get the next question in the exam session."""
    try:
        result = exam_service.next_question(request.session_id)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get next question: {str(e)}")


@router.get("/session/{session_id}")
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get current session info and statistics."""
    try:
        result = exam_service.get_session_info(session_id)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/end/{session_id}")
def end_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """End the exam session and return final stats."""
    try:
        result = exam_service.end_session(session_id)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
