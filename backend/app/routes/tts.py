"""
TTS route — POST /api/tts/explain

Accepts a solution text and returns an audio URL for neural TTS playback.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.tts_service import generate_voice, cleanup_old_audio

router = APIRouter()


class TTSRequest(BaseModel):
    solution: str
    question: str | None = None


class TTSResponse(BaseModel):
    success: bool
    audio_url: str | None = None
    steps: list[dict] = []
    voice: str | None = None
    total_steps: int = 0
    error: str | None = None
    fallback_to_browser: bool = False


@router.post("/explain", response_model=TTSResponse)
async def explain_in_voice(req: TTSRequest):
    """Generate neural TTS audio for a math solution."""
    if not req.solution or not req.solution.strip():
        raise HTTPException(status_code=400, detail="Solution text is required")

    # Clean up old audio files (older than 1 hour)
    cleanup_old_audio(max_age_seconds=3600)

    result = await generate_voice(req.solution, question=req.question)
    return TTSResponse(**result)
