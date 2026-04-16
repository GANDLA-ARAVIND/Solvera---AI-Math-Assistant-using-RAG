"""Quick self-test of the improved comparison functions."""
import sys, os

# Setup paths exactly like evaluate_system.py
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EVAL_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from sympy import simplify, expand, factor, trigsimp, cancel, N, symbols, sympify
from sympy import sin, cos, tan, exp, log, sqrt, pi, expand_trig, Abs
from sympy import asin, acos, atan, sec, csc, cot, E, oo, I
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)
import re, random, math

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)

_x, _y, _z = symbols('x y z')
_a, _b, _n = symbols('a b n')
LOCAL_DICT = {
    'sin': sin, 'cos': cos, 'tan': tan,
    'asin': asin, 'acos': acos, 'atan': atan,
    'log': log, 'exp': exp, 'sqrt': sqrt,
    'pi': pi, 'E': E,
    'x': _x, 'y': _y, 'z': _z,
    'a': _a, 'b': _b, 'n': _n,
}

NUMERIC_TOLERANCE = 1e-5
NUM_TEST_POINTS = 8


def normalize_expression(expr_str):
    if not expr_str or not expr_str.strip():
        return None
    text = str(expr_str).strip()
    # Remove markdown decorators
    # Remove markdown headers/bold carefully, preserving arithmetic *
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<![a-zA-Z0-9)\]])\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\$\$?", "", text)
    # Remove boxed
    text = re.sub(r"\\boxed\{(.+?)\}", r"\1", text)
    text = re.sub(r"\\text\{[^}]*\}", "", text)
    # Fractions
    for _ in range(5):
        new = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", text)
        if new == text:
            break
        text = new
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", text)
    latex_map = {
        "\\cdot": "*", "\\times": "*", "\\div": "/",
        "\\pi": " pi ", "\\infty": " oo ",
        "\\sin": " sin", "\\cos": " cos", "\\tan": " tan",
        "\\ln": " log", "\\log": " log", "\\exp": " exp",
        "\\left": "", "\\right": "", "\\,": " ", "\\ ": " ", "\\": "",
    }
    for k, v in latex_map.items():
        text = text.replace(k, v)
    text = text.replace("^", "**")
    text = re.sub(r"\+\s*[Cc]\s*$", "", text)
    text = re.sub(r"\+\s*[Cc]\s*(?=[,\]\)])", "", text)
    text = re.sub(r"(?:,?\s*where\s+.*$)", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if not text:
        return None
    try:
        return parse_expr(text, transformations=TRANSFORMATIONS, local_dict=LOCAL_DICT)
    except Exception:
        pass
    try:
        return parse_expr(text, transformations=TRANSFORMATIONS)
    except Exception:
        pass
    try:
        return sympify(text, locals=LOCAL_DICT)
    except Exception:
        pass
    try:
        return sympify(text)
    except Exception:
        return None


def symbolic_compare(pred_expr, actual_expr):
    if pred_expr is None or actual_expr is None:
        return False
    if pred_expr.is_number and actual_expr.is_number:
        try:
            return bool(simplify(pred_expr - actual_expr) == 0)
        except Exception:
            pass
        try:
            return abs(complex(N(pred_expr)) - complex(N(actual_expr))) < NUMERIC_TOLERANCE
        except Exception:
            return False
    # Check 1: simplify(diff)
    try:
        if simplify(pred_expr - actual_expr) == 0:
            return True
    except Exception:
        pass
    # Check 2: expand
    try:
        if expand(pred_expr) == expand(actual_expr):
            return True
    except Exception:
        pass
    # Check 3: factor
    try:
        if factor(pred_expr) == factor(actual_expr):
            return True
    except Exception:
        pass
    # Check 4: trigsimp
    try:
        if trigsimp(pred_expr - actual_expr) == 0:
            return True
    except Exception:
        pass
    # Check 4b: trigsimp each side individually
    try:
        ts_pred = trigsimp(pred_expr)
        ts_actual = trigsimp(actual_expr)
        if ts_pred == ts_actual:
            return True
        if simplify(ts_pred - ts_actual) == 0:
            return True
    except Exception:
        pass
    # Check 4c: expand_trig + simplify
    try:
        et_pred = expand_trig(pred_expr)
        et_actual = expand_trig(actual_expr)
        if simplify(et_pred - et_actual) == 0:
            return True
    except Exception:
        pass
    # Check 5: ratio test
    try:
        if actual_expr != 0 and simplify(pred_expr / actual_expr) == 1:
            return True
    except Exception:
        pass
    # Check 6: cancel
    try:
        if cancel(pred_expr - actual_expr) == 0:
            return True
    except Exception:
        pass
    return False


def numeric_compare(pred_expr, actual_expr, tolerance=NUMERIC_TOLERANCE):
    if pred_expr is None or actual_expr is None:
        return False
    try:
        free_syms = sorted(
            pred_expr.free_symbols | actual_expr.free_symbols, key=lambda s: s.name
        )
    except Exception:
        return False
    if not free_syms:
        try:
            return abs(complex(N(pred_expr)) - complex(N(actual_expr))) < tolerance
        except Exception:
            return False
    random.seed(42)
    candidate_values = [0.5, 1.0, 1.5, 2.0, -1.0, -0.5, 0.7, 1.3, -1.7, 2.5, 0.3, 3.0]
    matches = evaluated = 0
    for _ in range(NUM_TEST_POINTS):
        subs = {s: random.choice(candidate_values) for s in free_syms}
        try:
            pv = complex(pred_expr.subs(subs).evalf())
            av = complex(actual_expr.subs(subs).evalf())
            if math.isnan(pv.real) or math.isinf(pv.real):
                continue
            if math.isnan(av.real) or math.isinf(av.real):
                continue
            evaluated += 1
            if abs(pv - av) < tolerance:
                matches += 1
        except Exception:
            continue
    return evaluated >= 3 and matches == evaluated


def evaluate_answer(predicted_str, actual_str, topic="general"):
    if not predicted_str or not actual_str:
        return False

    def _ns(t):
        t = t.strip().lower()
        t = re.sub(r"\s+", "", t)
        t = t.replace("^", "**")
        t = re.sub(r"\+\s*[Cc]$", "", t)
        return t

    if _ns(predicted_str) == _ns(actual_str):
        return True

    pred_expr = normalize_expression(predicted_str)
    actual_expr = normalize_expression(actual_str)

    if symbolic_compare(pred_expr, actual_expr):
        return True

    if topic in ("integrals", "calculus"):
        pred_no_c = re.sub(r"\+\s*[Cc]\b", "", predicted_str)
        pred_expr_no_c = normalize_expression(pred_no_c)
        if symbolic_compare(pred_expr_no_c, actual_expr):
            return True
        if pred_expr is not None and actual_expr is not None:
            try:
                diff_simplified = simplify(pred_expr - actual_expr)
                if not diff_simplified.free_symbols:
                    return True
            except Exception:
                pass

    if topic == "derivatives":
        if pred_expr is not None and actual_expr is not None:
            try:
                if trigsimp(expand(pred_expr) - expand(actual_expr)) == 0:
                    return True
            except Exception:
                pass

    if numeric_compare(pred_expr, actual_expr):
        return True

    return False


# ════════════════════════════════════════════════
# TEST CASES
# ════════════════════════════════════════════════
tests = [
    ("x**3/3 + C", "x**3/3", "integrals", True, "integral with +C"),
    ("(1/3)*x**3", "x**3/3", "integrals", True, "equivalent fraction form"),
    ("-cos(x) + C", "-cos(x)", "integrals", True, "integral with +C"),
    ("cos(2*x)", "-sin(x)**2 + cos(x)**2", "derivatives", True, "trig identity cos(2x)"),
    ("3*x**2 + 4*x - 5", "4*x + 3*x**2 - 5", "derivatives", True, "reordered terms"),
    ("sin(x)", "tan(x)*cos(x)", "trigonometry", True, "trig simplification"),
    ("x + 3", "x + 3", "algebra", True, "exact match"),
    ("2*exp(2*x)", "2*exp(2*x)", "derivatives", True, "exact exp match"),
    ("x + 5", "x + 3", "algebra", False, "genuinely wrong"),
    ("sin(x)**2 + cos(x)**2", "1", "trigonometry", True, "pythagorean identity"),
    ("exp(x) + C", "exp(x)", "integrals", True, "exp integral +C"),
    ("x**2 + 3*x + C", "x**2 + 3*x", "integrals", True, "poly integral +C"),
]

print("=" * 60)
print("  Comparison Function Unit Tests")
print("=" * 60)
passed = failed = 0
for pred, actual, topic, expected, desc in tests:
    result = evaluate_answer(pred, actual, topic)
    ok = result == expected
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  {status}: {desc}")
    if not ok:
        print(f"         pred={pred!r}  actual={actual!r}  got={result}  expected={expected}")

print(f"\n  {passed}/{passed + failed} tests passed")
if failed:
    print(f"  {failed} FAILED")
else:
    print("  All tests passed!")
print("=" * 60)
