"""Concept Learning Mode — interactive concept teaching service.

Functions:
    - get_concept_explanation(topic, subtopic) → structured explanation with RAG
    - get_formula(topic, subtopic) → key formulas with LaTeX + RAG
    - generate_example(topic, subtopic) → worked example with SymPy verification + graph
    - generate_practice_question(topic, subtopic) → practice Q
    - evaluate_user_answer(session_id, answer) → SymPy equivalence check + feedback

Uses RAG retrieval, SymPy verification, Gemini → Groq → OpenAI → Ollama cascade.
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
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
)
from app.services.plot_service import plot_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

# ── In-memory session store ─────────────────────────────────────────────
_sessions: dict[str, dict] = {}

# ── Supported topics and subtopics ──────────────────────────────────────
SUPPORTED_TOPICS = {
    "algebra": [
        "linear_equations", "quadratic_equations", "polynomials",
        "inequalities", "sequences_and_series", "matrices_and_determinants",
        "complex_numbers", "binomial_theorem", "partial_fractions",
    ],
    "calculus": [
        "limits", "continuity", "differentiation", "integration",
        "differential_equations", "application_of_derivatives",
        "definite_integrals", "area_under_curves",
    ],
    "trigonometry": [
        "trigonometric_functions", "trigonometric_identities",
        "trigonometric_equations", "inverse_trigonometry",
        "properties_of_triangles", "heights_and_distances",
    ],
    "geometry": [
        "straight_lines", "circles", "conic_sections",
        "coordinate_geometry", "3d_geometry", "vectors",
    ],
    "statistics": [
        "mean_median_mode", "probability", "distributions",
        "permutations_and_combinations", "mathematical_reasoning",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
#  LLM cascade helper (same pattern as solver_service)
# ═══════════════════════════════════════════════════════════════════════════

def _call_llm(prompt: str, system: str = "") -> str | None:
    """Try Gemini → Groq → OpenAI → Ollama. Returns text or None."""

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
            logger.info("Concept agent Gemini fallback: %s", type(e).__name__)

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
            logger.info("Concept agent Groq fallback: %s", type(e).__name__)

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
            logger.info("Concept agent OpenAI fallback: %s", type(e).__name__)

    # 4. Ollama
    if USE_OLLAMA:
        try:
            from app.services.ollama_service import generate_response
            text = generate_response(prompt)
            if text:
                return text.strip()
        except Exception as e:
            logger.info("Concept agent Ollama fallback: %s", type(e).__name__)

    return None


def _pretty(topic: str) -> str:
    return topic.replace("_", " ").title()


# ═══════════════════════════════════════════════════════════════════════════
#  RAG context helper
# ═══════════════════════════════════════════════════════════════════════════

def _get_rag_context(query: str, topic: str | None = None) -> str:
    """Retrieve RAG context for a topic/query. Returns formatted string."""
    if not rag_service.is_ready():
        return ""
    docs = rag_service.retrieve_top3(query, topic_filter=topic)
    context = rag_service.format_context(docs)
    logger.info("[concept-service] RAG retrieved %d docs for '%s'", len(docs), query[:60])
    return context


def _rag_section(query: str, topic: str | None = None) -> str:
    """Build a RAG context block to inject into prompts."""
    ctx = _get_rag_context(query, topic)
    if ctx:
        return f"\n\nUse the following reference material from the knowledge base:\n{ctx}\n"
    return ""


# ═══════════════════════════════════════════════════════════════════════════
#  SymPy example helper
# ═══════════════════════════════════════════════════════════════════════════

def _sympy_verify_example(subtopic: str) -> str | None:
    """Generate a SymPy-verified mini example for the subtopic."""
    try:
        from sympy import symbols, solve, diff, integrate, limit, simplify, sin, cos, latex

        x = symbols("x")

        examples: dict[str, tuple] = {
            "linear_equations": ("Solve $3x + 7 = 22$", lambda: solve(3*x + 7 - 22, x)),
            "quadratic_equations": ("Solve $x^2 - 5x + 6 = 0$", lambda: solve(x**2 - 5*x + 6, x)),
            "polynomials": ("Find roots of $x^3 - 6x^2 + 11x - 6 = 0$", lambda: solve(x**3 - 6*x**2 + 11*x - 6, x)),
            "differentiation": ("Differentiate $x^3 - 3x^2 + 2x$", lambda: diff(x**3 - 3*x**2 + 2*x, x)),
            "integration": ("Integrate $\\int 2x\\ dx$", lambda: integrate(2*x, x)),
            "definite_integrals": ("Evaluate $\\int_0^1 x^2\\ dx$", lambda: integrate(x**2, (x, 0, 1))),
            "limits": ("$\\lim_{x \\to 0} \\frac{\\sin x}{x}$", lambda: limit(sin(x) / x, x, 0)),
            "trigonometric_functions": ("Simplify $\\sin^2 x + \\cos^2 x$", lambda: simplify(sin(x)**2 + cos(x)**2)),
            "trigonometric_identities": ("Simplify $\\sin^2 x + \\cos^2 x$", lambda: simplify(sin(x)**2 + cos(x)**2)),
            "application_of_derivatives": ("Find critical points of $x^3 - 3x$", lambda: solve(diff(x**3 - 3*x, x), x)),
            "area_under_curves": ("Area under $y = x^2$ from 0 to 1", lambda: integrate(x**2, (x, 0, 1))),
        }

        entry = examples.get(subtopic)
        if not entry:
            return None

        problem, solver = entry
        result = solver()
        result_latex = latex(result)
        return f"**SymPy Verified:** {problem} → $${result_latex}$$"

    except Exception as e:
        logger.debug("SymPy verify failed for %s: %s", subtopic, e)
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Core functions (with RAG + SymPy + logging)
# ═══════════════════════════════════════════════════════════════════════════

CONCEPT_SYSTEM = (
    "You are an expert mathematics tutor helping students learn concepts.\n\n"
    "Rules:\n"
    "- Always respond in structured sections with clear headings.\n"
    "- Never give long paragraphs. Keep sentences short.\n"
    "- Use numbered steps for explanations and solutions.\n"
    "- Make explanations simple and beginner-friendly.\n"
    "- Highlight formulas clearly using LaTeX ($ inline, $$ display).\n"
    "- Provide worked examples with step-by-step solutions.\n"
    "- Suitable for JEE / competitive exam preparation.\n\n"
    "Always include these sections where applicable:\n"
    "1. Concept — Short definition\n"
    "2. Formula — Key formula(s) with LaTeX\n"
    "3. Step-by-Step Explanation — Numbered steps\n"
    "4. Worked Example — Problem → Steps → Final Answer\n"
    "5. Key Takeaway — 1-2 line summary"
)


def get_concept_explanation(topic: str, subtopic: str) -> dict:
    """Return a structured explanation of a concept using RAG + LLM."""
    logger.info("[concept-service] explain: topic=%s subtopic=%s", topic, subtopic)

    rag = _rag_section(f"{_pretty(subtopic)} definition concept properties", topic)

    prompt = f"""Explain the concept of **{_pretty(subtopic)}** in **{_pretty(topic)}**.{rag}

Structure your response EXACTLY like this:

## Definition
(A clear, concise definition)

## Key Points
- Point 1
- Point 2
- Point 3

## Intuition
(An intuitive explanation — why does this concept matter and how to think about it)

## Important Properties
- Property 1
- Property 2

## Common Mistakes
- Mistake 1 and how to avoid it
- Mistake 2 and how to avoid it

Use LaTeX notation for all mathematical expressions (e.g., $ax^2 + bx + c = 0$).
"""
    text = _call_llm(prompt, CONCEPT_SYSTEM)
    if not text:
        text = f"## {_pretty(subtopic)}\n\nConcept explanation is currently unavailable. Please try again."

    logger.info("[concept-service] explain generated: %d chars", len(text))
    return {"topic": topic, "subtopic": subtopic, "explanation": text}


def get_formula(topic: str, subtopic: str) -> dict:
    """Return key formulas for a subtopic using RAG + LLM."""
    logger.info("[concept-service] formula: topic=%s subtopic=%s", topic, subtopic)

    rag = _rag_section(f"{_pretty(subtopic)} formulas equations", topic)

    prompt = f"""List ALL important formulas for **{_pretty(subtopic)}** in **{_pretty(topic)}**.{rag}

Structure your response EXACTLY like this:

## Key Formulas — {_pretty(subtopic)}

### Formula 1: (Name)
$$formula$$
Where: (explain each variable)

### Formula 2: (Name)
$$formula$$
Where: (explain each variable)

(Continue for all important formulas)

## Quick Reference Table
| Formula | When to Use |
|---------|------------|
| $formula$ | condition |

Use LaTeX for all math. Be comprehensive — include all JEE-relevant formulas.
"""
    text = _call_llm(prompt, CONCEPT_SYSTEM)
    if not text:
        text = f"## Formulas — {_pretty(subtopic)}\n\nFormula listing is currently unavailable. Please try again."

    logger.info("[concept-service] formula generated: %d chars", len(text))
    return {"topic": topic, "subtopic": subtopic, "formulas": text}


def generate_example(topic: str, subtopic: str) -> dict:
    """Generate a worked example using RAG + LLM + SymPy verification + graph."""
    logger.info("[concept-service] example: topic=%s subtopic=%s", topic, subtopic)

    rag = _rag_section(f"{_pretty(subtopic)} solved example step by step", topic)

    prompt = f"""Create a worked example for **{_pretty(subtopic)}** in **{_pretty(topic)}**.{rag}

Structure your response EXACTLY like this:

## Worked Example

**Problem:** (State the problem clearly)

### Step-by-Step Solution

**Step 1:** (Description)
$$math$$

**Step 2:** (Description)
$$math$$

(Continue with all steps)

### Final Answer
$$answer$$

### Key Takeaway
(What principle does this example illustrate?)

Use LaTeX for all math. Make it JEE-level difficulty.
"""
    text = _call_llm(prompt, CONCEPT_SYSTEM)
    if not text:
        text = f"## Example — {_pretty(subtopic)}\n\nExample generation is currently unavailable. Please try again."

    # SymPy verification — append a verified mini-example
    sympy_ex = _sympy_verify_example(subtopic)
    if sympy_ex:
        text = text + "\n\n---\n\n" + sympy_ex
        logger.info("[concept-service] SymPy verified example appended for %s", subtopic)

    # Try to generate a related plot if it's a graphable concept
    plot_url = None
    graphable = ["quadratic_equations", "polynomials", "straight_lines", "circles",
                 "conic_sections", "trigonometric_functions", "limits",
                 "differentiation", "integration", "area_under_curves"]
    if subtopic in graphable:
        plot_url = _try_generate_concept_plot(topic, subtopic)

    result = {"topic": topic, "subtopic": subtopic, "example": text}
    if plot_url:
        result["plot_url"] = plot_url
        logger.info("[concept-service] Graph generated for %s", subtopic)

    logger.info("[concept-service] example generated: %d chars", len(text))
    return result


def _try_generate_concept_plot(topic: str, subtopic: str) -> str | None:
    """Try to generate a relevant plot for the concept."""
    expression_map = {
        "quadratic_equations": "x**2 - 4*x + 3",
        "polynomials": "x**3 - 3*x**2 + 2*x",
        "straight_lines": "2*x + 1",
        "circles": None,  # Not easily plottable as y=f(x)
        "conic_sections": None,
        "trigonometric_functions": "sin(x)",
        "limits": "sin(x)/x",
        "differentiation": "x**3 - 3*x",
        "integration": "x**2",
        "area_under_curves": "x**2",
    }
    expr = expression_map.get(subtopic)
    if not expr:
        return None
    result = plot_service.generate_plot(expr, title=f"{_pretty(subtopic)} — Example Graph")
    if result.get("success"):
        return result["plot_url"]
    return None


def generate_practice_question(topic: str, subtopic: str) -> dict:
    """Generate a practice question using RAG + LLM and store answer in session."""
    logger.info("[concept-service] practice: topic=%s subtopic=%s", topic, subtopic)

    rag = _rag_section(f"{_pretty(subtopic)} practice problem", topic)

    prompt = f"""Generate ONE practice question for **{_pretty(subtopic)}** in **{_pretty(topic)}**.{rag}

You MUST respond in EXACTLY this JSON format (no markdown, no code fences):
{{
    "question": "The question text with LaTeX math notation",
    "correct_answer": "The numeric or symbolic answer (e.g. 42 or 3*x**2)",
    "answer_type": "numeric or expression",
    "hint": "A helpful hint without giving away the answer",
    "difficulty": "medium",
    "solution_steps": "Step 1: ...\\nStep 2: ...\\nStep 3: ...\\nFinal Answer: ..."
}}

Rules:
- Make it JEE-level appropriate
- The question must be solvable in 2-5 steps
- correct_answer must be a valid number or SymPy expression
- solution_steps should be a full step-by-step solution
"""
    text = _call_llm(prompt, CONCEPT_SYSTEM)
    if not text:
        return {
            "session_id": None,
            "question": "Practice question generation is currently unavailable. Please try again.",
            "hint": None,
            "topic": topic,
            "subtopic": subtopic,
        }

    # Parse LLM JSON response
    try:
        raw = text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        # Fallback: treat the entire response as the question
        return {
            "session_id": None,
            "question": text,
            "hint": None,
            "topic": topic,
            "subtopic": subtopic,
        }

    # Create a session to track this practice question
    session_id = uuid.uuid4().hex
    _sessions[session_id] = {
        "session_id": session_id,
        "topic": topic,
        "subtopic": subtopic,
        "question": data.get("question", text),
        "correct_answer": data.get("correct_answer", ""),
        "answer_type": data.get("answer_type", "numeric"),
        "solution_steps": data.get("solution_steps", ""),
        "hint": data.get("hint", ""),
        "created_at": time.time(),
        "answered": False,
    }

    logger.info("[concept-service] practice session created: %s", session_id)

    return {
        "session_id": session_id,
        "question": data.get("question", text),
        "hint": data.get("hint"),
        "difficulty": data.get("difficulty", "medium"),
        "topic": topic,
        "subtopic": subtopic,
    }


def evaluate_user_answer(session_id: str, user_answer: str) -> dict:
    """Evaluate a user's answer to a practice question."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Practice session not found.")

    if session["answered"]:
        return {
            "session_id": session_id,
            "already_answered": True,
            "message": "You have already answered this question.",
            "correct_answer": session["correct_answer"],
            "solution": session["solution_steps"],
        }

    # Reuse the exam service's answer evaluator
    from app.services.exam_service import evaluate_answer

    is_correct = evaluate_answer(
        user_answer,
        session["correct_answer"],
        session.get("answer_type", "numeric"),
    )

    session["answered"] = True

    logger.info(
        "[concept-service] eval: session=%s correct=%s user='%s' expected='%s'",
        session_id, is_correct, user_answer, session["correct_answer"],
    )

    # Generate detailed feedback via LLM if wrong
    feedback = ""
    if not is_correct:
        feedback_prompt = f"""The student answered incorrectly.

Question: {session['question']}
Student's answer: {user_answer}
Correct answer: {session['correct_answer']}

Provide brief, encouraging feedback:
1. What mistake they likely made
2. The correct approach in 2-3 sentences
3. A tip to avoid this mistake

Use LaTeX for math. Be concise and supportive."""
        feedback = _call_llm(feedback_prompt, CONCEPT_SYSTEM) or ""

    message = "✅ Correct! Well done!" if is_correct else "❌ Not quite right. Let's learn from this!"

    return {
        "session_id": session_id,
        "is_correct": is_correct,
        "message": message,
        "user_answer": user_answer,
        "correct_answer": session["correct_answer"],
        "solution": session["solution_steps"],
        "feedback": feedback,
        "topic": session["topic"],
        "subtopic": session["subtopic"],
    }


def get_supported_topics() -> dict:
    """Return the topic tree."""
    return SUPPORTED_TOPICS
