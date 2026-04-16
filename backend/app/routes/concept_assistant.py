"""Concept Assistant (Chat Tutor) API route.

POST /concept-assistant — free-form math concept Q&A using RAG + Gemini.
"""

from fastapi import APIRouter, Depends
from app.services.auth_service import get_current_user
from app.schemas.concept import ConceptAssistantRequest, ConceptAssistantResponse
from app.agents.concept_agent import ask_assistant

router = APIRouter()


@router.post("", response_model=ConceptAssistantResponse)
def concept_assistant(req: ConceptAssistantRequest, user=Depends(get_current_user)):
    """Answer any math concept question using RAG + Gemini.

    POST /concept-assistant
    """
    return ask_assistant(req.question)
