"""SymPy Solver — primary computation engine for the hybrid pipeline.

This module is the *authoritative* source for mathematical answers.
It handles: derivatives, integrals (indefinite & definite), limits,
equation solving, simplification, expansion, factoring, trig, and evaluation.

Every public function returns a standardised ``SolverResult`` dict.
"""

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

import sympy
from sympy import (
    symbols, Symbol, solve, diff, integrate, limit, simplify, expand,
    factor, trigsimp, expand_trig, cancel,
    oo, pi, E, I,
    sin, cos, tan, sec, csc, cot,
    asin, acos, atan,
    sqrt, exp, log, ln, Abs, Rational, factorial,
    N, S,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

logger = logging.getLogger(__name__)

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# Local dict so parse_expr doesn't confuse trig names with variables
_PARSE_LOCALS = {
    "sin": sin, "cos": cos, "tan": tan, "sec": sec, "csc": csc, "cot": cot,
    "asin": asin, "acos": acos, "atan": atan,
    "log": log, "ln": ln, "exp": exp, "sqrt": sqrt, "Abs": Abs,
    "pi": pi, "E": E, "oo": oo, "I": I,
    "e": E,
}

# Create standard symbols
x, y, z = symbols("x y z")
a, b, n = symbols("a b n")
_PARSE_LOCALS.update({"x": x, "y": y, "z": z, "a": a, "b": b, "n": n})


# ═══════════════════════════════════════════════════════════════════════════
#  Result type
# ═══════════════════════════════════════════════════════════════════════════

def _make_result(
    success: bool,
    result: Any = None,
    result_latex: str = "",
    result_str: str = "",
    math_type: str = "",
    input_expr: str = "",
    steps: list[str] | None = None,
    error: str = "",
) -> dict:
    """Build a standardised solver result dict."""
    return {
        "success": success,
        "result": result,                       # raw SymPy object
        "result_latex": result_latex,            # LaTeX string
        "result_str": result_str,               # plain string (for eval comparison)
        "math_type": math_type,
        "input_expr": input_expr,
        "steps": steps or [],
        "error": error,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Safe expression parser
# ═══════════════════════════════════════════════════════════════════════════

def _safe_parse(expr_str: str):
    """Parse an expression string into a SymPy expression. Returns None on failure."""
    if not expr_str or not expr_str.strip():
        return None

    text = expr_str.strip()
    # Normalize common tokens
    text = text.replace("^", "**")
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", text)
    text = text.replace("\\cdot", "*").replace("\\times", "*")
    text = text.replace("\\pi", " pi ").replace("\\infty", " oo ")
    text = text.replace("\\sin", " sin").replace("\\cos", " cos")
    text = text.replace("\\tan", " tan").replace("\\ln", " log")
    text = text.replace("\\log", " log").replace("\\exp", " exp")
    text = text.replace("\\left", "").replace("\\right", "")
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("\\", "")
    text = re.sub(r"\$\$?", "", text)
    text = text.strip()

    if not text:
        return None

    for attempt in [
        lambda: parse_expr(text, transformations=TRANSFORMATIONS, local_dict=_PARSE_LOCALS),
        lambda: parse_expr(text, transformations=TRANSFORMATIONS),
        lambda: sympy.sympify(text, locals=_PARSE_LOCALS),
    ]:
        try:
            return attempt()
        except Exception:
            continue

    return None


def _get_variable(parsed_info: dict):
    """Get the SymPy symbol for the primary variable."""
    var_name = parsed_info.get("variable", "x")
    return symbols(var_name)


# ═══════════════════════════════════════════════════════════════════════════
#  Master entry point
# ═══════════════════════════════════════════════════════════════════════════

def sympy_solve(math_type: str, parsed: dict) -> dict:
    """Dispatch to the appropriate SymPy solver based on detected math type.

    Args:
        math_type: One of the types from ``detect_math_type`` (e.g. "derivative").
        parsed: The dict returned by ``extract_math_expression``.

    Returns:
        A ``SolverResult`` dict.
    """
    dispatch = {
        "derivative": _solve_derivative,
        "second_derivative": _solve_second_derivative,
        "integration": _solve_integral,
        "definite_integral": _solve_definite_integral,
        "limit": _solve_limit,
        "equation": _solve_equation,
        "system_of_equations": _solve_system,
        "simplification": _solve_simplify,
        "expansion": _solve_expand,
        "factoring": _solve_factor,
        "trigonometry": _solve_trig,
        "evaluation": _solve_evaluate,
    }

    solver_fn = dispatch.get(math_type, _solve_generic)

    try:
        result = solver_fn(parsed)
        if result["success"]:
            logger.info(
                "SymPy solved [%s]: %s → %s",
                math_type, parsed.get("expr", "?"), result["result_str"],
            )
        else:
            logger.warning(
                "SymPy failed [%s]: %s — %s",
                math_type, parsed.get("expr", "?"), result["error"],
            )
        return result
    except Exception as exc:
        logger.error("SymPy solver exception [%s]: %s", math_type, exc)
        return _make_result(
            success=False,
            math_type=math_type,
            input_expr=parsed.get("expr", ""),
            error=str(exc),
        )


# ═══════════════════════════════════════════════════════════════════════════
#  Individual solvers
# ═══════════════════════════════════════════════════════════════════════════

def _solve_derivative(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="derivative", input_expr=parsed["expr"],
                            error="Could not parse expression")

    var = _get_variable(parsed)
    result = diff(expr, var)
    result_simplified = simplify(result)

    return _make_result(
        success=True,
        result=result_simplified,
        result_latex=sympy.latex(result_simplified),
        result_str=str(result_simplified),
        math_type="derivative",
        input_expr=parsed["expr"],
        steps=[
            f"Given: f({var}) = {sympy.latex(expr)}",
            f"Apply differentiation rules: d/d{var}",
            f"Result: {sympy.latex(result)}",
            f"Simplified: {sympy.latex(result_simplified)}",
        ],
    )


def _solve_second_derivative(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="second_derivative", input_expr=parsed["expr"],
                            error="Could not parse expression")

    var = _get_variable(parsed)
    first = diff(expr, var)
    result = diff(first, var)
    result_simplified = simplify(result)

    return _make_result(
        success=True,
        result=result_simplified,
        result_latex=sympy.latex(result_simplified),
        result_str=str(result_simplified),
        math_type="second_derivative",
        input_expr=parsed["expr"],
        steps=[
            f"Given: f({var}) = {sympy.latex(expr)}",
            f"First derivative: f'({var}) = {sympy.latex(first)}",
            f"Second derivative: f''({var}) = {sympy.latex(result_simplified)}",
        ],
    )


def _solve_integral(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="integration", input_expr=parsed["expr"],
                            error="Could not parse expression")

    var = _get_variable(parsed)
    result = integrate(expr, var)

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="integration",
        input_expr=parsed["expr"],
        steps=[
            f"Given: ∫ {sympy.latex(expr)} d{var}",
            f"Apply integration rules",
            f"Result: {sympy.latex(result)} + C",
        ],
    )


def _solve_definite_integral(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="definite_integral", input_expr=parsed["expr"],
                            error="Could not parse expression")

    var = _get_variable(parsed)
    bounds = parsed.get("bounds")

    if not bounds:
        # Fall back to indefinite
        return _solve_integral(parsed)

    lower = _safe_parse(bounds[0])
    upper = _safe_parse(bounds[1])

    if lower is None or upper is None:
        return _make_result(False, math_type="definite_integral", input_expr=parsed["expr"],
                            error=f"Could not parse bounds: {bounds}")

    result = integrate(expr, (var, lower, upper))
    result_simplified = simplify(result)

    return _make_result(
        success=True,
        result=result_simplified,
        result_latex=sympy.latex(result_simplified),
        result_str=str(result_simplified),
        math_type="definite_integral",
        input_expr=parsed["expr"],
        steps=[
            f"Given: ∫_{{{sympy.latex(lower)}}}^{{{sympy.latex(upper)}}} {sympy.latex(expr)} d{var}",
            f"Compute antiderivative: F({var}) = {sympy.latex(integrate(expr, var))}",
            f"Evaluate: F({sympy.latex(upper)}) - F({sympy.latex(lower)})",
            f"Result: {sympy.latex(result_simplified)}",
        ],
    )


def _solve_limit(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="limit", input_expr=parsed["expr"],
                            error="Could not parse expression")

    var = _get_variable(parsed)
    point_str = parsed.get("point", "0")
    point = _safe_parse(point_str) if point_str else S(0)
    if point is None:
        point = S(0)

    result = limit(expr, var, point)

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="limit",
        input_expr=parsed["expr"],
        steps=[
            f"Given: lim_({var}→{sympy.latex(point)}) {sympy.latex(expr)}",
            f"Evaluate the limit",
            f"Result: {sympy.latex(result)}",
        ],
    )


def _solve_equation(parsed: dict) -> dict:
    expr_str = parsed["expr"]
    expr = _safe_parse(expr_str)
    if expr is None:
        return _make_result(False, math_type="equation", input_expr=expr_str,
                            error="Could not parse equation")

    # Determine variable to solve for
    free_vars = sorted(expr.free_symbols, key=lambda s: s.name)
    if not free_vars:
        # No variables — just simplify
        result = simplify(expr)
        return _make_result(
            success=True,
            result=result,
            result_latex=sympy.latex(result),
            result_str=str(result),
            math_type="evaluation",
            input_expr=expr_str,
            steps=[f"Expression evaluates to: {sympy.latex(result)}"],
        )

    var = free_vars[0]  # solve for first variable by default
    solutions = solve(expr, var)

    if not solutions:
        return _make_result(False, math_type="equation", input_expr=expr_str,
                            error="No solutions found")

    # Format result
    if len(solutions) == 1:
        result_str = str(solutions[0])
        result_latex = sympy.latex(solutions[0])
    else:
        result_str = str(solutions)
        result_latex = ", ".join(sympy.latex(s) for s in solutions)

    return _make_result(
        success=True,
        result=solutions,
        result_latex=result_latex,
        result_str=result_str,
        math_type="equation",
        input_expr=expr_str,
        steps=[
            f"Solve: {sympy.latex(expr)} = 0 for {var}",
            f"Solutions: {var} = {result_latex}",
        ],
    )


def _solve_system(parsed: dict) -> dict:
    """Solve a system of equations."""
    raw_eqs = parsed.get("equations", [])
    if not raw_eqs:
        # Try splitting by comma
        expr_str = parsed["expr"]
        raw_eqs = [eq.strip() for eq in expr_str.split(",") if eq.strip()]

    if len(raw_eqs) < 2:
        return _make_result(False, math_type="system_of_equations",
                            input_expr=parsed["expr"],
                            error="Need at least 2 equations for a system")

    sym_eqs = []
    all_vars = set()
    for raw in raw_eqs:
        if "=" in raw:
            parts = raw.split("=", 1)
            lhs = _safe_parse(parts[0].strip())
            rhs = _safe_parse(parts[1].strip())
            if lhs is not None and rhs is not None:
                eq = lhs - rhs
                sym_eqs.append(eq)
                all_vars.update(eq.free_symbols)
        else:
            eq = _safe_parse(raw)
            if eq is not None:
                sym_eqs.append(eq)
                all_vars.update(eq.free_symbols)

    if len(sym_eqs) < 2:
        return _make_result(False, math_type="system_of_equations",
                            input_expr=parsed["expr"],
                            error="Could not parse system equations")

    var_list = sorted(all_vars, key=lambda s: s.name)
    solutions = solve(sym_eqs, var_list)

    if not solutions:
        return _make_result(False, math_type="system_of_equations",
                            input_expr=parsed["expr"],
                            error="No solutions found for system")

    # Format
    if isinstance(solutions, dict):
        result_str = str(solutions)
        result_latex = ", ".join(
            f"{sympy.latex(k)} = {sympy.latex(v)}" for k, v in solutions.items()
        )
    elif isinstance(solutions, list) and solutions:
        result_str = str(solutions)
        result_latex = str(solutions)
    else:
        result_str = str(solutions)
        result_latex = str(solutions)

    return _make_result(
        success=True,
        result=solutions,
        result_latex=result_latex,
        result_str=result_str,
        math_type="system_of_equations",
        input_expr=parsed["expr"],
        steps=[f"System solved: {result_latex}"],
    )


def _solve_simplify(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="simplification", input_expr=parsed["expr"],
                            error="Could not parse expression")

    result = simplify(expr)
    # Also try trigsimp if trig functions are present
    if expr.has(sin, cos, tan, sec, csc, cot):
        trig_result = trigsimp(expr)
        # Pick the simpler form
        if len(str(trig_result)) < len(str(result)):
            result = trig_result

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="simplification",
        input_expr=parsed["expr"],
        steps=[
            f"Given: {sympy.latex(expr)}",
            f"Simplified: {sympy.latex(result)}",
        ],
    )


def _solve_expand(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="expansion", input_expr=parsed["expr"],
                            error="Could not parse expression")

    result = expand(expr)

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="expansion",
        input_expr=parsed["expr"],
        steps=[
            f"Given: {sympy.latex(expr)}",
            f"Expanded: {sympy.latex(result)}",
        ],
    )


def _solve_factor(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="factoring", input_expr=parsed["expr"],
                            error="Could not parse expression")

    result = factor(expr)

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="factoring",
        input_expr=parsed["expr"],
        steps=[
            f"Given: {sympy.latex(expr)}",
            f"Factored: {sympy.latex(result)}",
        ],
    )


def _solve_trig(parsed: dict) -> dict:
    """Handle trig simplification, identity verification, or equation solving."""
    expr_str = parsed["expr"]
    expr = _safe_parse(expr_str)
    if expr is None:
        return _make_result(False, math_type="trigonometry", input_expr=expr_str,
                            error="Could not parse trig expression")

    query_lower = parsed.get("original", "").lower()

    # If it looks like an equation to solve
    if any(kw in query_lower for kw in ["solve", "find"]):
        var = _get_variable(parsed)
        solutions = solve(expr, var)
        if solutions:
            result_str = str(solutions)
            result_latex = ", ".join(sympy.latex(s) for s in solutions)
            return _make_result(
                success=True,
                result=solutions,
                result_latex=result_latex,
                result_str=result_str,
                math_type="trigonometry",
                input_expr=expr_str,
                steps=[
                    f"Solve: {sympy.latex(expr)} = 0",
                    f"Solutions: {result_latex}",
                ],
            )

    # Otherwise simplify
    result = trigsimp(expr)
    if result == expr:
        result = simplify(expr)

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="trigonometry",
        input_expr=expr_str,
        steps=[
            f"Given: {sympy.latex(expr)}",
            f"Simplified: {sympy.latex(result)}",
        ],
    )


def _solve_evaluate(parsed: dict) -> dict:
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="evaluation", input_expr=parsed["expr"],
                            error="Could not parse expression")

    result = simplify(expr)
    # If it's numeric, fully evaluate
    if result.is_number:
        result = result.evalf()
        # If it's an integer value, convert
        if result == int(result):
            result = sympy.Integer(int(result))

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="evaluation",
        input_expr=parsed["expr"],
        steps=[
            f"Given: {sympy.latex(expr)}",
            f"Result: {sympy.latex(result)}",
        ],
    )


def _solve_generic(parsed: dict) -> dict:
    """Fallback — try simplification, then solve, then evaluate."""
    expr = _safe_parse(parsed["expr"])
    if expr is None:
        return _make_result(False, math_type="unknown", input_expr=parsed["expr"],
                            error="Could not parse expression")

    # If has free variables and contains "=", treat as equation
    free_vars = list(expr.free_symbols)
    if free_vars:
        try:
            solutions = solve(expr, free_vars[0])
            if solutions:
                result_str = str(solutions) if len(solutions) > 1 else str(solutions[0])
                return _make_result(
                    success=True,
                    result=solutions,
                    result_latex=sympy.latex(solutions),
                    result_str=result_str,
                    math_type="equation",
                    input_expr=parsed["expr"],
                    steps=[f"Solved for {free_vars[0]}: {result_str}"],
                )
        except Exception:
            pass

    # Try simplification
    result = simplify(expr)

    return _make_result(
        success=True,
        result=result,
        result_latex=sympy.latex(result),
        result_str=str(result),
        math_type="simplification",
        input_expr=parsed["expr"],
        steps=[
            f"Given: {sympy.latex(expr)}",
            f"Simplified: {sympy.latex(result)}",
        ],
    )
