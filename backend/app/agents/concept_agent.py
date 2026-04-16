"""Concept Learning Agent — orchestrates RAG, SymPy, Gemini and plot_service.

This agent is the central entry point for all concept-learning operations.
It provides two high-level capabilities:

1. **Topic-based learning** (``learn_topic``)
   Given a math topic, returns a complete learning bundle:
   concept definition, formula, solved example, graph (if applicable),
   and a practice question — all in structured JSON.

2. **Concept assistant** (``ask_assistant``)
   A free-form chat tutor that answers any math concept question.
   Uses RAG retrieval + Gemini to generate structured answers.
"""

import json
import logging
import re
import time
import uuid

import google.generativeai as genai

from app.config import (
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    OPENAI_API_KEY,
    USE_OPENAI,
    OPENAI_MODEL,
    USE_OLLAMA,
)
from app.services.rag_service import rag_service
from app.services.plot_service import plot_service

logger = logging.getLogger(__name__)

# ── In-memory practice session store ────────────────────────────────────
_practice_sessions: dict[str, dict] = {}

# ── Topic → sample expression for plotting ─────────────────────────────
_GRAPH_EXPRESSIONS: dict[str, str] = {
    "algebra": "x**2 - 4*x + 3",
    "quadratic_equations": "x**2 - 4*x + 3",
    "polynomials": "x**3 - 3*x**2 + 2*x",
    "linear_equations": "2*x + 1",
    "integration": "x**2",
    "definite_integrals": "x**2",
    "derivatives": "x**3 - 3*x",
    "differentiation": "x**3 - 3*x",
    "calculus": "x**3 - 3*x",
    "limits": "sin(x)/x",
    "trigonometry": "sin(x)",
    "trigonometric_functions": "sin(x)",
    "functions": "x**2 - 2*x + 1",
    "sequences": None,
    "matrices": None,
    "probability": None,
}


# ═══════════════════════════════════════════════════════════════════════════
#  LLM cascade (Gemini → Groq → OpenAI → Ollama)
# ═══════════════════════════════════════════════════════════════════════════

def _call_llm(prompt: str, system: str = "") -> str | None:
    """Try providers in cascade order. Returns text or None."""

    # 1. Gemini
    if GOOGLE_API_KEY:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                GEMINI_MODEL,
                system_instruction=system or None,
            )
            resp = model.generate_content(
                prompt,
                safety_settings=[
                    {"category": c, "threshold": "BLOCK_NONE"}
                    for c in [
                        "HARM_CATEGORY_HARASSMENT",
                        "HARM_CATEGORY_HATE_SPEECH",
                        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "HARM_CATEGORY_DANGEROUS_CONTENT",
                    ]
                ],
            )
            if resp.text:
                return resp.text.strip()
        except Exception as e:
            logger.info("Concept-agent Gemini fallback: %s", type(e).__name__)

    # 2. Groq
    if GROQ_API_KEY:
        try:
            from groq import Groq

            client = Groq(api_key=GROQ_API_KEY)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            text = resp.choices[0].message.content
            if text:
                return text.strip()
        except Exception as e:
            logger.info("Concept-agent Groq fallback: %s", type(e).__name__)

    # 3. OpenAI
    if OPENAI_API_KEY and USE_OPENAI:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=OPENAI_API_KEY)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            text = resp.choices[0].message.content
            if text:
                return text.strip()
        except Exception as e:
            logger.info("Concept-agent OpenAI fallback: %s", type(e).__name__)

    # 4. Ollama
    if USE_OLLAMA:
        try:
            from app.services.ollama_service import generate_response

            text = generate_response(prompt)
            if text:
                return text.strip()
        except Exception as e:
            logger.info("Concept-agent Ollama fallback: %s", type(e).__name__)

    return None


def _pretty(s: str) -> str:
    return s.replace("_", " ").title()


# ═══════════════════════════════════════════════════════════════════════════
#  RAG context helper
# ═══════════════════════════════════════════════════════════════════════════

def _get_rag_context(query: str, topic: str | None = None) -> str:
    """Retrieve RAG context for a topic/query. Returns formatted string."""
    if not rag_service.is_ready():
        logger.debug("RAG not ready — skipping retrieval for concept agent")
        return ""
    docs = rag_service.retrieve_top3(query, topic_filter=topic)
    context = rag_service.format_context(docs)
    logger.info("[concept-agent] RAG retrieved %d docs for query='%s'", len(docs), query[:80])
    return context


# ═══════════════════════════════════════════════════════════════════════════
#  SymPy helper — generate a solved example
# ═══════════════════════════════════════════════════════════════════════════

def _sympy_example(topic: str) -> str | None:
    """Generate a quick SymPy-solved example for the given topic."""
    try:
        from sympy import symbols, solve, diff, integrate, limit, simplify, sin, cos, oo, pi
        from sympy import latex

        x = symbols("x")

        examples: dict[str, tuple] = {
            "algebra": (
                "Solve $x^2 - 5x + 6 = 0$",
                lambda: solve(x**2 - 5*x + 6, x),
            ),
            "quadratic_equations": (
                "Solve $x^2 - 5x + 6 = 0$",
                lambda: solve(x**2 - 5*x + 6, x),
            ),
            "linear_equations": (
                "Solve $3x + 7 = 22$",
                lambda: solve(3*x + 7 - 22, x),
            ),
            "polynomials": (
                "Find roots of $x^3 - 6x^2 + 11x - 6 = 0$",
                lambda: solve(x**3 - 6*x**2 + 11*x - 6, x),
            ),
            "derivatives": (
                "Differentiate $x^3 - 3x^2 + 2x$",
                lambda: diff(x**3 - 3*x**2 + 2*x, x),
            ),
            "differentiation": (
                "Differentiate $x^3 - 3x^2 + 2x$",
                lambda: diff(x**3 - 3*x**2 + 2*x, x),
            ),
            "calculus": (
                "Differentiate $x^4 - 2x^2$",
                lambda: diff(x**4 - 2*x**2, x),
            ),
            "integration": (
                "Integrate $\\int 2x\\ dx$",
                lambda: integrate(2*x, x),
            ),
            "definite_integrals": (
                "Evaluate $\\int_0^1 x^2\\ dx$",
                lambda: integrate(x**2, (x, 0, 1)),
            ),
            "limits": (
                "Evaluate $\\lim_{x \\to 0} \\frac{\\sin x}{x}$",
                lambda: limit(sin(x) / x, x, 0),
            ),
            "trigonometry": (
                "Simplify $\\sin^2 x + \\cos^2 x$",
                lambda: simplify(sin(x)**2 + cos(x)**2),
            ),
            "trigonometric_functions": (
                "Simplify $\\sin^2 x + \\cos^2 x$",
                lambda: simplify(sin(x)**2 + cos(x)**2),
            ),
        }

        entry = examples.get(topic)
        if not entry:
            return None

        problem, solver = entry
        result = solver()
        result_latex = latex(result)
        return f"**SymPy Verified Example:**\n\n{problem}\n\n**Answer:** $${result_latex}$$"

    except Exception as e:
        logger.debug("SymPy example generation failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Graph helper
# ═══════════════════════════════════════════════════════════════════════════

def _generate_graph(topic: str) -> str | None:
    """Generate a plot for the topic if applicable. Returns URL or None."""
    expr = _GRAPH_EXPRESSIONS.get(topic)
    if not expr:
        return None
    result = plot_service.generate_plot(expr, title=f"{_pretty(topic)} — Visualization")
    if result.get("success"):
        logger.info("[concept-agent] Graph generated for topic='%s'", topic)
        return result["plot_url"]
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE 1: learn_topic — single-call structured learning bundle
# ═══════════════════════════════════════════════════════════════════════════

LEARN_SYSTEM = (
    "You are an expert mathematics tutor helping students learn concepts.\n\n"
    "Rules:\n"
    "- Always respond in structured sections with clear headings.\n"
    "- Never give long paragraphs. Keep sentences short.\n"
    "- Use numbered steps for explanations and solutions.\n"
    "- Make explanations simple and beginner-friendly.\n"
    "- Highlight formulas clearly using LaTeX ($ inline, $$ display).\n"
    "- Provide worked examples with step-by-step solutions.\n"
    "- Suitable for JEE / competitive exam preparation."
)

def learn_topic(topic: str) -> dict:
    """Return a complete learning bundle for the given topic.

    Returns dict with keys: concept, formula, example, graph, practice_question.
    """
    logger.info("[concept-agent] === learn_topic START === topic='%s'", topic)

    # 1. RAG retrieval
    rag_context = _get_rag_context(f"Explain {_pretty(topic)} concept definition formula example", topic)
    logger.info("[concept-agent] RAG context length: %d chars", len(rag_context))

    # 2. Build prompt with RAG context
    rag_section = ""
    if rag_context:
        rag_section = f"\n\nUse the following reference material:\n{rag_context}\n"

    prompt = f"""Explain the mathematical concept of **{_pretty(topic)}**.{rag_section}

You MUST respond in EXACTLY this JSON format (no markdown fences, no extra text):
{{
    "concept": "A clear definition and explanation of the concept (2-3 paragraphs with LaTeX math)",
    "formula": "The main formula(s) with LaTeX notation, each on its own line. Example: $$ax^2 + bx + c = 0$$ where a, b, c are coefficients",
    "example": "A fully solved example with step-by-step solution using LaTeX",
    "practice_question": "A practice question for the student to try (state the question clearly)"
}}

Rules:
- Use LaTeX: $ for inline math, $$ for display math
- The example must show every step clearly
- The practice question must be solvable and well-defined
- Keep explanations student-friendly
"""

    text = _call_llm(prompt, LEARN_SYSTEM)

    # 3. Parse LLM response
    result = {
        "concept": "",
        "formula": "",
        "example": "",
        "graph": None,
        "practice_question": "",
    }

    if text:
        try:
            raw = text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            result["concept"] = data.get("concept", "")
            result["formula"] = data.get("formula", "")
            result["example"] = data.get("example", "")
            result["practice_question"] = data.get("practice_question", "")
            logger.info("[concept-agent] LLM JSON parsed successfully")
        except (json.JSONDecodeError, Exception) as e:
            logger.info("[concept-agent] LLM returned non-JSON — using raw text")
            result["concept"] = text

    # 4. SymPy verified example (supplement LLM example)
    sympy_ex = _sympy_example(topic)
    if sympy_ex:
        result["example"] = result["example"] + "\n\n---\n\n" + sympy_ex if result["example"] else sympy_ex
        logger.info("[concept-agent] SymPy example appended")

    # 5. Graph visualization
    graph_url = _generate_graph(topic)
    if graph_url:
        result["graph"] = graph_url
        logger.info("[concept-agent] Graph URL: %s", graph_url)

    logger.info("[concept-agent] === learn_topic END === topic='%s'", topic)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE 2: ask_assistant — free-form concept Q&A
# ═══════════════════════════════════════════════════════════════════════════

ASSISTANT_SYSTEM = (
    "You are an expert mathematics tutor helping students learn concepts.\n\n"
    "Rules:\n"
    "- Always respond in structured sections.\n"
    "- Never give long paragraphs.\n"
    "- Use numbered steps.\n"
    "- Use short sentences.\n"
    "- Make explanations simple and beginner-friendly.\n"
    "- Highlight formulas clearly using LaTeX ($ inline, $$ display).\n"
    "- Provide one worked example.\n\n"
    "Format every response EXACTLY as:\n\n"
    "Concept:\n(Short, clear explanation of the concept in 2-3 sentences)\n\n"
    "Formula:\n(The main formula using $$ display math)\n\n"
    "Step-by-Step Explanation:\n"
    "1. (First key idea — one sentence)\n"
    "2. (Second key idea — one sentence)\n"
    "3. (Third key idea — one sentence)\n\n"
    "Example:\nProblem: (state the problem)\n"
    "Steps:\n1. (first step with math)\n2. (second step with math)\n"
    "Final Answer: (the answer)\n\n"
    "Key Takeaway:\n(Summarize the important idea in 1-2 lines)"
)


def _format_structured_response(raw_text: str) -> dict:
    """Parse raw LLM text into structured sections.

    Looks for section headers (Concept:, Formula:, Step-by-Step Explanation:,
    Example:, Key Takeaway:) and splits accordingly.  Falls back to putting
    everything in 'answer' if no headings are found.
    """
    sections = {
        "answer": "",
        "formula": "",
        "example": "",
        "steps": "",
        "key_takeaway": "",
    }

    # Normalise common heading variations
    text = raw_text.strip()
    text = re.sub(r"\*\*Concept:?\*\*", "Concept:", text)
    text = re.sub(r"\*\*Formula:?\*\*", "Formula:", text)
    text = re.sub(r"\*\*Step-by-Step Explanation:?\*\*", "Step-by-Step Explanation:", text)
    text = re.sub(r"\*\*Example:?\*\*", "Example:", text)
    text = re.sub(r"\*\*Key Takeaway:?\*\*", "Key Takeaway:", text)
    text = re.sub(r"#+\s*Concept:?", "Concept:", text)
    text = re.sub(r"#+\s*Formula:?", "Formula:", text)
    text = re.sub(r"#+\s*Step-by-Step Explanation:?", "Step-by-Step Explanation:", text)
    text = re.sub(r"#+\s*Example:?", "Example:", text)
    text = re.sub(r"#+\s*Key Takeaway:?", "Key Takeaway:", text)

    # Define section patterns (order matters — first match wins)
    patterns = [
        ("Concept:", "answer"),
        ("Formula:", "formula"),
        ("Step-by-Step Explanation:", "steps"),
        ("Example:", "example"),
        ("Key Takeaway:", "key_takeaway"),
    ]

    # Locate header positions
    positions = []
    for header, key in patterns:
        idx = text.find(header)
        if idx != -1:
            positions.append((idx, len(header), key))

    if not positions:
        # No structured headers found — return everything as answer
        sections["answer"] = _clean_section(text)
        return sections

    positions.sort(key=lambda p: p[0])

    for i, (start, hlen, key) in enumerate(positions):
        content_start = start + hlen
        content_end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections[key] = _clean_section(text[content_start:content_end])

    # If there's text before the first heading, prepend it to answer
    first_pos = positions[0][0]
    if first_pos > 0:
        preamble = _clean_section(text[:first_pos])
        if preamble:
            sections["answer"] = preamble + ("\n\n" + sections["answer"] if sections["answer"] else "")

    return sections


def _clean_section(text: str) -> str:
    """Strip leading/trailing whitespace and remove excessive blank lines."""
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def ask_assistant(question: str) -> dict:
    """Answer a free-form math concept question using RAG + Gemini.

    Returns dict with keys: answer, formula, example, steps, key_takeaway.
    """
    logger.info("[concept-assistant] === ask START === q='%s'", question[:100])

    # 1. RAG retrieval
    rag_context = _get_rag_context(question)
    logger.info("[concept-assistant] RAG context length: %d chars", len(rag_context))

    # 2. Build prompt
    rag_section = ""
    if rag_context:
        rag_section = f"\n\nUse the following reference material:\n{rag_context}\n"

    prompt = f"""Student question: {question}{rag_section}

Respond using EXACTLY this format (keep each section short and clear):

Concept:
(Short, clear explanation of the concept in 2-3 sentences. No long paragraphs.)

Formula:
(The main formula using $$ display math. Explain each variable briefly.)

Step-by-Step Explanation:
1. (First key idea — one sentence)
2. (Second key idea — one sentence)
3. (Third key idea — one sentence)

Example:
Problem: (state a simple problem)
Steps:
1. (first step with math)
2. (second step with math)
Final Answer: (the answer)

Key Takeaway:
(Summarize the important idea in 1-2 lines)

Rules:
- Answer the exact question asked
- Use LaTeX: $ for inline, $$ for display math
- Keep every section short — no long paragraphs
- Use numbered steps everywhere
- Be beginner-friendly
"""

    text = _call_llm(prompt, ASSISTANT_SYSTEM)

    result = {
        "answer": "",
        "formula": "",
        "example": "",
        "steps": "",
        "key_takeaway": "",
    }

    if text:
        # First try JSON parse (in case LLM returns JSON despite instructions)
        try:
            raw = text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            result["answer"] = data.get("answer", data.get("concept", ""))
            result["formula"] = data.get("formula", "")
            result["example"] = data.get("example", "")
            result["steps"] = data.get("steps", data.get("step_by_step", ""))
            result["key_takeaway"] = data.get("key_takeaway", data.get("additional_notes", ""))
            logger.info("[concept-assistant] LLM JSON parsed successfully")
        except (json.JSONDecodeError, ValueError):
            # Expected path — parse structured text
            result = _format_structured_response(text)
            logger.info("[concept-assistant] Structured text parsed into sections")

    logger.info("[concept-assistant] === ask END === q='%s'", question[:100])
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE 4: Practice question evaluation
# ═══════════════════════════════════════════════════════════════════════════

def generate_practice(topic: str) -> dict:
    """Generate a practice question for the given topic with stored correct answer."""
    logger.info("[concept-agent] Generating practice question for topic='%s'", topic)

    rag_context = _get_rag_context(f"Practice question for {_pretty(topic)}", topic)

    rag_section = ""
    if rag_context:
        rag_section = f"\n\nReference material:\n{rag_context}\n"

    prompt = f"""Generate ONE practice question for **{_pretty(topic)}**.{rag_section}

You MUST respond in EXACTLY this JSON format (no markdown, no code fences):
{{
    "question": "The question text with LaTeX math notation",
    "correct_answer": "The numeric or symbolic answer (e.g. 42 or 3*x**2)",
    "answer_type": "numeric or expression",
    "hint": "A helpful hint without giving away the answer",
    "solution_steps": "Step 1: ...\\nStep 2: ...\\nFinal Answer: ..."
}}

Rules:
- Make it appropriate for JEE / competitive exams
- correct_answer must be a valid number or SymPy expression
- The question must be solvable in 2-5 steps
"""

    text = _call_llm(prompt, LEARN_SYSTEM)

    if not text:
        return {"session_id": None, "question": "Practice question unavailable. Try again.", "hint": None}

    try:
        raw = text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return {"session_id": None, "question": text, "hint": None}

    # Store session
    session_id = uuid.uuid4().hex
    _practice_sessions[session_id] = {
        "topic": topic,
        "question": data.get("question", text),
        "correct_answer": data.get("correct_answer", ""),
        "answer_type": data.get("answer_type", "numeric"),
        "solution_steps": data.get("solution_steps", ""),
        "hint": data.get("hint", ""),
        "created_at": time.time(),
        "answered": False,
    }

    logger.info("[concept-agent] Practice session created: %s", session_id)

    return {
        "session_id": session_id,
        "question": data.get("question", text),
        "hint": data.get("hint"),
    }


def evaluate_practice(session_id: str, user_answer: str) -> dict:
    """Evaluate a user's practice answer using SymPy equivalence check.

    Uses: ``simplify(user_answer - correct_answer) == 0``
    """
    session = _practice_sessions.get(session_id)
    if not session:
        raise ValueError("Practice session not found.")

    if session["answered"]:
        return {
            "result": "already_answered",
            "correct_answer": session["correct_answer"],
            "explanation": session["solution_steps"],
        }

    # SymPy evaluation
    from app.services.exam_service import evaluate_answer

    is_correct = evaluate_answer(
        user_answer,
        session["correct_answer"],
        session.get("answer_type", "numeric"),
    )

    session["answered"] = True

    logger.info(
        "[concept-agent] Practice eval: session=%s correct=%s user='%s' expected='%s'",
        session_id, is_correct, user_answer, session["correct_answer"],
    )

    if is_correct:
        return {
            "result": "correct",
            "correct_answer": session["correct_answer"],
            "explanation": session["solution_steps"],
        }

    # Generate feedback for incorrect answer
    feedback = _call_llm(
        f"Student answered '{user_answer}' but correct answer is '{session['correct_answer']}' "
        f"for the question: {session['question']}. "
        f"Explain briefly what went wrong and show the correct approach. Use LaTeX.",
        LEARN_SYSTEM,
    ) or session["solution_steps"]

    return {
        "result": "incorrect",
        "correct_answer": session["correct_answer"],
        "explanation": feedback,
    }
