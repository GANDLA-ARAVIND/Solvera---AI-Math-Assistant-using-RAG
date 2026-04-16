"""JEE Exam Service — session management, question generation, answer evaluation.

Uses both predefined dataset AND LLM-based question generation.
Evaluates answers with SymPy symbolic comparison + numeric tolerance.
Generates step-by-step solutions via RAG + LLM cascade.
"""

import json
import uuid
import time
import random
import logging
import re
import os
from pathlib import Path

from sympy import (
    symbols, simplify, Rational, pi, E, oo,
    sin, cos, tan, sqrt, exp, log, factorial,
    nsimplify,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

logger = logging.getLogger(__name__)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


# ═══════════════════════════════════════════════════════════════════════════
#  In-memory session store
# ═══════════════════════════════════════════════════════════════════════════
_sessions: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════════════════════
#  Load predefined questions
# ═══════════════════════════════════════════════════════════════════════════
_QUESTIONS: list[dict] = []


def _load_questions():
    """Load the predefined JEE question bank from JSON."""
    global _QUESTIONS
    data_path = Path(__file__).resolve().parent.parent / "knowledge_base" / "data" / "jee_questions.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            _QUESTIONS = json.load(f)
        logger.info("Loaded %d predefined JEE questions.", len(_QUESTIONS))
    else:
        logger.warning("jee_questions.json not found at %s", data_path)


_load_questions()


# ═══════════════════════════════════════════════════════════════════════════
#  LLM-based question generation
# ═══════════════════════════════════════════════════════════════════════════
_LLM_QUESTION_PROMPT = """You are a JEE Mathematics question generator.
Generate ONE math question at "{difficulty}" difficulty level.

Topic preference: {topic}

You MUST respond in EXACTLY this JSON format (no markdown, no code fences):
{{
  "question": "The question text",
  "correct_answer": "The numeric or symbolic answer (e.g. 42 or 3*x**2)",
  "answer_type": "numeric or expression",
  "topic": "algebra/calculus/trigonometry/geometry/statistics",
  "solution_query": "A prompt to generate the step-by-step solution"
}}

Rules:
- If answer_type is "numeric", correct_answer must be a number or simple fraction like "3/4"
- If answer_type is "expression", correct_answer must be a valid SymPy expression like "3*x**2"
- Make the question appropriate for JEE Mains level
- Keep the question clear and unambiguous
- Do NOT include code fences or markdown formatting
"""


def _generate_llm_question(difficulty: str) -> dict | None:
    """Try to generate a question via the LLM cascade."""
    try:
        import google.generativeai as genai
        from app.config import GOOGLE_API_KEY, GEMINI_MODEL

        if not GOOGLE_API_KEY:
            return None

        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        topics = ["algebra", "calculus", "trigonometry", "geometry", "statistics"]
        topic = random.choice(topics)

        prompt = _LLM_QUESTION_PROMPT.format(difficulty=difficulty, topic=topic)
        resp = model.generate_content(
            prompt,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        )

        if not resp.text:
            return None

        # Clean the response — strip markdown code fences if present
        raw = resp.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        # Validate required fields
        required = {"question", "correct_answer", "answer_type", "topic", "solution_query"}
        if not required.issubset(data.keys()):
            return None

        data["id"] = f"llm_{uuid.uuid4().hex[:8]}"
        data["difficulty"] = difficulty
        return data

    except Exception as e:
        logger.warning("LLM question generation failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Question selection (dataset + LLM hybrid)
# ═══════════════════════════════════════════════════════════════════════════
def _pick_question(difficulty: str, used_ids: set[str]) -> dict | None:
    """Pick a question — alternates between dataset and LLM generation."""
    # Map difficulty names
    diff_map = {"basic": "basic", "medium": "medium", "hard": "hard"}
    mapped_diff = diff_map.get(difficulty, "medium")

    # Get available predefined questions for this difficulty
    pool = [q for q in _QUESTIONS if q["difficulty"] == mapped_diff and q["id"] not in used_ids]

    # Strategy: try predefined first, then LLM, then any predefined
    if pool:
        # 50% chance to use LLM if we have predefined ones available too
        if random.random() < 0.4:
            llm_q = _generate_llm_question(mapped_diff)
            if llm_q:
                return llm_q
        return random.choice(pool)

    # No predefined left — must use LLM
    llm_q = _generate_llm_question(mapped_diff)
    if llm_q:
        return llm_q

    # Last resort: pick any unused question
    fallback = [q for q in _QUESTIONS if q["id"] not in used_ids]
    if fallback:
        return random.choice(fallback)

    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Answer evaluation with SymPy
# ═══════════════════════════════════════════════════════════════════════════
def _clean_expr(s: str) -> str:
    """Clean a math expression for SymPy parsing."""
    s = s.strip()
    # Remove LaTeX formatting
    s = re.sub(r"\\frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", s)
    s = s.replace("\\cdot", "*").replace("\\times", "*")
    s = s.replace("\\pi", "pi").replace("\\sqrt", "sqrt")
    s = s.replace("\\sin", "sin").replace("\\cos", "cos")
    s = s.replace("\\tan", "tan").replace("\\log", "log")
    s = s.replace("\\ln", "log").replace("\\exp", "exp")
    s = s.replace("^", "**")
    s = re.sub(r"[$$\\]", "", s)
    return s.strip()


def evaluate_answer(user_answer: str, correct_answer: str, answer_type: str) -> bool:
    """Compare user_answer with correct_answer using SymPy.

    Uses simplify(user - correct) == 0 for expressions,
    and numeric tolerance for numeric answers.
    """
    try:
        user_clean = _clean_expr(user_answer)
        correct_clean = _clean_expr(correct_answer)

        # Handle set answers like "[2, 3]"
        if answer_type == "set":
            try:
                correct_set = set(str(x).strip() for x in json.loads(correct_clean))
                # User might type "2, 3" or "{2, 3}" or "[2, 3]"
                user_input = user_clean.strip("{}[] ")
                user_set = set(x.strip() for x in user_input.split(","))
                if correct_set == user_set:
                    return True
                # Try numeric comparison
                correct_nums = set()
                for v in correct_set:
                    try:
                        correct_nums.add(float(parse_expr(v, transformations=TRANSFORMATIONS).evalf()))
                    except Exception:
                        correct_nums.add(v)
                user_nums = set()
                for v in user_set:
                    try:
                        user_nums.add(float(parse_expr(v, transformations=TRANSFORMATIONS).evalf()))
                    except Exception:
                        user_nums.add(v)
                return correct_nums == user_nums
            except Exception:
                pass

        # Parse both
        user_expr = parse_expr(user_clean, transformations=TRANSFORMATIONS)
        correct_expr = parse_expr(correct_clean, transformations=TRANSFORMATIONS)

        # Symbolic comparison: simplify(user - correct) == 0
        diff = simplify(user_expr - correct_expr)
        if diff == 0:
            return True

        # Numeric tolerance comparison
        try:
            user_val = complex(user_expr.evalf())
            correct_val = complex(correct_expr.evalf())
            if abs(user_val - correct_val) < 1e-6:
                return True
            # Relative tolerance for larger numbers
            if abs(correct_val) > 1e-10:
                if abs((user_val - correct_val) / correct_val) < 1e-4:
                    return True
        except Exception:
            pass

        return False

    except Exception as e:
        logger.debug("SymPy evaluation failed: %s — falling back to string compare", e)
        # String comparison fallback
        try:
            return float(user_answer.strip()) == float(correct_answer.strip())
        except Exception:
            return user_answer.strip().lower() == correct_answer.strip().lower()


# ═══════════════════════════════════════════════════════════════════════════
#  Solution generation (reuse existing solver pipeline)
# ═══════════════════════════════════════════════════════════════════════════
def _generate_solution(question_data: dict) -> str:
    """Generate a step-by-step solution using the solver service (RAG + LLM)."""
    try:
        from app.services.solver_service import solver_service

        query = question_data.get("solution_query", question_data["question"])
        topic = question_data.get("topic", "general_math")

        # Get RAG context
        rag_context, feedback_context, _ = solver_service.get_context(query, topic)

        # Generate solution via LLM cascade
        solution = solver_service.generate_response(
            context=rag_context,
            query=query,
            feedback_context=feedback_context,
        )
        return solution

    except Exception as e:
        logger.warning("Solution generation failed: %s", e)
        return f"**Solution:**\n\nThe correct answer is: {question_data.get('correct_answer', 'N/A')}\n\nPlease refer to your textbook for the detailed step-by-step solution."


# ═══════════════════════════════════════════════════════════════════════════
#  Public API — called from routes
# ═══════════════════════════════════════════════════════════════════════════

def start_exam(level: str, user_id: int) -> dict:
    """Create a new exam session and return the first question."""
    if level not in ("basic", "medium", "hard"):
        raise ValueError("Invalid difficulty level. Choose: basic, medium, hard")

    session_id = uuid.uuid4().hex
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "difficulty": level,
        "score": 0,
        "correct_count": 0,
        "total_attempted": 0,
        "used_question_ids": set(),
        "current_question": None,
        "question_start_time": None,
        "total_time": 0.0,
        "topic_stats": {},  # topic -> {"correct": int, "total": int}
        "created_at": time.time(),
    }

    # Pick first question
    question_data = _pick_question(level, session["used_question_ids"])
    if not question_data:
        raise RuntimeError("No questions available for this difficulty level.")

    session["current_question"] = question_data
    session["used_question_ids"].add(question_data["id"])
    session["question_start_time"] = time.time()

    _sessions[session_id] = session

    return {
        "session_id": session_id,
        "question_number": 1,
        "total_questions": session["total_attempted"] + 1,
        "question": question_data["question"],
        "topic": question_data.get("topic", "general_math"),
        "difficulty": level,
        "score": 0,
        "correct_count": 0,
    }


def get_question(session_id: str) -> dict:
    """Get the current question for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found.")

    q = session["current_question"]
    if not q:
        raise ValueError("No current question. Call next_question first.")

    return {
        "session_id": session_id,
        "question_number": session["total_attempted"] + 1,
        "total_questions": session["total_attempted"] + 1,
        "question": q["question"],
        "topic": q.get("topic", "general_math"),
        "difficulty": session["difficulty"],
        "score": session["score"],
        "correct_count": session["correct_count"],
    }


def submit_answer(session_id: str, user_answer: str) -> dict:
    """Evaluate the user's answer and generate solution."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found.")

    q = session["current_question"]
    if not q:
        raise ValueError("No current question to answer.")

    # Stop timer
    time_taken = time.time() - session["question_start_time"]
    session["total_time"] += time_taken

    # Evaluate answer
    is_correct = evaluate_answer(
        user_answer,
        q["correct_answer"],
        q.get("answer_type", "numeric"),
    )

    # Update stats
    session["total_attempted"] += 1
    if is_correct:
        session["correct_count"] += 1
        # Score: basic=1, medium=2, hard=3
        points = {"basic": 1, "medium": 2, "hard": 3}.get(session["difficulty"], 1)
        session["score"] += points

    # Track topic stats
    topic = q.get("topic", "general_math")
    if topic not in session["topic_stats"]:
        session["topic_stats"][topic] = {"correct": 0, "total": 0}
    session["topic_stats"][topic]["total"] += 1
    if is_correct:
        session["topic_stats"][topic]["correct"] += 1

    # Calculate accuracy
    accuracy = (session["correct_count"] / session["total_attempted"]) * 100

    # Generate step-by-step solution
    solution = _generate_solution(q)

    # Clear current question (user must call next_question)
    session["current_question"] = None

    message = "✅ Your answer is correct!" if is_correct else "❌ Your answer is incorrect."

    return {
        "is_correct": is_correct,
        "message": message,
        "correct_answer": q["correct_answer"],
        "user_answer": user_answer,
        "solution": solution,
        "time_taken_seconds": round(time_taken, 2),
        "score": session["score"],
        "correct_count": session["correct_count"],
        "total_attempted": session["total_attempted"],
        "accuracy_percent": round(accuracy, 1),
        "session_id": session_id,
    }


def next_question(session_id: str) -> dict:
    """Generate the next question for the session."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found.")

    question_data = _pick_question(session["difficulty"], session["used_question_ids"])
    if not question_data:
        raise ValueError("No more questions available. Session is complete!")

    session["current_question"] = question_data
    session["used_question_ids"].add(question_data["id"])
    session["question_start_time"] = time.time()

    return {
        "session_id": session_id,
        "question_number": session["total_attempted"] + 1,
        "total_questions": session["total_attempted"] + 1,
        "question": question_data["question"],
        "topic": question_data.get("topic", "general_math"),
        "difficulty": session["difficulty"],
        "score": session["score"],
        "correct_count": session["correct_count"],
    }


def get_session_info(session_id: str) -> dict:
    """Get full session statistics."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found.")

    accuracy = 0.0
    if session["total_attempted"] > 0:
        accuracy = (session["correct_count"] / session["total_attempted"]) * 100

    # Identify weak topics (below 50% accuracy)
    weak_topics = []
    for topic, stats in session["topic_stats"].items():
        if stats["total"] > 0 and (stats["correct"] / stats["total"]) < 0.5:
            weak_topics.append(topic)

    return {
        "session_id": session_id,
        "difficulty": session["difficulty"],
        "score": session["score"],
        "correct_count": session["correct_count"],
        "total_attempted": session["total_attempted"],
        "accuracy_percent": round(accuracy, 1),
        "total_time_seconds": round(session["total_time"], 2),
        "weak_topics": weak_topics,
    }


def end_session(session_id: str) -> dict:
    """End session and return final stats."""
    info = get_session_info(session_id)
    # Clean up
    if session_id in _sessions:
        del _sessions[session_id]
    return info
