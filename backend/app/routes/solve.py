import json
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.history import SolveHistory
from app.schemas.math_query import MathQueryRequest
from app.services.solver_service import solver_service
from app.services.plot_service import plot_service
from app.services.auth_service import get_current_user

router = APIRouter()

# Simple in-memory rate limiter: max 20 requests per minute per user
_rate_limits: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 60  # seconds


def _check_rate_limit(user_id: int):
    now = time.time()
    # Clean old entries
    _rate_limits[user_id] = [
        t for t in _rate_limits[user_id] if now - t < RATE_WINDOW
    ]
    if len(_rate_limits[user_id]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment before trying again.",
        )
    _rate_limits[user_id].append(now)


@router.post("/")
async def solve_math_problem(
    request: MathQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_rate_limit(current_user.id)

    # Convert conversation history to dicts if provided
    conv_history = None
    if request.conversation_history:
        conv_history = [msg.model_dump() for msg in request.conversation_history]

    result = await solver_service.solve(
        request.query,
        user_id=current_user.id,
        include_plot=request.include_plot or False,
        conversation_history=conv_history,
    )

    if not result["success"]:
        return result

    # Save to history
    validation = result.get("validation", {})
    match_val = validation.get("match")
    sympy_flag = 1 if match_val is True else (-1 if match_val is False else 0)

    history_entry = SolveHistory(
        user_id=current_user.id,
        query_text=request.query,
        topic=result.get("topic"),
        solution_text=result["solution"],
        sympy_verified=sympy_flag,
        rag_sources_used=json.dumps(result.get("rag_sources", [])),
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    result["history_id"] = history_entry.id
    return result


@router.post("/plot")
async def generate_plot(
    expression: str = Query(..., description="Math expression to plot, e.g. x**2 - 4"),
    x_min: float = Query(-10, description="Minimum x value"),
    x_max: float = Query(10, description="Maximum x value"),
    current_user: User = Depends(get_current_user),
):
    _check_rate_limit(current_user.id)
    result = plot_service.generate_plot(expression, x_range=(x_min, x_max))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
