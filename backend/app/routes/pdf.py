"""PDF upload, analysis, and Q&A routes."""

import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.pdf_service import pdf_service

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for PDF text per user (lightweight session)
_pdf_sessions: dict[int, str] = {}

MAX_PDF_SIZE = 20 * 1024 * 1024  # 20 MB


class PDFQuestionRequest(BaseModel):
    question: str
    conversation_history: Optional[list[dict]] = None


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF, extract text, analyze it, and return the analysis."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(status_code=400, detail="PDF too large. Maximum size is 20MB.")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

    try:
        # Extract text
        pdf_text = pdf_service.extract_text(content)
        logger.info("PDF uploaded by user %s: %d chars extracted from '%s'",
                     current_user.id, len(pdf_text), file.filename)

        # Store PDF context for this user
        _pdf_sessions[current_user.id] = pdf_text

        # Generate analysis
        analysis = pdf_service.analyze(pdf_text)

        page_count = pdf_text.count("--- Page ")

        return {
            "success": True,
            "filename": file.filename,
            "pages": page_count,
            "text_length": len(pdf_text),
            "analysis": analysis,
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("PDF processing failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to process the PDF. Please try again.")


@router.post("/ask")
async def ask_pdf_question(
    request: PDFQuestionRequest,
    current_user: User = Depends(get_current_user),
):
    """Ask a question about the uploaded PDF."""
    pdf_text = _pdf_sessions.get(current_user.id)
    if not pdf_text:
        raise HTTPException(
            status_code=400,
            detail="No PDF uploaded. Please upload a PDF first.",
        )

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        answer = pdf_service.answer(
            pdf_text,
            request.question.strip(),
            request.conversation_history,
        )
        return {
            "success": True,
            "answer": answer,
        }
    except Exception as e:
        logger.error("PDF Q&A failed: %s", e)
        return {
            "success": False,
            "message": "Failed to answer the question. Please try again.",
        }


@router.delete("/clear")
async def clear_pdf_session(
    current_user: User = Depends(get_current_user),
):
    """Clear the current PDF session for the user."""
    _pdf_sessions.pop(current_user.id, None)
    return {"success": True, "message": "PDF session cleared."}
