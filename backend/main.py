from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import FRONTEND_URL
from app.database import engine, Base
from app.routes import auth, solve, ocr, history, feedback
import os

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Solvera API", version="1.0.0", description="AI-Powered Intelligent Math Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/plots", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(solve.router, prefix="/api/solve", tags=["Math Solving"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "solvera"}
