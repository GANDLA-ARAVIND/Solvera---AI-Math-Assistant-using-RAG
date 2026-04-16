"""Concept Learning Mode API routes."""

from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import get_current_user
from app.schemas.concept import (
    ConceptRequest,
    ConceptTopicRequest,
    PracticeAnswerRequest,
    ConceptExplanationResponse,
    FormulaResponse,
    ExampleResponse,
    PracticeQuestionResponse,
    EvaluationResponse,
    ConceptBundleResponse,
    PracticeEvalResponse,
)
from app.services.concept_service import (
    get_concept_explanation,
    get_formula,
    generate_example,
    generate_practice_question,
    evaluate_user_answer,
    get_supported_topics,
)
from app.agents.concept_agent import (
    learn_topic,
    generate_practice,
    evaluate_practice,
)

router = APIRouter()


# ── Single-call topic bundle (Feature 1) ────────────────────────────────

@router.post("", response_model=ConceptBundleResponse)
def concept_mode_bundle(req: ConceptTopicRequest, user=Depends(get_current_user)):
    """Return a complete learning bundle: concept + formula + example + graph + practice.

    POST /concept-mode
    """
    return learn_topic(req.topic)


# ── Practice question via agent (Feature 4) ─────────────────────────────

@router.post("/agent-practice")
def agent_practice(req: ConceptTopicRequest, user=Depends(get_current_user)):
    """Generate a practice question via the concept agent."""
    return generate_practice(req.topic)


@router.post("/agent-evaluate", response_model=PracticeEvalResponse)
def agent_evaluate(req: PracticeAnswerRequest, user=Depends(get_current_user)):
    """Evaluate practice answer via the concept agent (SymPy equivalence)."""
    try:
        return evaluate_practice(req.session_id, req.answer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Existing subtopic-level endpoints ───────────────────────────────────

@router.get("/topics")
def list_topics(user=Depends(get_current_user)):
    """Return the supported topic tree."""
    return get_supported_topics()


@router.post("/explain", response_model=ConceptExplanationResponse)
def explain_concept(req: ConceptRequest, user=Depends(get_current_user)):
    """Get a structured explanation of a concept."""
    topics = get_supported_topics()
    if req.topic not in topics:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {req.topic}")
    if req.subtopic not in topics[req.topic]:
        raise HTTPException(status_code=400, detail=f"Unknown subtopic: {req.subtopic}")
    return get_concept_explanation(req.topic, req.subtopic)


@router.post("/formula", response_model=FormulaResponse)
def concept_formula(req: ConceptRequest, user=Depends(get_current_user)):
    """Get key formulas for a subtopic."""
    topics = get_supported_topics()
    if req.topic not in topics:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {req.topic}")
    if req.subtopic not in topics[req.topic]:
        raise HTTPException(status_code=400, detail=f"Unknown subtopic: {req.subtopic}")
    return get_formula(req.topic, req.subtopic)


@router.post("/example", response_model=ExampleResponse)
def concept_example(req: ConceptRequest, user=Depends(get_current_user)):
    """Get a worked example for a subtopic."""
    topics = get_supported_topics()
    if req.topic not in topics:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {req.topic}")
    if req.subtopic not in topics[req.topic]:
        raise HTTPException(status_code=400, detail=f"Unknown subtopic: {req.subtopic}")
    return generate_example(req.topic, req.subtopic)


@router.post("/practice", response_model=PracticeQuestionResponse)
def concept_practice(req: ConceptRequest, user=Depends(get_current_user)):
    """Generate a practice question for a subtopic."""
    topics = get_supported_topics()
    if req.topic not in topics:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {req.topic}")
    if req.subtopic not in topics[req.topic]:
        raise HTTPException(status_code=400, detail=f"Unknown subtopic: {req.subtopic}")
    return generate_practice_question(req.topic, req.subtopic)


@router.post("/evaluate", response_model=EvaluationResponse)
def concept_evaluate(req: PracticeAnswerRequest, user=Depends(get_current_user)):
    """Evaluate a user's answer to a practice question."""
    try:
        return evaluate_user_answer(req.session_id, req.answer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
