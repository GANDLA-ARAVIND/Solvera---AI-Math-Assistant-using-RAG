"""Math problem type detection — classifies questions into solvable categories.

Detects: derivative, integration, definite_integral, limit, equation, system_of_equations,
simplification, expansion, factoring, trigonometry, second_derivative, evaluation.
"""

import re
import logging

logger = logging.getLogger(__name__)


# ── Detection rules: (type_name, keywords, patterns) ─────────────────────
# Order matters — more specific types should come first.
_DETECTION_RULES: list[tuple[str, list[str], list[str]]] = [
    # Definite integral (must check before generic integral)
    (
        "definite_integral",
        [],
        [
            r"(?:integral|integrate).*?from\s+.+?\s+to\s+",
            r"∫.*?(?:from|to)",
            r"definite\s+integral",
            r"integral\s+of\s+.+?\s+from\s+",
        ],
    ),
    # Second derivative (before generic derivative)
    (
        "second_derivative",
        ["second derivative", "d²/dx²", "d2/dx2", "f''(x)", "f''"],
        [
            r"second\s+derivative",
            r"d\s*²\s*/\s*dx\s*²",
            r"d2\s*/\s*dx2",
        ],
    ),
    # Derivative
    (
        "derivative",
        [
            "derivative", "differentiate", "d/dx", "dy/dx",
            "differentiation", "diff",
        ],
        [
            r"\bd/d[a-z]\b",
            r"\bdy/dx\b",
            r"(?:find|compute|calculate|take|what is).*?derivative",
        ],
    ),
    # Integration (indefinite)
    (
        "integration",
        [
            "integrate", "integral", "antiderivative",
            "integration", "∫",
        ],
        [
            r"∫\s*",
            r"(?:find|compute|calculate).*?(?:integral|antiderivative)",
        ],
    ),
    # Limit
    (
        "limit",
        ["limit", "lim", "approaches", "tends to"],
        [
            r"\blim\b",
            r"as\s+x\s*(?:→|->|approaches|tends\s+to)",
            r"limit\s+(?:of|as)",
        ],
    ),
    # System of equations
    (
        "system_of_equations",
        ["system of equations", "simultaneously", "simultaneous"],
        [
            r"system\s+of\s+equations",
            r"solve.*?(?:and|,)\s*\w+\s*[+\-*/]\s*\w+\s*=",
        ],
    ),
    # Equation solving
    (
        "equation",
        ["solve", "find x", "find the roots", "find the zeros", "roots of"],
        [
            r"solve\s+(?:for\s+)?[a-z]?\s*(?:in|:)?\s*",
            r"find\s+(?:the\s+)?(?:roots?|zeros?|solutions?|value)",
            r"[a-z]\s*=\s*0",
        ],
    ),
    # Factoring
    (
        "factoring",
        ["factor", "factorize", "factorise"],
        [r"\bfactor(?:ize|ise)?\b"],
    ),
    # Expansion
    (
        "expansion",
        ["expand", "expansion"],
        [r"\bexpand\b"],
    ),
    # Simplification
    (
        "simplification",
        ["simplify", "simplification", "reduce"],
        [r"\bsimplify\b", r"\breduce\b"],
    ),
    # Trigonometry (catch-all for trig problems not caught above)
    (
        "trigonometry",
        [
            "sin", "cos", "tan", "sec", "csc", "cot",
            "trigonometric", "trig identity", "trig",
        ],
        [
            r"\b(?:sin|cos|tan|sec|csc|cot)\s*\(",
            r"(?:prove|verify|show)\s+(?:that\s+)?.*?(?:sin|cos|tan)",
            r"trig(?:onometric)?\s+(?:identity|equation)",
        ],
    ),
    # Evaluation (numeric computation)
    (
        "evaluation",
        ["evaluate", "calculate", "compute", "what is"],
        [
            r"\bevaluate\b",
            r"\bcalculate\b",
            r"what\s+is\s+\d",
        ],
    ),
]


def detect_math_type(question: str) -> dict:
    """Detect the type of math problem from a natural-language question.

    Args:
        question: The user's raw math question.

    Returns:
        A dict with keys:
            ``type``       – one of the category strings (e.g. "derivative")
            ``confidence`` – float 0-1
            ``details``    – human-readable reason
    """
    q_lower = question.lower().strip()

    for type_name, keywords, patterns in _DETECTION_RULES:
        # Check keywords
        kw_hits = sum(1 for kw in keywords if kw in q_lower)

        # Check regex patterns
        pat_hits = sum(
            1 for pat in patterns if re.search(pat, q_lower, re.IGNORECASE)
        )

        total_hits = kw_hits + pat_hits

        if total_hits >= 1:
            confidence = min(0.95, 0.6 + 0.15 * total_hits)
            logger.debug(
                "Detected math type '%s' (confidence %.2f, hits=%d)",
                type_name, confidence, total_hits,
            )
            return {
                "type": type_name,
                "confidence": confidence,
                "details": f"Matched {kw_hits} keyword(s) + {pat_hits} pattern(s)",
            }

    # ── Fallback heuristics ──────────────────────────────────────────────
    # Contains "=" → likely an equation
    if "=" in question:
        return {
            "type": "equation",
            "confidence": 0.5,
            "details": "Contains '=' sign (heuristic)",
        }

    # Contains math operators → evaluation
    if re.search(r"\d\s*[+\-*/]\s*\d", question):
        return {
            "type": "evaluation",
            "confidence": 0.4,
            "details": "Arithmetic expression detected (heuristic)",
        }

    return {
        "type": "unknown",
        "confidence": 0.0,
        "details": "Could not determine math type",
    }
