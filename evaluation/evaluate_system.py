"""
Solvera Evaluation System  (v2 — improved answer matching)
==========================================================
Evaluates the AI math solver against a dataset of known questions and answers.

Usage:
    python evaluation/evaluate_system.py

Pipeline:
  1. Loads test_dataset.json
  2. Sends each question to the Solvera solver pipeline
  3. Compares predicted answers with expected answers using a **multi-layer**
     SymPy comparison pipeline (normalize → symbolic → ratio → numeric)
  4. Computes Accuracy, Precision, Recall, F1 Score, and response times
  5. Saves per-question results to results.csv
  6. Prints a detailed summary table to the terminal

Key comparison functions (modular):
  normalize_expression(expr_str)   — clean LaTeX / formatting → SymPy expr
  symbolic_compare(pred, actual)   — simplify(pred - actual) == 0
  numeric_compare(pred, actual)    — evaluate at random points, tolerance 1e-5
  evaluate_answer(pred, actual, topic) — orchestrate all checks
"""

import asyncio
import csv
import json
import logging
import math
import os
import random
import re
import sys
import time

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("solvera_eval")

# ---------------------------------------------------------------------------
# Path setup — allow running from project root:  python evaluation/evaluate_system.py
# ---------------------------------------------------------------------------
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EVAL_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

# Add backend to sys.path so we can import app.*
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Change working directory to backend so relative paths (.env, faiss_index, etc.) resolve
os.chdir(BACKEND_DIR)

# ---------------------------------------------------------------------------
# Import Solvera internals (after path setup)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.services.solver_service import solver_service
from app.services.rag_service import rag_service

# SymPy imports for answer comparison
import sympy
from sympy import (
    simplify, sympify, symbols, oo, pi, E, I, N,
    sin, cos, tan, sec, csc, cot,
    asin, acos, atan,
    sqrt, exp, log, ln, Abs, Rational,
    expand, factor, trigsimp, cancel,
    Symbol, Number,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,          # lets ^ mean **
)

# Local dictionary for parse_expr — ensures known math functions are recognized
# instead of being treated as variable names by implicit_multiplication.
_x, _y, _z = symbols('x y z')
_a, _b, _n = symbols('a b n')
LOCAL_DICT = {
    'sin': sin, 'cos': cos, 'tan': tan, 'sec': sec, 'csc': csc, 'cot': cot,
    'asin': asin, 'acos': acos, 'atan': atan,
    'log': log, 'ln': ln, 'exp': exp, 'sqrt': sqrt, 'Abs': Abs,
    'pi': pi, 'E': E, 'oo': oo, 'I': I,
    'x': _x, 'y': _y, 'z': _z,
    'a': _a, 'b': _b, 'n': _n,
}

# Tolerance for numeric comparison
NUMERIC_TOLERANCE = 1e-5
# Number of random test points for numeric fallback
NUM_TEST_POINTS = 8

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
DATASET_PATH = os.path.join(EVAL_DIR, "test_dataset.json")
RESULTS_CSV_PATH = os.path.join(EVAL_DIR, "results.csv")


# ═══════════════════════════════════════════════════════════════════════════
#  1. normalize_expression(expr_str) → SymPy expression | None
# ═══════════════════════════════════════════════════════════════════════════

def normalize_expression(expr_str: str):
    """
    Clean a raw answer string and convert it to a SymPy expression.

    Steps:
      - Strip whitespace
      - Remove LaTeX wrappers ($, \\boxed, \\text, etc.)
      - Replace ^ with **
      - Remove trailing '+ C' (integration constant)
      - Convert LaTeX commands (\\frac, \\sqrt, trig names) to SymPy equivalents
      - Parse with sympify / parse_expr
    Returns a SymPy expression or None on failure.
    """
    if not expr_str or not expr_str.strip():
        return None

    text = str(expr_str).strip()

    # ── Remove markdown / display math decorators ─────────────────────────
    # Remove markdown headers (## ) and bold (**text**) but preserve arithmetic *
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)  # headers
    text = re.sub(r"(?<![a-zA-Z0-9)\]])\*\*(.+?)\*\*", r"\1", text)  # **bold** (not x**2)
    text = re.sub(r"`([^`]*)`", r"\1", text)                     # `code`
    text = re.sub(r"\$\$?", "", text)

    # ── Remove \\boxed{...} ───────────────────────────────────────────────
    text = re.sub(r"\\boxed\{(.+?)\}", r"\1", text)

    # ── Remove \\text{...} ────────────────────────────────────────────────
    text = re.sub(r"\\text\{[^}]*\}", "", text)

    # ── LaTeX fractions:  \\frac{a}{b} → ((a)/(b)) ───────────────────────
    # Repeat for nested fractions
    for _ in range(5):
        new = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", text)
        if new == text:
            break
        text = new

    # ── LaTeX sqrt ────────────────────────────────────────────────────────
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", text)

    # ── Common LaTeX → Python/SymPy tokens ────────────────────────────────
    latex_map = {
        "\\cdot": "*", "\\times": "*", "\\div": "/",
        "\\pi": " pi ", "\\infty": " oo ",
        "\\sin": " sin", "\\cos": " cos", "\\tan": " tan",
        "\\sec": " sec", "\\csc": " csc", "\\cot": " cot",
        "\\arcsin": " asin", "\\arccos": " acos", "\\arctan": " atan",
        "\\ln": " log", "\\log": " log",
        "\\exp": " exp",
        "\\left": "", "\\right": "",
        "\\,": " ", "\\ ": " ",
        "\\": "",
    }
    for latex_cmd, replacement in latex_map.items():
        text = text.replace(latex_cmd, replacement)

    # ── Replace ^ with ** ─────────────────────────────────────────────────
    text = text.replace("^", "**")

    # ── Remove integration constant  + C  or  + c  at end ────────────────
    text = re.sub(r"\+\s*[Cc]\s*$", "", text)
    text = re.sub(r"\+\s*[Cc]\s*(?=[,\]\)])", "", text)    # inside lists

    # ── Remove "where C is …" trailing text ──────────────────────────────
    text = re.sub(r"(?:,?\s*where\s+.*$)", "", text, flags=re.IGNORECASE)

    # ── Clean stray whitespace ────────────────────────────────────────────
    text = text.strip()
    if not text:
        return None

    # ── Try parsing ───────────────────────────────────────────────────────
    for parser in [_try_parse_expr, _try_sympify]:
        result = parser(text)
        if result is not None:
            return result

    return None


def _try_parse_expr(text: str):
    """Parse with parse_expr (more lenient, handles implicit multiplication)."""
    try:
        return parse_expr(text, transformations=TRANSFORMATIONS, local_dict=LOCAL_DICT)
    except Exception:
        pass
    # Retry without local_dict in case of symbol clashes
    try:
        return parse_expr(text, transformations=TRANSFORMATIONS)
    except Exception:
        return None


def _try_sympify(text: str):
    """Parse with sympify (stricter, but handles some forms parse_expr doesn't)."""
    try:
        return sympify(text, locals=LOCAL_DICT)
    except Exception:
        pass
    try:
        return sympify(text)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  2. symbolic_compare(pred_expr, actual_expr) → bool
# ═══════════════════════════════════════════════════════════════════════════

def symbolic_compare(pred_expr, actual_expr) -> bool:
    """
    Compare two SymPy expressions symbolically.

    Checks (in order):
      1. simplify(pred - actual) == 0
      2. expand(pred) == expand(actual)
      3. factor(pred) == factor(actual)
      4. trigsimp(pred - actual) == 0
      5. simplify(pred / actual) == 1  (ratio test — catches scalar multiples)
      6. cancel(pred - actual) == 0
    """
    if pred_expr is None or actual_expr is None:
        return False

    # If both are numbers, just compare
    if pred_expr.is_number and actual_expr.is_number:
        try:
            return bool(simplify(pred_expr - actual_expr) == 0)
        except Exception:
            pass
        try:
            diff = abs(complex(N(pred_expr)) - complex(N(actual_expr)))
            return diff < NUMERIC_TOLERANCE
        except Exception:
            return False

    # ── Check 1: simplify(diff) == 0 ─────────────────────────────────────
    try:
        diff = simplify(pred_expr - actual_expr)
        if diff == 0:
            return True
    except Exception:
        pass

    # ── Check 2: expand both sides ────────────────────────────────────────
    try:
        if expand(pred_expr) == expand(actual_expr):
            return True
    except Exception:
        pass

    # ── Check 3: factor both sides ────────────────────────────────────────
    try:
        if factor(pred_expr) == factor(actual_expr):
            return True
    except Exception:
        pass

    # ── Check 4: trigsimp (trig identities) ───────────────────────────────
    try:
        if trigsimp(pred_expr - actual_expr) == 0:
            return True
    except Exception:
        pass

    # ── Check 4b: trigsimp each side individually then compare ────────────
    try:
        ts_pred = trigsimp(pred_expr)
        ts_actual = trigsimp(actual_expr)
        if ts_pred == ts_actual:
            return True
        if simplify(ts_pred - ts_actual) == 0:
            return True
    except Exception:
        pass

    # ── Check 4c: expand_trig + simplify ──────────────────────────────────
    try:
        from sympy import expand_trig
        et_pred = expand_trig(pred_expr)
        et_actual = expand_trig(actual_expr)
        if simplify(et_pred - et_actual) == 0:
            return True
    except Exception:
        pass

    # ── Check 5: ratio test  simplify(pred/actual) == 1 ──────────────────
    try:
        if actual_expr != 0:
            ratio = simplify(pred_expr / actual_expr)
            if ratio == 1:
                return True
    except Exception:
        pass

    # ── Check 6: cancel ──────────────────────────────────────────────────
    try:
        if cancel(pred_expr - actual_expr) == 0:
            return True
    except Exception:
        pass

    return False


# ═══════════════════════════════════════════════════════════════════════════
#  3. numeric_compare(pred_expr, actual_expr) → bool
# ═══════════════════════════════════════════════════════════════════════════

def numeric_compare(pred_expr, actual_expr, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    """
    Numeric fallback: substitute random values for all free variables in both
    expressions and check whether the results are approximately equal.

    Uses NUM_TEST_POINTS random test points.  If ALL points agree within
    *tolerance*, returns True.
    """
    if pred_expr is None or actual_expr is None:
        return False

    # Gather free symbols from both expressions
    try:
        free_syms = sorted(
            pred_expr.free_symbols | actual_expr.free_symbols,
            key=lambda s: s.name,
        )
    except Exception:
        return False

    if not free_syms:
        # No variables — just evaluate directly
        try:
            pv = complex(N(pred_expr))
            av = complex(N(actual_expr))
            return abs(pv - av) < tolerance
        except Exception:
            return False

    # Generate several random substitution dicts
    random.seed(42)  # reproducibility
    test_points = []
    # Mix of positive, negative, fractional values (avoid 0 & near-singularities)
    candidate_values = [0.5, 1.0, 1.5, 2.0, -1.0, -0.5, 0.7, 1.3, -1.7, 2.5, 0.3, 3.0]
    for _ in range(NUM_TEST_POINTS):
        subs = {s: random.choice(candidate_values) for s in free_syms}
        test_points.append(subs)

    matches = 0
    evaluated = 0
    for subs in test_points:
        try:
            pv = complex(pred_expr.subs(subs).evalf())
            av = complex(actual_expr.subs(subs).evalf())
            # Skip if either is nan/inf
            if math.isnan(pv.real) or math.isinf(pv.real):
                continue
            if math.isnan(av.real) or math.isinf(av.real):
                continue
            evaluated += 1
            if abs(pv - av) < tolerance:
                matches += 1
        except Exception:
            continue

    # Need at least 3 valid points, all matching
    return evaluated >= 3 and matches == evaluated


# ═══════════════════════════════════════════════════════════════════════════
#  4. evaluate_answer(predicted_str, actual_str, topic) → bool
#     Orchestrates all comparison strategies
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_answer(predicted_str: str, actual_str: str, topic: str = "general") -> bool:
    """
    Master comparison function.  Tries every strategy in order:

    1. Normalized string equality
    2. List / set comparison (for equation solutions)
    3. Dict comparison (for systems of equations)
    4. symbolic_compare on normalized expressions
    5. symbolic_compare after stripping +C  (integrals)
    6. numeric_compare (random-point evaluation)
    7. Substring / containment heuristics for multiple solutions
    """
    if not predicted_str or not actual_str:
        return False

    # ── Step 0: raw string normalization ──────────────────────────────────
    pred_raw = _normalize_string(predicted_str)
    actual_raw = _normalize_string(actual_str)

    if pred_raw == actual_raw:
        return True

    # ── Step 1: list / set comparison  [2, 3] ─────────────────────────────
    list_result = _compare_as_lists(pred_raw, actual_raw)
    if list_result is not None:
        return list_result

    # ── Step 2: dict comparison  {x: 7, y: 3} ────────────────────────────
    dict_result = _compare_as_dicts(pred_raw, actual_raw)
    if dict_result is not None:
        return dict_result

    # ── Step 3: symbolic comparison ───────────────────────────────────────
    pred_expr = normalize_expression(predicted_str)
    actual_expr = normalize_expression(actual_str)

    if symbolic_compare(pred_expr, actual_expr):
        return True

    # ── Step 4: integral — try stripping +C from predicted ────────────────
    if topic in ("integrals", "calculus"):
        pred_no_c = re.sub(r"\+\s*[Cc]\b", "", predicted_str)
        pred_expr_no_c = normalize_expression(pred_no_c)
        if symbolic_compare(pred_expr_no_c, actual_expr):
            return True
        # Also try: if difference is a constant (derivative check)
        if pred_expr is not None and actual_expr is not None:
            try:
                free = (pred_expr - actual_expr).free_symbols
                diff_simplified = simplify(pred_expr - actual_expr)
                if not diff_simplified.free_symbols:
                    # Difference is a constant → equivalent up to +C
                    return True
            except Exception:
                pass

    # ── Step 5: derivative equivalence — extra trig / simplify ────────────
    if topic == "derivatives":
        if pred_expr is not None and actual_expr is not None:
            try:
                # cos(2x) == -sin²(x) + cos²(x) etc.
                diff = trigsimp(expand(pred_expr) - expand(actual_expr))
                if diff == 0:
                    return True
            except Exception:
                pass

    # ── Step 6: numeric comparison (multi-point random evaluation) ────────
    if numeric_compare(pred_expr, actual_expr):
        return True

    # ── Step 7: "or" / multiple-answer heuristic ──────────────────────────
    #    e.g. predicted = "x = 2 or x = -2"  |  actual = "[2, -2]"
    or_result = _compare_multiple_solutions(predicted_str, actual_str)
    if or_result is not None:
        return or_result

    return False


# ═══════════════════════════════════════════════════════════════════════════
#  Internal helpers for evaluate_answer
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_string(text: str) -> str:
    """Minimal string normalization for quick equality check."""
    t = text.strip().lower()
    t = re.sub(r"\s+", "", t)
    t = t.replace("^", "**")
    t = re.sub(r"\+\s*[Cc]$", "", t)
    return t


def _compare_as_lists(pred_raw: str, actual_raw: str):
    """Compare two answers that may be lists like [2,3]. Returns bool or None."""
    # Check if either looks like a list
    is_pred_list = pred_raw.startswith("[") or pred_raw.startswith("(")
    is_actual_list = actual_raw.startswith("[") or actual_raw.startswith("(")

    if not is_actual_list and not is_pred_list:
        return None  # not lists — skip

    pred_items = _parse_list_items(pred_raw)
    actual_items = _parse_list_items(actual_raw)

    if pred_items is None or actual_items is None:
        return None  # couldn't parse — skip

    if len(pred_items) != len(actual_items):
        return False

    # Check if every actual item has a matching predicted item (set equality)
    matched = set()
    for a in actual_items:
        found = False
        for i, p in enumerate(pred_items):
            if i in matched:
                continue
            if symbolic_compare(p, a) or numeric_compare(p, a):
                matched.add(i)
                found = True
                break
        if not found:
            return False
    return True


def _parse_list_items(s: str):
    """Parse "[2, 3]" or "2, 3" into a list of SymPy expressions."""
    s = s.strip().strip("[]() ")
    if not s:
        return None
    parts = [p.strip() for p in s.split(",") if p.strip()]
    exprs = []
    for p in parts:
        e = normalize_expression(p)
        if e is None:
            return None
        exprs.append(e)
    return exprs


def _compare_as_dicts(pred_raw: str, actual_raw: str):
    """Compare dict-style solutions like {x: 7, y: 3}. Returns bool or None."""
    pred_dict = _parse_dict_answer(pred_raw)
    actual_dict = _parse_dict_answer(actual_raw)
    if pred_dict is None or actual_dict is None:
        return None
    if set(pred_dict.keys()) != set(actual_dict.keys()):
        return False
    for key in actual_dict:
        if key not in pred_dict:
            return False
        if not symbolic_compare(pred_dict[key], actual_dict[key]):
            if not numeric_compare(pred_dict[key], actual_dict[key]):
                return False
    return True


def _parse_dict_answer(s: str):
    """Parse '{x: 7, y: 3}' into a dict of {str: SymPy expr}."""
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    pairs = re.findall(r"(\w+)\s*:\s*([^,}]+)", s)
    if not pairs:
        return None
    result = {}
    for var, val in pairs:
        expr = normalize_expression(val.strip())
        if expr is None:
            return None
        result[var] = expr
    return result


def _compare_multiple_solutions(predicted_str: str, actual_str: str):
    """
    Handle 'x = 2 or x = -2' vs '[2, -2]' style answers.
    Returns bool or None.
    """
    # Extract values after "=" separated by "or" / "and" / ","
    or_vals = re.findall(
        r"(?:=\s*)([-\d./]+(?:\*\*\d+)?)", predicted_str
    )
    if len(or_vals) >= 2:
        pred_items = []
        for v in or_vals:
            e = normalize_expression(v)
            if e is not None:
                pred_items.append(e)
        actual_items = _parse_list_items(actual_str.strip())
        if pred_items and actual_items and len(pred_items) == len(actual_items):
            matched = set()
            for a in actual_items:
                for i, p in enumerate(pred_items):
                    if i not in matched and symbolic_compare(p, a):
                        matched.add(i)
                        break
            if len(matched) == len(actual_items):
                return True
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Answer extraction from LLM solution text (improved)
# ═══════════════════════════════════════════════════════════════════════════

def _clean_answer_text(text: str) -> str:
    """Strip LaTeX wrappers, dollar signs, and common decorators."""
    if not text:
        return ""
    # Remove markdown headers/bold carefully, preserving arithmetic *
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<![a-zA-Z0-9)\]])\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\$\$?", "", text)
    text = re.sub(r"\\boxed\{(.+?)\}", r"\1", text)
    text = re.sub(r"\\text\{[^}]*\}", "", text)
    for _ in range(5):
        new = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", text)
        if new == text:
            break
        text = new
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", text)
    replacements = {
        "\\cdot": "*", "\\times": "*", "\\div": "/",
        "\\pi": "pi", "\\infty": "oo",
        "\\sin": "sin", "\\cos": "cos", "\\tan": "tan",
        "\\ln": "log", "\\log": "log",
        "\\exp": "exp", "\\e": "E",
        "\\left": "", "\\right": "",
        "\\,": "", "\\ ": "",
        "\\": "",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = text.replace("^", "**")
    return text.strip()


def extract_answer_from_solution(solution_text: str) -> str:
    """
    Try multiple strategies to pull the final answer from an LLM solution.
    Returns a cleaned string suitable for normalize_expression().
    """
    if not solution_text:
        return ""

    candidates = []

    # Strategy 1: ## Final Answer section
    match = re.search(
        r"(?:##\s*Final\s*Answer|Final\s*Answer|FINAL\s*ANSWER)[:\s]*\$?\$?(.*?)\$?\$?\s*(?:##|$)",
        solution_text, re.IGNORECASE | re.DOTALL,
    )
    if match:
        candidates.append(match.group(1).strip())

    # Strategy 2: \\boxed{...}
    boxed = re.findall(r"\\boxed\{(.+?)\}", solution_text)
    if boxed:
        candidates.append(boxed[-1].strip())  # last boxed is usually the answer

    # Strategy 3: "answer is …" / "result is …" / "therefore …" / "equals …"
    for pattern in [
        r"(?:the\s+)?(?:answer|result|solution|integral|derivative)\s+is[:\s]*\$?\$?(.*?)\$?\$?\s*$",
        r"(?:therefore|thus|hence|so)[,:\s]*\$?\$?(.*?)\$?\$?\s*$",
        r"=\s*\$?\$?(.*?)\$?\$?\s*$",
    ]:
        m = re.search(pattern, solution_text, re.IGNORECASE | re.MULTILINE)
        if m:
            val = m.group(1).strip()
            if val and len(val) < 200:
                candidates.append(val)

    # Strategy 4: last display-math block  $$ ... $$
    display_blocks = re.findall(r"\$\$(.*?)\$\$", solution_text, re.DOTALL)
    if display_blocks:
        candidates.append(display_blocks[-1].strip())

    # Strategy 5: last non-empty line
    lines = [l.strip() for l in solution_text.strip().split("\n") if l.strip()]
    if lines:
        candidates.append(lines[-1])

    # Clean all candidates and return the first one that normalizes successfully
    for raw in candidates:
        cleaned = _clean_answer_text(raw)
        if cleaned and normalize_expression(cleaned) is not None:
            return cleaned

    # Fall back to first non-empty candidate
    for raw in candidates:
        cleaned = _clean_answer_text(raw)
        if cleaned:
            return cleaned

    return ""


# ═══════════════════════════════════════════════════════════════════════════
# Evaluation runner
# ═══════════════════════════════════════════════════════════════════════════

async def evaluate():
    """Run the full evaluation pipeline."""

    # --- Initialize RAG service (required by solver) ---
    logger.info("Initializing RAG service …")
    rag_service.initialize()
    if rag_service.is_ready():
        logger.info("RAG service is ready.\n")
    else:
        logger.info("WARNING: RAG service not ready — results may be degraded.\n")

    # --- Load dataset ---
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total = len(dataset)
    correct = 0
    incorrect = 0
    response_times: list[float] = []
    csv_rows: list[dict] = []

    logger.info(f"{'='*70}")
    logger.info(f"  Solvera Evaluation (v2) — {total} questions")
    logger.info(f"{'='*70}\n")

    for idx, item in enumerate(dataset, start=1):
        question = item["question"]
        expected_answer = item["answer"]
        alternate_answers = item.get("alternates", [])  # optional equivalent forms
        topic = item.get("topic", "general")

        logger.info(f"[{idx}/{total}] {question}")
        logger.info(f"  Expected        : {expected_answer}")

        # --- Call solver ---
        start_time = time.time()
        try:
            result = await solver_service.solve(query=question, user_id=0, include_plot=False)
            elapsed = time.time() - start_time
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.info(f"  ERROR           : {exc}")
            csv_rows.append({
                "Question": question,
                "Predicted Answer": f"ERROR: {exc}",
                "Actual Answer": expected_answer,
                "Normalized Predicted": "",
                "Normalized Expected": str(normalize_expression(expected_answer)),
                "Correct or Incorrect": "Incorrect",
                "Response Time": round(elapsed, 4),
            })
            incorrect += 1
            response_times.append(elapsed)
            logger.info("")
            continue

        # --- Extract predicted answer ---
        solution_text = result.get("solution", "")
        predicted_answer = extract_answer_from_solution(solution_text)

        # HYBRID PIPELINE: The SymPy answer is the authoritative source
        # It's now returned directly in the validation dict when sympy_computed=True
        validation = result.get("validation", {})
        sympy_answer = validation.get("sympy_answer")
        sympy_computed = result.get("sympy_computed", False)
        math_type = result.get("math_type", "unknown")

        # Build a list of candidate predicted answers (try all of them)
        # Priority: SymPy answer first (highest confidence), then extracted answer
        candidates = []
        if sympy_answer and str(sympy_answer) != "None":
            candidates.append(str(sympy_answer))
        if predicted_answer:
            candidates.append(predicted_answer)
        # Also try the raw solution's last line as a fallback
        if solution_text:
            raw_last = _clean_answer_text(
                solution_text.strip().split("\n")[-1].strip()
            )
            if raw_last and raw_last not in candidates:
                candidates.append(raw_last)

        # --- Compare answers using all candidates against all acceptable answers ---
        all_acceptable = [expected_answer] + alternate_answers
        is_correct = False
        best_candidate = candidates[0] if candidates else ""
        norm_pred_str = ""
        norm_actual_str = str(normalize_expression(expected_answer))

        for cand in candidates:
            norm_expr = normalize_expression(cand)
            if norm_expr is not None:
                norm_pred_str = str(norm_expr)

            for acceptable in all_acceptable:
                if evaluate_answer(cand, acceptable, topic):
                    is_correct = True
                    best_candidate = cand
                    if norm_expr is not None:
                        norm_pred_str = str(norm_expr)
                    break
            if is_correct:
                break

        if is_correct:
            correct += 1
            status = "Correct"
        else:
            incorrect += 1
            status = "Incorrect"

        response_times.append(elapsed)

        # --- Detailed logging ---
        logger.info(f"  Predicted       : {best_candidate}")
        logger.info(f"  Norm. Predicted : {norm_pred_str}")
        logger.info(f"  Norm. Expected  : {norm_actual_str}")
        logger.info(f"  SymPy Computed  : {sympy_computed}  (type: {math_type})")
        logger.info(f"  Result          : {status}  ({elapsed:.2f}s)")
        logger.info("")

        csv_rows.append({
            "Question": question,
            "Predicted Answer": best_candidate,
            "Actual Answer": expected_answer,
            "Normalized Predicted": norm_pred_str,
            "Normalized Expected": norm_actual_str,
            "Correct or Incorrect": status,
            "SymPy Computed": str(sympy_computed),
            "Math Type": math_type,
            "Response Time": round(elapsed, 4),
        })

    # ── Save results.csv ──────────────────────────────────────────────────
    with open(RESULTS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Question", "Predicted Answer", "Actual Answer",
            "Normalized Predicted", "Normalized Expected",
            "Correct or Incorrect", "SymPy Computed", "Math Type",
            "Response Time",
        ])
        writer.writeheader()
        writer.writerows(csv_rows)

    logger.info(f"Results saved to {RESULTS_CSV_PATH}\n")

    # ── Compute metrics ───────────────────────────────────────────────────
    accuracy = correct / total if total > 0 else 0.0
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

    # Count how many were solved by SymPy
    sympy_solved = sum(
        1 for row in csv_rows if row.get("SymPy Computed") == "True"
    )
    sympy_rate = sympy_solved / total if total > 0 else 0.0

    # For a binary correct/incorrect evaluation:
    #   TP = correct answers   FN = incorrect answers
    #   FP = 0 (system always produces an answer)
    tp = correct
    fp = 0
    fn = incorrect

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # ── Print summary ─────────────────────────────────────────────────────
    logger.info(f"{'='*70}")
    logger.info(f"  EVALUATION RESULTS  (Hybrid SymPy-First Pipeline)")
    logger.info(f"{'='*70}")
    logger.info(f"  Total Questions     : {total}")
    logger.info(f"  Correct Answers     : {correct}")
    logger.info(f"  Incorrect Answers   : {incorrect}")
    logger.info(f"  SymPy Computed      : {sympy_solved}/{total}  ({sympy_rate*100:.1f}%)")
    logger.info(f"  Accuracy            : {accuracy:.4f}  ({accuracy*100:.1f}%)")
    logger.info(f"  Precision           : {precision:.4f}")
    logger.info(f"  Recall              : {recall:.4f}")
    logger.info(f"  F1 Score            : {f1_score:.4f}")
    logger.info(f"  Avg Response Time   : {avg_response_time:.4f} seconds")
    logger.info(f"{'='*70}\n")

    # ── Save metrics summary as JSON for plot_results.py ──────────────────
    metrics = {
        "total_questions": total,
        "correct_answers": correct,
        "incorrect_answers": incorrect,
        "sympy_computed": sympy_solved,
        "sympy_rate": round(sympy_rate, 4),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4),
        "avg_response_time": round(avg_response_time, 4),
    }
    metrics_path = os.path.join(EVAL_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Metrics saved to {metrics_path}")


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    asyncio.run(evaluate())
