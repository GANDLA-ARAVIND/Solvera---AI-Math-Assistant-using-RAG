"""Explanation generator — uses Gemini/LLM ONLY to explain SymPy results.

The LLM never computes answers. It receives the correct answer from SymPy
and generates a student-friendly step-by-step explanation.
"""

import logging
import re

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
from app.services import ollama_service
from app.utils.prompts import EXPLANATION_SYSTEM_PROMPT, EXPLANATION_PROMPT

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """Generate step-by-step explanations for SymPy-computed answers."""

    def __init__(self):
        # Provider priority: Gemini → Groq → OpenAI → Ollama
        self._providers: list[str] = []

        if GOOGLE_API_KEY:
            genai.configure(api_key=GOOGLE_API_KEY)
            self.gemini_model = genai.GenerativeModel(
                GEMINI_MODEL,
                system_instruction=EXPLANATION_SYSTEM_PROMPT,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=3072,
                ),
            )
            self._providers.append("gemini")

        if GROQ_API_KEY:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            self.groq_model = "llama-3.3-70b-versatile"
            self._providers.append("groq")

        if USE_OPENAI and OPENAI_API_KEY:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
            self.openai_model = OPENAI_MODEL
            self._providers.append("openai")

        if USE_OLLAMA:
            self._providers.append("ollama")

        self.provider = self._providers[0] if self._providers else "none"
        logger.info("ExplanationGenerator providers: %s", self._providers)

    def generate(
        self,
        question: str,
        sympy_result: dict,
        rag_context: str = "",
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Generate a step-by-step explanation for the SymPy result.

        Args:
            question: Original user question.
            sympy_result: Dict from ``sympy_solve`` with keys like result_str,
                          result_latex, math_type, steps.
            rag_context: Relevant RAG context (formulas, concepts, examples).
            conversation_history: Prior conversation turns (optional).

        Returns:
            Formatted explanation string (Markdown + LaTeX).
        """
        if not self._providers:
            # No LLM available — return a formatted SymPy-only solution
            return self._format_sympy_only(question, sympy_result)

        prompt = self._build_prompt(question, sympy_result, rag_context)

        for provider in self._providers:
            try:
                explanation = self._call_provider(
                    provider, prompt, conversation_history
                )
                self.provider = provider
                # Ensure the final answer from SymPy is embedded
                explanation = self._ensure_correct_answer(
                    explanation, sympy_result
                )
                return explanation
            except Exception as exc:
                logger.info("Explanation: %s unavailable, trying next.", provider)

        # All providers failed — return SymPy-only answer
        logger.warning("All explanation providers failed — using SymPy-only format.")
        return self._format_sympy_only(question, sympy_result)

    # ──────────────────────────────────────────────────────────────────────
    #  Prompt Building
    # ──────────────────────────────────────────────────────────────────────

    def _build_prompt(
        self, question: str, sympy_result: dict, rag_context: str
    ) -> str:
        result_latex = sympy_result.get("result_latex", "")
        result_str = sympy_result.get("result_str", "")
        math_type = sympy_result.get("math_type", "")
        steps = sympy_result.get("steps", [])
        input_expr = sympy_result.get("input_expr", "")

        steps_text = "\n".join(f"  - {s}" for s in steps) if steps else "N/A"

        return EXPLANATION_PROMPT.format(
            question=question,
            math_type=math_type,
            input_expression=input_expr,
            sympy_answer=result_str,
            sympy_answer_latex=result_latex,
            computation_steps=steps_text,
            rag_context=rag_context if rag_context else "No additional context.",
        )

    # ──────────────────────────────────────────────────────────────────────
    #  Provider Dispatch
    # ──────────────────────────────────────────────────────────────────────

    def _call_provider(
        self,
        provider: str,
        prompt: str,
        conversation_history: list[dict] | None,
    ) -> str:
        if provider == "gemini":
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

        if provider == "groq":
            resp = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=3072,
            )
            return resp.choices[0].message.content

        if provider == "openai":
            messages = [
                {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            resp = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.4,
                max_tokens=3072,
            )
            return resp.choices[0].message.content

        if provider == "ollama":
            return ollama_service.generate_response(
                context="",
                query=prompt,
                system_prompt=EXPLANATION_SYSTEM_PROMPT,
            )

        raise ValueError(f"Unknown provider: {provider}")

    # ──────────────────────────────────────────────────────────────────────
    #  Answer Enforcement
    # ──────────────────────────────────────────────────────────────────────

    def _ensure_correct_answer(self, explanation: str, sympy_result: dict) -> str:
        """Make sure the explanation ends with the SymPy answer, not an LLM guess."""
        result_latex = sympy_result.get("result_latex", "")
        result_str = sympy_result.get("result_str", "")
        math_type = sympy_result.get("math_type", "")

        if not result_latex:
            return explanation

        # Check if the explanation already has a Final Answer section
        if re.search(r"##\s*Final\s*Answer", explanation, re.IGNORECASE):
            # Replace whatever is in the Final Answer section with the SymPy answer
            explanation = re.sub(
                r"(##\s*Final\s*Answer\s*\n).*?(?=\n##|\Z)",
                rf"\1$${result_latex}$$\n",
                explanation,
                flags=re.DOTALL | re.IGNORECASE,
            )
        else:
            # Append a Final Answer section
            # Add +C for indefinite integrals
            answer_display = result_latex
            if math_type == "integration":
                answer_display = f"{result_latex} + C"

            explanation += f"\n\n## Final Answer\n$${answer_display}$$"

        return explanation

    # ──────────────────────────────────────────────────────────────────────
    #  Fallback: SymPy-only formatted answer
    # ──────────────────────────────────────────────────────────────────────

    def _format_sympy_only(self, question: str, sympy_result: dict) -> str:
        """Produce a well-formatted answer using only SymPy data (no LLM)."""
        result_latex = sympy_result.get("result_latex", "?")
        result_str = sympy_result.get("result_str", "?")
        math_type = sympy_result.get("math_type", "computation")
        input_expr = sympy_result.get("input_expr", "?")
        steps = sympy_result.get("steps", [])

        parts = [
            "## Problem",
            f"{question}\n",
            f"## Solution (computed by SymPy)\n",
        ]

        for i, step in enumerate(steps, 1):
            parts.append(f"**Step {i}:** {step}\n")

        answer_display = result_latex
        if math_type == "integration":
            answer_display = f"{result_latex} + C"

        parts.append(f"\n## Final Answer")
        parts.append(f"$${answer_display}$$")

        return "\n".join(parts)


# Singleton
explanation_generator = ExplanationGenerator()
