from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import FRONTEND_URL
from app.database import engine, Base
from app.routes import auth, solve, ocr, history, feedback, tts, exam, concept, concept_assistant, pdf
import logging
import os
import warnings

# ── Silence noisy third-party loggers ────────────────────────────────────
warnings.filterwarnings("ignore", message=".*unauthenticated.*HF Hub.*")
warnings.filterwarnings("ignore", message=".*UNEXPECTED.*")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    # --- Startup: load FAISS index so RAG retrieval is ready ---
    from app.services.rag_service import rag_service

    logger.info("Initializing RAG service (FAISS) …")
    rag_service.initialize()
    if rag_service.is_ready():
        logger.info("RAG service is ready.")
    else:
        logger.warning(
            "RAG service NOT ready. Run: python -m app.knowledge_base.seed_data"
        )
    yield
    # --- Shutdown ---
    logger.info("Solvera shutting down.")


app = FastAPI(
    title="Solvera API",
    version="1.0.0",
    description="AI-Powered Intelligent Math Assistant",
    lifespan=lifespan,
)

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
os.makedirs("static/tts", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(solve.router, prefix="/api/solve", tags=["Math Solving"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(tts.router, prefix="/api/tts", tags=["Text-to-Speech"])
app.include_router(exam.router, prefix="/api/exam", tags=["JEE Exam Mode"])
app.include_router(concept.router, prefix="/api/concept-mode", tags=["Concept Learning Mode"])
app.include_router(concept_assistant.router, prefix="/api/concept-assistant", tags=["Concept Assistant"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])


@app.get("/api/health")
def health_check():
    from app.config import USE_OPENAI, OPENAI_MODEL, USE_OLLAMA, OLLAMA_MODEL, USE_GROQ, GEMINI_MODEL
    from app.services.rag_service import rag_service

    info = {
        "status": "ok",
        "service": "solvera",
        "rag_ready": rag_service.is_ready(),
    }

    if USE_OPENAI:
        info["llm_provider"] = "openai"
        info["openai_model"] = OPENAI_MODEL
    elif USE_OLLAMA:
        from app.services.ollama_service import is_ollama_available
        info["llm_provider"] = "ollama"
        info["ollama_model"] = OLLAMA_MODEL
        info["ollama_available"] = is_ollama_available()
    elif USE_GROQ:
        info["llm_provider"] = "groq"
    else:
        info["llm_provider"] = "gemini"
        info["gemini_model"] = GEMINI_MODEL

    return info
