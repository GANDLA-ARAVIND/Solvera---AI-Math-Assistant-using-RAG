import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.history import SolveHistory
from app.services.ocr_service import ocr_service
from app.services.solver_service import solver_service
from app.services.auth_service import get_current_user

router = APIRouter()


@router.post("/extract")
async def extract_from_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Extract math from an uploaded image without solving."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    result = await ocr_service.extract_math_from_image(image_bytes, file.filename)
    return result


@router.post("/solve")
async def extract_and_solve(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extract math from image AND solve it in one step."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    # Step 1: Extract
    extraction = await ocr_service.extract_math_from_image(image_bytes, file.filename)
    if not extraction["success"]:
        return {"extraction": extraction, "solution": None}

    # Step 2: Solve the extracted text
    solution = await solver_service.solve(
        extraction["extracted_text"], user_id=current_user.id
    )

    # Step 3: Save to history with image reference
    if solution.get("success"):
        validation = solution.get("validation", {})
        match_val = validation.get("match")
        sympy_flag = 1 if match_val is True else (-1 if match_val is False else 0)

        history_entry = SolveHistory(
            user_id=current_user.id,
            query_text=extraction["extracted_text"],
            query_image_path=extraction.get("image_path"),
            topic=solution.get("topic"),
            solution_text=solution["solution"],
            sympy_verified=sympy_flag,
            rag_sources_used=json.dumps(solution.get("rag_sources", [])),
        )
        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)
        solution["history_id"] = history_entry.id

    return {"extraction": extraction, "solution": solution}
