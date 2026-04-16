"""Query preprocessing — normalizes math expressions from natural language.

Converts user input like "integrate x^2 + 3x" into a clean mathematical
expression ("x**2 + 3*x") and extracts variables, bounds, etc.
"""

import re
import logging

logger = logging.getLogger(__name__)


# ── Keyword phrases to strip (order matters — longer first) ──────────────
_STRIP_PHRASES = [
    # Calculus
    "find the second derivative of",
    "find the derivative of",
    "find the integral of",
    "find the antiderivative of",
    "find the limit of",
    "take the derivative of",
    "take the integral of",
    "compute the derivative of",
    "compute the integral of",
    "compute the limit of",
    "calculate the derivative of",
    "calculate the integral of",
    "calculate the limit of",
    "what is the derivative of",
    "what is the integral of",
    "what is the limit of",
    "differentiate",
    "integrate",
    "evaluate the integral",
    "evaluate the limit",
    "evaluate",
    "d/dx",
    "dy/dx",
    # Algebra
    "solve the equation",
    "solve the system of equations",
    "solve for x",
    "solve for y",
    "solve",
    "factor",
    "expand",
    "simplify",
    "find the roots of",
    "find the zeros of",
    "find the value of",
    "find",
    "calculate",
    "compute",
    "what is",
    "determine",
]

# ── LaTeX → Python math replacements ────────────────────────────────────
_LATEX_REPLACEMENTS = [
    (r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))"),  # \frac{a}{b}
    (r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)"),                   # \sqrt{x}
    (r"\\cdot", "*"),
    (r"\\times", "*"),
    (r"\\div", "/"),
    (r"\\pi", " pi "),
    (r"\\infty", " oo "),
    (r"\\sin", " sin"),
    (r"\\cos", " cos"),
    (r"\\tan", " tan"),
    (r"\\sec", " sec"),
    (r"\\csc", " csc"),
    (r"\\cot", " cot"),
    (r"\\arcsin", " asin"),
    (r"\\arccos", " acos"),
    (r"\\arctan", " atan"),
    (r"\\ln", " log"),
    (r"\\log", " log"),
    (r"\\exp", " exp"),
    (r"\\left", ""),
    (r"\\right", ""),
    (r"\\,", " "),
    (r"\\ ", " "),
]


def preprocess_query(query: str) -> str:
    """Normalize a math query: strip noise, convert LaTeX, fix operators.

    Args:
        query: Raw user question (e.g. "integrate x^2 + 3x from 0 to 1").

    Returns:
        Cleaned expression string ready for SymPy parsing.
    """
    text = query.strip()

    # Remove dollar-sign math delimiters
    text = re.sub(r"\$\$?", "", text)

    # Remove \\boxed{...}
    text = re.sub(r"\\boxed\{(.+?)\}", r"\1", text)
    text = re.sub(r"\\text\{[^}]*\}", "", text)

    # Apply LaTeX → Python replacements
    for pattern, repl in _LATEX_REPLACEMENTS:
        text = re.sub(pattern, repl, text)

    # Replace ^ with **
    text = text.replace("^", "**")

    # Remove remaining backslashes
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("\\", "")

    # Strip stray whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_math_expression(query: str) -> dict:
    """Extract the core math expression plus metadata from a natural-language query.

    Returns a dict with:
        ``expr``       – the main mathematical expression string
        ``variable``   – primary variable (default ``"x"``)
        ``bounds``     – tuple (lower, upper) for definite integrals, or None
        ``point``      – limit point, or None
        ``lhs`` / ``rhs`` – for equations with ``=``
    """
    text = preprocess_query(query)
    query_lower = query.lower()

    result = {
        "expr": "",
        "variable": "x",
        "bounds": None,
        "point": None,
        "lhs": None,
        "rhs": None,
        "original": query,
    }

    # ── Detect variable ──────────────────────────────────────────────────
    var_match = re.search(r"with respect to\s+(\w)", query_lower)
    if var_match:
        result["variable"] = var_match.group(1)
        text = re.sub(r"with respect to\s+\w", "", text, flags=re.IGNORECASE)

    # ── Detect definite integral bounds ──────────────────────────────────
    bounds_match = re.search(
        r"from\s+([\w\d./*+\-() pioo]+)\s+to\s+([\w\d./*+\-() pioo]+)",
        text, re.IGNORECASE,
    )
    if bounds_match:
        result["bounds"] = (bounds_match.group(1).strip(), bounds_match.group(2).strip())
        text = text[:bounds_match.start()] + text[bounds_match.end():]

    # ── Detect limit point ───────────────────────────────────────────────
    limit_patterns = [
        r"as\s+\w\s*(?:→|->|approaches|tends to)\s*([\w\d./*+\-() pioo∞infinity]+)",
        r"(?:→|->)\s*([\w\d./*+\-() pioo∞infinity]+)",
        r"x\s*approaches\s*([\w\d./*+\-() pioo∞infinity]+)",
    ]
    for pat in limit_patterns:
        lim_match = re.search(pat, text, re.IGNORECASE)
        if lim_match:
            pt = lim_match.group(1).strip()
            # Normalize infinity tokens
            if pt.lower() in ("infinity", "inf", "∞"):
                pt = "oo"
            elif pt.lower() in ("-infinity", "-inf", "-∞"):
                pt = "-oo"
            result["point"] = pt
            text = text[:lim_match.start()] + text[lim_match.end():]
            break

    # ── Strip instructional phrases ──────────────────────────────────────
    text_lower = text.lower()
    for phrase in _STRIP_PHRASES:
        idx = text_lower.find(phrase)
        if idx != -1:
            text = text[idx + len(phrase):]
            text_lower = text.lower()

    # Clean up
    text = text.strip().strip(":").strip()
    text = re.sub(r"\s+", " ", text).strip()

    # ── Handle equations (contains "=") ──────────────────────────────────
    if "=" in text:
        parts = text.split("=", 1)
        if len(parts) == 2:
            result["lhs"] = parts[0].strip()
            result["rhs"] = parts[1].strip()
            # For solve: move everything to one side
            if result["rhs"] and result["rhs"] != "0":
                result["expr"] = f"({parts[0].strip()}) - ({parts[1].strip()})"
            else:
                result["expr"] = parts[0].strip()
    else:
        result["expr"] = text

    # ── Handle system of equations ───────────────────────────────────────
    if "," in result["expr"] and any(
        kw in query_lower for kw in ["system", "simultaneously", "equations:"]
    ):
        eqs = [eq.strip() for eq in result["expr"].split(",") if eq.strip()]
        result["equations"] = eqs

    # ── Fix implicit multiplication (e.g. "3x" → "3*x") ────────────────
    result["expr"] = _add_implicit_multiplication(result["expr"])

    logger.debug("Extracted expression: %s", result)
    return result


def _add_implicit_multiplication(expr: str) -> str:
    """Insert * between digit-letter boundaries (e.g. '3x' → '3*x')."""
    # Don't touch function names like sin, cos, log, etc.
    # digit followed by letter (but not part of 'pi', 'exp', etc.)
    expr = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", expr)
    # closing paren followed by opening paren or variable
    expr = re.sub(r"\)(\()", r")*(", expr)
    expr = re.sub(r"\)([a-zA-Z])", r")*\1", expr)
    # variable followed by opening paren (but preserve function calls)
    # This is handled by SymPy's implicit_multiplication_application
    return expr
