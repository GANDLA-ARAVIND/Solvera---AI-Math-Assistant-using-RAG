import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
USE_GROQ = os.getenv("USE_GROQ", "false").lower() == "true"

# OpenAI (GPT-4) ---------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Ollama (free, local LLM) -----------------------------------------------
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# LLM provider priority: GEMINI > GROQ > OPENAI > OLLAMA (SymPy as last resort)
# Gemini is used first for step-by-step solutions. Set API keys to enable providers.

OCR_MODEL = os.getenv("OCR_MODEL", "models/gemini-3-pro-image-preview")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24  # 24 hours
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./solvera.db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "./faiss_index")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
