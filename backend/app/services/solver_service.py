"""Solver service — LLM-first pipeline: classify → RAG → Gemini → Groq → SymPy/OpenAI.

Architecture (v3 — LLM-first with SymPy verification):
    1. Query classification (is it math?)
    2. Query preprocessing & math expression extraction
    3. Math type detection (derivative, integral, equation, …)
    4. RAG context retrieval (top 3: formula, concept, example)
    5. LLM step-by-step solution: Gemini (primary) → Groq (fallback)
    6. If all LLMs fail: SymPy compute + OpenAI explain (last resort)
    7. SymPy verification of the final answer

Priority: Gemini API → Groq → SymPy/OpenAI
"""

import re
import logging
import json
from datetime import datetime

import google.generativeai as genai

from app.config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    USE_GROQ,
    OPENAI_API_KEY,
    USE_OPENAI,
    OPENAI_MODEL,
    USE_OLLAMA,
    OLLAMA_MODEL,
)
from app.services.query_classifier import query_classifier
from app.services.rag_service import rag_service
from app.services.sympy_validator import sympy_validator
from app.services.plot_service import plot_service
from app.services.feedback_service import feedback_service
from app.services import ollama_service
from app.solver.query_parser import preprocess_query, extract_math_expression
from app.solver.math_type_detector import detect_math_type
from app.solver.sympy_solver import sympy_solve
from app.solver.explanation_generator import explanation_generator
from app.services.reasoning_agent import reasoning_agent
from app.utils.prompts import (
    MATH_SOLVER_SYSTEM_PROMPT,
    MATH_SOLVER_WITH_RAG_PROMPT,
    MATH_SOLVER_WITH_CONTEXT_PROMPT,
)
from app.utils.latex_utils import fix_latex_formatting, extract_final_answer

logger = logging.getLogger(__name__)

# ── Pipeline debug log storage ──────────────────────────────────────────
_pipeline_logs: list[dict] = []

def get_pipeline_logs(last_n: int = 50) -> list[dict]:
    """Return the last *n* pipeline debug logs."""
    return _pipeline_logs[-last_n:]

# Keywords that suggest a plot would be useful
PLOT_TRIGGER_KEYWORDS = [
    "graph", "plot", "sketch", "draw", "visualize", "curve",
    "function", "f(x)", "y =", "y=",
]

# Difficulty estimation keywords
DIFFICULTY_MARKERS = {
    "basic": ["what is", "define", "simple", "basic", "evaluate", "calculate"],
    "intermediate": [
        "solve", "find", "prove", "show that", "integrate", "differentiate",
        "factor", "simplify",
    ],
    "advanced": [
        "differential equation", "optimization", "convergence", "series expansion",
        "partial fraction", "by parts", "reduction formula", "parametric",
        "multiple integrals", "JEE", "competition", "olympiad",
    ],
}

FOLLOW_UP_MAP = {
    "algebra": [
        "Try solving a system of linear equations",
        "Practice factoring a cubic polynomial",
        "Explore quadratic inequalities",
    ],
    "calculus": [
        "Find the area under a curve using integration",
        "Try a related rates problem",
        "Practice using L'Hôpital's rule for limits",
    ],
    "geometry": [
        "Find the equation of a tangent to a circle",
        "Practice coordinate geometry with conic sections",
        "Try a locus problem",
    ],
    "trigonometry": [
        "Prove a trigonometric identity",
        "Solve a trigonometric equation in [0, 2π)",
        "Try an inverse trigonometry problem",
    ],
    "statistics": [
        "Calculate probability using Bayes' theorem",
        "Find mean and variance of a distribution",
        "Try a permutation and combination problem",
    ],
    "number_theory": [
        "Find GCD using Euclidean algorithm",
        "Prove a statement using mathematical induction",
        "Try a modular arithmetic problem",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# SolverService — LLM-first Architecture (Gemini → Groq → SymPy/OpenAI)
# ═══════════════════════════════════════════════════════════════════════════
class SolverService:

    def __init__(self):
        # Provider ordering: Gemini → Groq → OpenAI → Ollama
        self._providers: list[str] = []

        if GOOGLE_API_KEY:
            genai.configure(api_key=GOOGLE_API_KEY)
            self.gemini_model = genai.GenerativeModel(
                GEMINI_MODEL,
                system_instruction=MATH_SOLVER_SYSTEM_PROMPT,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            self._providers.append("gemini")
            logger.info("Gemini available (%s)", GEMINI_MODEL)

        if GROQ_API_KEY:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            self.groq_model = "llama-3.3-70b-versatile"
            self._providers.append("groq")
            logger.info("Groq available (%s)", self.groq_model)

        if USE_OPENAI and OPENAI_API_KEY:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
            self.openai_model = OPENAI_MODEL
            self._providers.append("openai")
            logger.info("OpenAI available (%s)", self.openai_model)

        if USE_OLLAMA:
            self._providers.append("ollama")
            logger.info("Ollama available (%s)", OLLAMA_MODEL)

        self.provider = self._providers[0] if self._providers else "sympy"
        logger.info(
            "LLM-first pipeline ready — Gemini primary, Groq fallback, SymPy/OpenAI last resort. "
            "Provider cascade: %s",
            " → ".join(self._providers) if self._providers else "none",
        )

    # ===================================================================
    #  Public helpers (backward-compatible)
    # ===================================================================
    def get_context(
        self, query: str, topic: str = "general_math", n_results: int = 3
    ) -> tuple[str, str, list[dict]]:
        """Retrieve relevant RAG context + feedback corrections (top 3)."""
        retrieved_docs = rag_service.retrieve_top3(query, topic_filter=topic)
        rag_context = rag_service.format_context_structured(retrieved_docs)
        feedback_context = feedback_service.get_relevant_corrections(query, topic)
        return rag_context, feedback_context, retrieved_docs

    def generate_response(
        self,
        context: str,
        query: str,
        feedback_context: str = "",
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Legacy LLM generation — kept for backward compatibility.

        The hybrid pipeline (``solve()``) uses SymPy + explanation_generator instead.
        """
        last_error = None
        for provider in self._providers:
            try:
                result = self._call_provider(
                    provider, context, query, feedback_context, conversation_history
                )
                self.provider = provider
                return result
            except Exception as exc:
                logger.warning(
                    "%s failed (%s: %s) — trying next provider.",
                    provider, type(exc).__name__, exc,
                )
                last_error = exc

        # All LLMs exhausted → SymPy fallback
        logger.warning("All LLM providers failed — falling back to SymPy.")
        fallback = self._sympy_fallback(query)
        if fallback:
            self.provider = "sympy"
            return fallback

        if last_error:
            raise last_error
        raise RuntimeError("No LLM providers configured and SymPy could not solve this.")

    def validate_with_sympy(self, query: str, solution: str, topic: str) -> dict:
        """Extract the final answer from *solution* and cross-check with SymPy."""
        return self._attempt_validation(query, solution, topic)

    # ===================================================================
    #  LLM-FIRST PIPELINE — the main solve() method
    # ===================================================================
    async def solve(
        self,
        query: str,
        user_id: int = None,
        include_plot: bool = False,
        conversation_history: list[dict] = None,
    ) -> dict:
        """LLM-first pipeline: classify → RAG → Gemini → Groq → SymPy/OpenAI.

        Priority: Gemini for full step-by-step → Groq fallback → SymPy/OpenAI last resort.
        SymPy is used for verification.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": query,
            "detected_math_type": None,
            "sympy_result": None,
            "rag_context_summary": None,
            "explanation_generated": False,
            "provider_used": None,
        }

        # ── Step 1: Classify ─────────────────────────────────────────────
        classification = query_classifier.is_math_query(query)
        if not classification["is_math"]:
            log_entry["detected_math_type"] = "non_math"
            _pipeline_logs.append(log_entry)
            return {
                "success": False,
                "error": "non_math_query",
                "message": (
                    "I can only help with mathematics questions. "
                    "Please ask a math-related question."
                ),
                "classification": classification,
            }

        topic = classification.get("topic", "general_math")
        difficulty = self._estimate_difficulty(query)

        # ── Step 2: Query Preprocessing ──────────────────────────────────
        parsed = extract_math_expression(query)
        logger.info("Parsed expression: %s", parsed)

        # ── Step 3: Math Type Detection ──────────────────────────────────
        math_type_info = detect_math_type(query)
        math_type = math_type_info["type"]
        log_entry["detected_math_type"] = math_type
        logger.info(
            "Detected math type: %s (confidence: %.2f)",
            math_type, math_type_info["confidence"],
        )

        # ── Step 3b: Reasoning Plan Generation ───────────────────────────
        reasoning_plan = reasoning_agent.generate_plan(
            query, math_type, math_type_info["confidence"]
        )
        logger.info("Reasoning plan: %d steps generated", len(reasoning_plan))

        # ── Step 4: RAG Context Retrieval (top 3) ────────────────────────
        rag_context, feedback_context, retrieved_docs = self.get_context(query, topic)
        log_entry["rag_context_summary"] = f"{len(retrieved_docs)} docs retrieved"

        # ── Step 5: SymPy Computation (for verification) ─────────────────
        sympy_result = sympy_solve(math_type, parsed)
        log_entry["sympy_result"] = sympy_result.get("result_str", "failed")
        logger.info(
            "SymPy result: success=%s, answer=%s",
            sympy_result["success"], sympy_result.get("result_str", "N/A"),
        )

        # ── Step 6: Generate Step-by-Step Solution ───────────────────────
        #    Priority: Gemini → Groq → SymPy/OpenAI
        solution_text = None

        # --- Try Gemini API (primary) ---
        if "gemini" in self._providers:
            try:
                logger.info("Trying Gemini for full step-by-step solution...")
                prompt = self._build_step_by_step_prompt(
                    query, rag_context, feedback_context,
                    conversation_history, sympy_result,
                )
                resp = self.gemini_model.generate_content(
                    prompt,
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ],
                )
                if resp.text and len(resp.text.strip()) > 50:
                    solution_text = fix_latex_formatting(resp.text)
                    self.provider = "gemini"
                    log_entry["provider_used"] = "gemini"
                    log_entry["explanation_generated"] = True
                    logger.info("Gemini generated step-by-step solution successfully.")
                else:
                    raise ValueError("Gemini returned empty or too-short response")
            except Exception as exc:
                logger.info("Gemini unavailable, switching to Groq.")

        # --- Try Groq (secondary) ---
        if solution_text is None and "groq" in self._providers:
            try:
                logger.info("Trying Groq for full step-by-step solution...")
                prompt = self._build_step_by_step_prompt(
                    query, rag_context, feedback_context,
                    conversation_history, sympy_result,
                )
                resp = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {"role": "system", "content": MATH_SOLVER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
                content = resp.choices[0].message.content
                if content and len(content.strip()) > 50:
                    solution_text = fix_latex_formatting(content)
                    self.provider = "groq"
                    log_entry["provider_used"] = "groq"
                    log_entry["explanation_generated"] = True
                    logger.info("Groq generated step-by-step solution successfully.")
                else:
                    raise ValueError("Groq returned empty or too-short response")
            except Exception as exc:
                logger.info("Groq unavailable, switching to SymPy/OpenAI.")

        # --- Last resort: SymPy compute + OpenAI explain ---
        if solution_text is None:
            logger.info("All primary LLMs failed — using SymPy/OpenAI last resort.")
            if sympy_result["success"]:
                # Try OpenAI to explain the SymPy result
                if "openai" in self._providers:
                    try:
                        logger.info("Trying OpenAI to explain SymPy result...")
                        solution_text = explanation_generator.generate(
                            question=query,
                            sympy_result=sympy_result,
                            rag_context=rag_context,
                            conversation_history=conversation_history,
                        )
                        solution_text = fix_latex_formatting(solution_text)
                        self.provider = f"sympy+openai"
                        log_entry["provider_used"] = "sympy+openai"
                        log_entry["explanation_generated"] = True
                    except Exception as exc:
                        logger.info("OpenAI unavailable, using SymPy-only format.")

                # If OpenAI also failed, format SymPy result directly
                if solution_text is None:
                    solution_text = explanation_generator._format_sympy_only(
                        query, sympy_result
                    )
                    self.provider = "sympy"
                    log_entry["provider_used"] = "sympy_only"
            else:
                # SymPy also failed — try generate_response as absolute fallback
                try:
                    solution_text = self.generate_response(
                        context=rag_context,
                        query=query,
                        feedback_context=feedback_context,
                        conversation_history=conversation_history,
                    )
                    solution_text = fix_latex_formatting(solution_text)
                    log_entry["provider_used"] = self.provider
                except Exception as e:
                    _pipeline_logs.append(log_entry)
                    return {
                        "success": False,
                        "error": "generation_error",
                        "message": f"Failed to generate solution: {str(e)}",
                    }

        # ── Step 7: Build Validation ─────────────────────────────────────
        if sympy_result["success"]:
            validation = {
                "attempted": True,
                "verified": True,
                "sympy_answer": sympy_result["result_str"],
                "match": True,
                "details": "Answer verified by SymPy",
                "latex": sympy_result.get("result_latex", ""),
            }
        else:
            validation = self.validate_with_sympy(query, solution_text, topic)

        # ── Step 8: Auto-generate plot if applicable ─────────────────────
        plot_url = None
        should_plot = include_plot or self._should_auto_plot(query, topic)
        if should_plot:
            plot_result = self._try_generate_plot(query, solution_text)
            if plot_result and plot_result.get("success"):
                plot_url = plot_result["plot_url"]

        # ── Step 9: Follow-up suggestions ────────────────────────────────
        follow_ups = self._get_follow_up_suggestions(topic, difficulty)

        # ── Step 10: Log and return ──────────────────────────────────────
        _pipeline_logs.append(log_entry)
        if len(_pipeline_logs) > 200:
            _pipeline_logs.pop(0)

        return {
            "success": True,
            "query": query,
            "topic": topic,
            "difficulty": difficulty,
            "classification": classification,
            "solution": solution_text,
            "reasoning_plan": reasoning_plan,
            "llm_provider": self.provider,
            "sympy_computed": sympy_result["success"],
            "math_type": math_type,
            "validation": validation,
            "plot_url": plot_url,
            "follow_up_suggestions": follow_ups,
            "rag_sources": [
                {
                    "title": d["metadata"].get("title", "Unknown"),
                    "topic": d["metadata"].get("topic", ""),
                    "relevance": round(d["relevance_score"], 3),
                }
                for d in retrieved_docs
            ],
        }

    # ===================================================================
    #  Provider dispatch (legacy — used by generate_response fallback)
    # ===================================================================
    def _call_provider(
        self,
        provider: str,
        context: str,
        query: str,
        feedback_context: str = "",
        conversation_history: list[dict] | None = None,
    ) -> str:
        if provider == "openai":
            return self._call_openai(context, query, feedback_context, conversation_history)

        if provider == "ollama":
            combined = context
            if feedback_context:
                combined += "\n" + feedback_context
            if conversation_history:
                return ollama_service.generate_response_with_history(
                    context=combined,
                    query=query,
                    conversation_history=conversation_history,
                    system_prompt=MATH_SOLVER_SYSTEM_PROMPT,
                )
            return ollama_service.generate_response(
                context=combined,
                query=query,
                system_prompt=MATH_SOLVER_SYSTEM_PROMPT,
            )

        if provider == "groq":
            prompt = self._build_prompt(context, query, feedback_context, conversation_history)
            resp = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": MATH_SOLVER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            return resp.choices[0].message.content

        if provider == "gemini":
            prompt = self._build_prompt(context, query, feedback_context, conversation_history)
            resp = self.gemini_model.generate_content(
                prompt,
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            )
            if not resp.text:
                raise ValueError("Gemini returned empty response")
            return resp.text

        raise ValueError(f"Unknown provider: {provider}")

    def _call_openai(
        self,
        context: str,
        query: str,
        feedback_context: str,
        conversation_history: list[dict] | None,
    ) -> str:
        messages = [{"role": "system", "content": MATH_SOLVER_SYSTEM_PROMPT}]
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "assistant" and len(content) > 500:
                    content = content[:500] + "..."
                messages.append({"role": role, "content": content})

        user_content = ""
        if context and not context.startswith("No specific"):
            user_content += f"RELEVANT REFERENCE MATERIAL:\n{context}\n\n"
        if feedback_context:
            user_content += f"{feedback_context}\n\n"
        user_content += (
            "Using the above reference material where applicable, "
            "solve the following problem step by step.\n\n"
            f"PROBLEM: {query}"
        )
        messages.append({"role": "user", "content": user_content})

        resp = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        return resp.choices[0].message.content

    # ===================================================================
    #  SymPy fallback — basic solution when API is down (legacy)
    # ===================================================================
    def _sympy_fallback(self, query: str) -> str | None:
        """Try to solve with SymPy and return a formatted string, or None."""
        try:
            parsed = extract_math_expression(query)
            math_type_info = detect_math_type(query)
            result = sympy_solve(math_type_info["type"], parsed)
            if result["success"]:
                return explanation_generator._format_sympy_only(query, result)
        except Exception as e:
            logger.debug("SymPy fallback failed: %s", e)
        return None

    # ===================================================================
    #  Helpers
    # ===================================================================
    def _build_step_by_step_prompt(
        self,
        query: str,
        rag_context: str,
        feedback_context: str = "",
        conversation_history: list[dict] | None = None,
        sympy_result: dict | None = None,
    ) -> str:
        """Build the prompt for full step-by-step solution generation."""
        parts = []

        # Add RAG context if available
        if rag_context and not rag_context.startswith("No specific"):
            parts.append(
                "══════════════════════════════════════\n"
                "REFERENCE MATERIAL (from knowledge base):\n"
                "══════════════════════════════════════\n"
                f"{rag_context}\n"
            )

        # Add feedback context if available
        if feedback_context:
            parts.append(f"{feedback_context}\n")

        # Add conversation history if available
        if conversation_history and len(conversation_history) > 0:
            conv_text = self._format_conversation(conversation_history[-6:])
            parts.append(
                "══════════════════════════════════════\n"
                "RECENT CONVERSATION:\n"
                "══════════════════════════════════════\n"
                f"{conv_text}\n"
            )

        # Add SymPy verification hint if available
        if sympy_result and sympy_result.get("success"):
            parts.append(
                "══════════════════════════════════════\n"
                "VERIFICATION (computed by SymPy):\n"
                "══════════════════════════════════════\n"
                f"SymPy answer: {sympy_result.get('result_str', 'N/A')}\n"
                f"LaTeX: $${sympy_result.get('result_latex', '')}$$\n"
                "Use this to verify your solution arrives at the same answer.\n"
            )

        parts.append(
            "══════════════════════════════════════\n"
            "INSTRUCTIONS:\n"
            "══════════════════════════════════════\n"
            "Solve the following problem with a COMPLETE step-by-step solution.\n\n"
            "REQUIREMENTS:\n"
            "• Show EVERY step — never skip intermediate calculations\n"
            "• Use LaTeX for all math ($...$ inline, $$...$$ display)\n"
            "• EXPLAIN the reasoning behind each step\n"
            "• Name all theorems, formulas, and identities used\n"
            "• End with a clearly marked ## Final Answer section\n\n"
            f"PROBLEM: {query}"
        )

        return "\n\n".join(parts)

    def _build_prompt(
        self,
        context: str,
        query: str,
        feedback_context: str = "",
        conversation_history: list[dict] | None = None,
    ) -> str:
        if conversation_history and len(conversation_history) > 0:
            conv_text = self._format_conversation(conversation_history[-6:])
            return MATH_SOLVER_WITH_CONTEXT_PROMPT.format(
                rag_context=context,
                feedback_context=feedback_context,
                conversation_history=conv_text,
                query=query,
            )
        return MATH_SOLVER_WITH_RAG_PROMPT.format(
            rag_context=context,
            feedback_context=feedback_context,
            query=query,
        )

    def _estimate_difficulty(self, query: str) -> str:
        query_lower = query.lower()
        scores = {"basic": 0, "intermediate": 0, "advanced": 0}
        for level, keywords in DIFFICULTY_MARKERS.items():
            for kw in keywords:
                if kw in query_lower:
                    scores[level] += 1
        if len(query) > 200:
            scores["advanced"] += 1
        if any(s in query for s in ["∫", "∑", "∏", "lim"]):
            scores["advanced"] += 1
        if re.search(r"\d{3,}", query):
            scores["intermediate"] += 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "intermediate"

    def _should_auto_plot(self, query: str, topic: str) -> bool:
        query_lower = query.lower()
        if any(kw in query_lower for kw in PLOT_TRIGGER_KEYWORDS):
            return True
        if topic == "calculus" and any(
            kw in query_lower for kw in ["curve", "function", "graph", "f(x)"]
        ):
            return True
        return False

    def _try_generate_plot(self, query: str, solution: str) -> dict | None:
        expr = self._extract_expression(query)
        if expr:
            try:
                return plot_service.generate_plot(expr)
            except Exception:
                pass
        patterns = [
            r"f\(x\)\s*=\s*(.+?)(?:\n|$)",
            r"y\s*=\s*(.+?)(?:\n|$)",
        ]
        for p in patterns:
            match = re.search(p, solution)
            if match:
                expr_str = match.group(1).strip().rstrip(".")
                expr_str = re.sub(r"\$+", "", expr_str).strip()
                expr_str = expr_str.replace("^", "**")
                expr_str = re.sub(r"\\frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", expr_str)
                expr_str = expr_str.replace("\\cdot", "*").replace("\\times", "*")
                expr_str = re.sub(r"\\[a-zA-Z]+", "", expr_str).strip()
                if expr_str and len(expr_str) < 100:
                    try:
                        return plot_service.generate_plot(expr_str)
                    except Exception:
                        pass
        return None

    def _format_conversation(self, history: list[dict]) -> str:
        parts = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant" and len(content) > 500:
                content = content[:500] + "..."
            parts.append(f"**{role.capitalize()}:** {content}")
        return "\n\n".join(parts)

    def _get_follow_up_suggestions(self, topic: str, difficulty: str) -> list[str]:
        suggestions = FOLLOW_UP_MAP.get(topic, FOLLOW_UP_MAP.get("algebra"))
        return suggestions[:3] if suggestions else []

    def _attempt_validation(self, query: str, solution: str, topic: str) -> dict:
        llm_answer = extract_final_answer(solution)
        if not llm_answer:
            return {
                "attempted": False,
                "reason": "Could not extract final answer from solution",
            }
        try:
            if topic in ["algebra", "number_theory"]:
                return sympy_validator.validate_equation(query, llm_answer)
            elif topic == "calculus":
                query_lower = query.lower()
                if any(
                    kw in query_lower
                    for kw in ["derivative", "differentiate", "d/dx", "dy/dx"]
                ):
                    expr = self._extract_expression(query)
                    if expr:
                        result = sympy_validator.validate_derivative(expr)
                        if result.get("sympy_answer"):
                            result["match"] = self._soft_compare(
                                result["sympy_answer"], llm_answer
                            )
                        return result
                elif any(
                    kw in query_lower
                    for kw in ["integral", "integrate", "antiderivative"]
                ):
                    expr = self._extract_expression(query)
                    if expr:
                        result = sympy_validator.validate_integral(expr)
                        if result.get("sympy_answer"):
                            result["match"] = self._soft_compare(
                                result["sympy_answer"], llm_answer
                            )
                        return result
                elif any(kw in query_lower for kw in ["limit", "lim"]):
                    expr = self._extract_expression(query)
                    if expr:
                        result = sympy_validator.validate_limit(query, expr)
                        if result.get("sympy_answer"):
                            result["match"] = self._soft_compare(
                                result["sympy_answer"], llm_answer
                            )
                        return result
            elif topic == "trigonometry":
                result = sympy_validator.validate_trig_expression(query, llm_answer)
                if result.get("attempted"):
                    return result
            elif topic in ["geometry", "statistics"]:
                result = sympy_validator.validate_numeric_result(query, llm_answer)
                if result.get("attempted"):
                    return result
        except Exception:
            pass

        return {
            "attempted": False,
            "reason": f"Validation not yet supported for topic: {topic}",
        }

    def _extract_expression(self, query: str) -> str | None:
        patterns = [
            r"(?:derivative|differentiate|integrate|integral)\s+(?:of\s+)?(.+?)(?:\s+with|\s+from|\s*$)",
            r"(?:d/dx|dy/dx)\s*[\(\[]?\s*(.+?)\s*[\)\]]?\s*$",
            r"∫\s*(.+?)\s*dx",
            r"(?:limit|lim)\s+(?:of\s+)?(.+?)(?:\s+as|\s+when|\s*$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                expr = match.group(1).strip().rstrip(".")
                expr = expr.replace("^", "**")
                return expr
        return None

    def _clean_equation(self, query: str) -> str | None:
        q = re.sub(r"^(solve|find|evaluate|calculate|simplify)\s+", "", query.lower()).strip()
        q = re.sub(r"\\frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", q)
        q = q.replace("\\cdot", "*").replace("\\times", "*")
        q = q.replace("^", "**")
        q = re.sub(r"[$$\\]", "", q).strip()
        if "=" in q:
            parts = q.split("=")
            if len(parts) == 2:
                return f"({parts[0].strip()}) - ({parts[1].strip()})"
        return q if q else None

    def _soft_compare(self, sympy_ans: str, llm_ans: str) -> bool:
        try:
            from sympy.parsing.sympy_parser import (
                parse_expr,
                standard_transformations,
                implicit_multiplication_application,
            )
            from sympy import simplify

            transforms = standard_transformations + (implicit_multiplication_application,)
            s_clean = re.sub(r"[$$\\]", "", sympy_ans).replace("^", "**").strip()
            l_clean = re.sub(r"[$$\\]", "", llm_ans).replace("^", "**").strip()
            s_expr = parse_expr(s_clean, transformations=transforms)
            l_expr = parse_expr(l_clean, transformations=transforms)
            return simplify(s_expr - l_expr) == 0
        except Exception:
            return sympy_ans.strip() == llm_ans.strip()


solver_service = SolverService()
