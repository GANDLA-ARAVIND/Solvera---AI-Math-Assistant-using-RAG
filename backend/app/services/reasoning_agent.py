"""Multi-Step Reasoning Agent — generates a structured reasoning plan before solving.

Pipeline stages:
  1. Query Understanding
  2. Problem Type Detection
  3. Reasoning Plan Generation (via LLM)
  4. Returns plan steps for the solver to use alongside its computation
"""

import logging
import json
import re

import google.generativeai as genai

from app.config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
)

logger = logging.getLogger(__name__)

# ── Reasoning Plan Prompt ────────────────────────────────────────────────

REASONING_PLAN_PROMPT = """You are a mathematical reasoning planner. Given a math problem, generate a concise step-by-step reasoning plan that describes HOW to solve it — do NOT actually compute the answer.

RULES:
1. Output ONLY a JSON array of step objects. No extra text before or after.
2. Each step must have "step" (number), "title" (short action phrase), and "description" (1-2 sentence explanation of what to do and why).
3. Generate 3-6 steps depending on problem complexity.
4. The last step should always be about computing or stating the final answer.
5. Name the specific mathematical rules, theorems, or techniques to apply.

EXAMPLE OUTPUT:
[
  {{"step": 1, "title": "Identify the function", "description": "Recognise the given expression as a polynomial function f(x) = x² + 3x + 2."}},
  {{"step": 2, "title": "Choose the solving method", "description": "Since this is a quadratic equation, apply the Quadratic Formula or factoring."}},
  {{"step": 3, "title": "Factor the polynomial", "description": "Find two numbers that multiply to 2 and add to 3: (x+1)(x+2)."}},
  {{"step": 4, "title": "Solve for roots", "description": "Set each factor to zero: x = -1 and x = -2."}},
  {{"step": 5, "title": "State the final answer", "description": "The roots of x² + 3x + 2 = 0 are x = -1 and x = -2."}}
]

PROBLEM TYPE: {math_type}
PROBLEM: {query}
"""


class ReasoningAgent:
    """Generates a reasoning plan for a math problem using the LLM."""

    def generate_plan(
        self, query: str, math_type: str, math_type_confidence: float = 0.0
    ) -> list[dict]:
        """Return a list of reasoning step dicts: [{step, title, description}, ...]"""
        prompt = REASONING_PLAN_PROMPT.format(math_type=math_type, query=query)

        # Try Gemini first, then Groq
        plan_text = self._call_gemini(prompt)
        if plan_text is None:
            plan_text = self._call_groq(prompt)

        if plan_text is None:
            # Fallback: generate a generic plan based on math type
            return self._generic_plan(query, math_type)

        return self._parse_plan(plan_text, query, math_type)

    # ── LLM Calls ────────────────────────────────────────────────────────

    def _call_gemini(self, prompt: str) -> str | None:
        if not GOOGLE_API_KEY:
            return None
        try:
            model = genai.GenerativeModel(
                GEMINI_MODEL,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
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
            if resp.text and resp.text.strip():
                return resp.text.strip()
        except Exception as e:
            logger.warning("Reasoning agent Gemini failed: %s", e)
        return None

    def _call_groq(self, prompt: str) -> str | None:
        if not GROQ_API_KEY:
            return None
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a mathematical reasoning planner. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception as e:
            logger.warning("Reasoning agent Groq failed: %s", e)
        return None

    # ── Parsing ──────────────────────────────────────────────────────────

    def _parse_plan(self, text: str, query: str, math_type: str) -> list[dict]:
        """Parse LLM output into a list of step dicts."""
        # Extract JSON array from the text (LLM may wrap it in markdown)
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                steps = json.loads(json_match.group())
                if isinstance(steps, list) and len(steps) >= 2:
                    # Validate and normalize
                    clean = []
                    for i, s in enumerate(steps):
                        if isinstance(s, dict) and "title" in s:
                            clean.append({
                                "step": s.get("step", i + 1),
                                "title": str(s["title"]),
                                "description": str(s.get("description", "")),
                            })
                    if len(clean) >= 2:
                        return clean
            except json.JSONDecodeError:
                logger.warning("Failed to parse reasoning plan JSON")

        return self._generic_plan(query, math_type)

    # ── Generic Fallback Plans ───────────────────────────────────────────

    def _generic_plan(self, query: str, math_type: str) -> list[dict]:
        """Return a sensible default plan when the LLM is unavailable."""
        plans = {
            "derivative": [
                {"step": 1, "title": "Identify the function", "description": "Parse the input to identify the function to differentiate."},
                {"step": 2, "title": "Determine differentiation rules", "description": "Identify which rules apply: power rule, chain rule, product rule, or quotient rule."},
                {"step": 3, "title": "Apply differentiation", "description": "Differentiate term by term, applying the identified rules."},
                {"step": 4, "title": "Simplify the result", "description": "Combine like terms and simplify the derivative expression."},
                {"step": 5, "title": "State the final answer", "description": "Present the derivative in its simplest form."},
            ],
            "second_derivative": [
                {"step": 1, "title": "Identify the function", "description": "Parse the input to identify the function."},
                {"step": 2, "title": "Compute the first derivative", "description": "Differentiate the function once using appropriate rules."},
                {"step": 3, "title": "Compute the second derivative", "description": "Differentiate the first derivative to get f''(x)."},
                {"step": 4, "title": "Simplify", "description": "Simplify the second derivative expression."},
                {"step": 5, "title": "State the final answer", "description": "Present f''(x) in simplified form."},
            ],
            "integration": [
                {"step": 1, "title": "Identify the integrand", "description": "Parse the mathematical expression to integrate."},
                {"step": 2, "title": "Choose integration technique", "description": "Determine the best method: direct integration, substitution, integration by parts, or partial fractions."},
                {"step": 3, "title": "Apply the integration method", "description": "Carry out the chosen integration technique step by step."},
                {"step": 4, "title": "Add the constant of integration", "description": "Include + C for indefinite integrals."},
                {"step": 5, "title": "State the final answer", "description": "Present the antiderivative in simplified form."},
            ],
            "definite_integral": [
                {"step": 1, "title": "Identify the integrand and limits", "description": "Parse the function and the bounds of integration."},
                {"step": 2, "title": "Find the antiderivative", "description": "Compute the indefinite integral of the function."},
                {"step": 3, "title": "Apply the Fundamental Theorem", "description": "Evaluate F(b) - F(a) using the upper and lower limits."},
                {"step": 4, "title": "Compute the numerical result", "description": "Calculate the final numeric value."},
                {"step": 5, "title": "State the final answer", "description": "Present the value of the definite integral."},
            ],
            "limit": [
                {"step": 1, "title": "Identify the expression and point", "description": "Determine the function and the value x approaches."},
                {"step": 2, "title": "Check direct substitution", "description": "Try substituting the limit point directly into the expression."},
                {"step": 3, "title": "Handle indeterminate forms", "description": "If direct substitution gives 0/0 or ∞/∞, apply L'Hôpital's Rule or algebraic manipulation."},
                {"step": 4, "title": "Evaluate the limit", "description": "Compute the final limit value."},
                {"step": 5, "title": "State the final answer", "description": "Present the limit result."},
            ],
            "equation": [
                {"step": 1, "title": "Identify the equation type", "description": "Classify as linear, quadratic, polynomial, or transcendental equation."},
                {"step": 2, "title": "Choose the solving method", "description": "Select the appropriate technique: factoring, quadratic formula, or algebraic manipulation."},
                {"step": 3, "title": "Solve the equation", "description": "Apply the chosen method to find the solution(s)."},
                {"step": 4, "title": "Verify the solution(s)", "description": "Substitute back to confirm each solution satisfies the original equation."},
                {"step": 5, "title": "State the final answer", "description": "Present all valid solutions."},
            ],
            "system_of_equations": [
                {"step": 1, "title": "Identify the system", "description": "Write out all equations and identify the unknowns."},
                {"step": 2, "title": "Choose a method", "description": "Select substitution, elimination, or matrix method."},
                {"step": 3, "title": "Solve the system", "description": "Apply the chosen method to find the values of all unknowns."},
                {"step": 4, "title": "Verify the solution", "description": "Substitute the solution back into all original equations."},
                {"step": 5, "title": "State the final answer", "description": "Present the complete solution set."},
            ],
            "simplification": [
                {"step": 1, "title": "Identify the expression", "description": "Parse the mathematical expression to simplify."},
                {"step": 2, "title": "Apply algebraic identities", "description": "Use relevant identities and rules to transform the expression."},
                {"step": 3, "title": "Combine and reduce", "description": "Combine like terms and cancel common factors."},
                {"step": 4, "title": "State the final answer", "description": "Present the simplified expression."},
            ],
            "factoring": [
                {"step": 1, "title": "Identify the polynomial", "description": "Parse the expression to be factored."},
                {"step": 2, "title": "Look for common factors", "description": "Extract the greatest common factor if one exists."},
                {"step": 3, "title": "Apply factoring technique", "description": "Use grouping, difference of squares, sum/difference of cubes, or trial factors."},
                {"step": 4, "title": "Verify by expansion", "description": "Multiply the factors back to confirm they produce the original expression."},
                {"step": 5, "title": "State the final answer", "description": "Present the fully factored form."},
            ],
            "trigonometry": [
                {"step": 1, "title": "Identify the trigonometric problem", "description": "Determine whether this involves identities, equations, or simplification."},
                {"step": 2, "title": "Select relevant identities", "description": "Choose the appropriate trigonometric identities or formulas."},
                {"step": 3, "title": "Apply transformations", "description": "Use the identities to transform or solve the expression."},
                {"step": 4, "title": "Simplify the result", "description": "Reduce the expression to its simplest form."},
                {"step": 5, "title": "State the final answer", "description": "Present the final result."},
            ],
        }

        return plans.get(math_type, [
            {"step": 1, "title": "Understand the problem", "description": "Parse and interpret the mathematical query."},
            {"step": 2, "title": "Identify the approach", "description": "Determine the mathematical method or formula needed."},
            {"step": 3, "title": "Execute the computation", "description": "Apply the method step by step."},
            {"step": 4, "title": "Simplify the result", "description": "Reduce the answer to its simplest form."},
            {"step": 5, "title": "State the final answer", "description": "Present the computed result clearly."},
        ])


# Singleton
reasoning_agent = ReasoningAgent()
