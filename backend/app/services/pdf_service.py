"""PDF extraction and Q&A service.

Extracts text from uploaded PDFs, generates an analysis summary,
and answers follow-up questions using the PDF content + external LLM knowledge.
"""

import logging
import google.generativeai as genai

from app.config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    USE_GROQ,
)

logger = logging.getLogger(__name__)

# ── LLM helpers ─────────────────────────────────────────────────────

def _call_gemini(system: str, user_prompt: str) -> str | None:
    """Call Gemini API and return the text response."""
    if not GOOGLE_API_KEY:
        return None
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=system,
        )
        resp = model.generate_content(user_prompt)
        return resp.text.strip() if resp and resp.text else None
    except Exception as e:
        logger.warning("Gemini call failed in pdf_service: %s", e)
        return None


def _call_groq(system: str, user_prompt: str) -> str | None:
    """Call Groq API and return text response."""
    if not GROQ_API_KEY or not USE_GROQ:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Groq call failed in pdf_service: %s", e)
        return None


def _call_llm(system: str, user_prompt: str) -> str:
    """Try Gemini first, then Groq, then return a fallback."""
    result = _call_gemini(system, user_prompt)
    if result:
        return result
    result = _call_groq(system, user_prompt)
    if result:
        return result
    return "Could not generate a response. Please try again."


# ── PDF text extraction ─────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    import io
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
        raise RuntimeError("PyPDF2 is required for PDF processing. Install it with: pip install PyPDF2")

    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(f"--- Page {i + 1} ---\n{text.strip()}")

    full_text = "\n\n".join(pages_text)
    if not full_text.strip():
        raise ValueError("No readable text found in the PDF. The PDF may be scanned/image-based.")
    return full_text


# ── PDF analysis ────────────────────────────────────────────────────

ANALYSIS_SYSTEM = """You are Solvera, an expert AI math tutor. You have been given the text content extracted from a PDF document.

Your task is to analyze the PDF and provide a structured summary:

1. **Document Type**: What kind of document is it? (textbook chapter, problem set, exam paper, solution manual, notes, etc.)
2. **Topics Covered**: List the main mathematical topics found.
3. **Key Concepts**: Highlight important formulas, theorems, or definitions.
4. **Problems Found**: If there are problems/exercises, list them briefly.
5. **Summary**: A concise overall summary of the document content.

Be concise but informative. Use markdown formatting. If math expressions are present, use LaTeX notation ($...$ for inline, $$...$$ for display)."""


def analyze_pdf(pdf_text: str) -> str:
    """Generate an analysis summary of the extracted PDF text."""
    # Limit text to avoid token limits (~first 8000 chars)
    truncated = pdf_text[:8000]
    if len(pdf_text) > 8000:
        truncated += "\n\n[... document continues ...]"

    prompt = f"Analyze this PDF document:\n\n{truncated}"
    return _call_llm(ANALYSIS_SYSTEM, prompt)


# ── PDF Q&A ─────────────────────────────────────────────────────────

QA_SYSTEM = """You are Solvera, an expert AI math tutor. You have access to content from a PDF document that the user uploaded.

When answering the user's question:
1. **Use the PDF content** as your primary reference when relevant.
2. **Go beyond the PDF** — also use your own mathematical knowledge to provide thorough, step-by-step explanations.
3. **Explain clearly** with steps, formulas (use LaTeX: $...$ inline, $$...$$ display), and examples.
4. If the question is about a specific problem from the PDF, solve it step by step.
5. If the question is conceptual, explain the concept in depth and relate it to the PDF content.
6. Always provide additional insights, tips, or related concepts that help the student learn better.

Be a thorough math tutor — don't just quote the PDF, teach the student."""


def answer_question(pdf_text: str, question: str, chat_history: list[dict] | None = None) -> str:
    """Answer a question using PDF context + LLM knowledge."""
    # Truncate PDF context
    context = pdf_text[:6000]
    if len(pdf_text) > 6000:
        context += "\n\n[... document continues ...]"

    # Build conversation context
    history_text = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:300]
            history_text += f"\n{role}: {content}"

    prompt = f"""PDF Document Content:
{context}

{f"Previous conversation:{history_text}" if history_text else ""}

User's Question: {question}

Please provide a thorough, step-by-step explanation. Use the PDF as reference but also draw from your mathematical expertise."""

    return _call_llm(QA_SYSTEM, prompt)


# Singleton-style module-level functions
pdf_service = type("PDFService", (), {
    "extract_text": staticmethod(extract_text_from_pdf),
    "analyze": staticmethod(analyze_pdf),
    "answer": staticmethod(answer_question),
})()
