import re
import sympy
from sympy import (
    symbols, solve, simplify, diff, integrate, limit, oo, pi, E,
    sin, cos, tan, asin, acos, atan, sqrt, Rational, factorial,
    trigsimp, expand_trig, nsimplify,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)


class SympyValidator:
    """Validates LLM math answers using SymPy symbolic computation."""

    TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

    def validate_equation(self, equation_str: str, llm_answer: str) -> dict:
        """Attempt to solve an equation with SymPy and compare to LLM answer."""
        try:
            expr = self._parse_math_expression(equation_str)
            if expr is None:
                return {
                    "attempted": True,
                    "verified": False,
                    "sympy_answer": None,
                    "match": None,
                    "details": "Could not parse expression",
                }

            free_vars = list(expr.free_symbols)
            if not free_vars:
                result = simplify(expr)
                return self._compare_results(str(result), llm_answer)

            x = free_vars[0]
            solutions = solve(expr, x)
            sympy_answer = str(solutions)

            return self._compare_results(sympy_answer, llm_answer)

        except Exception as e:
            return {
                "attempted": True,
                "verified": False,
                "sympy_answer": None,
                "match": None,
                "details": f"Validation error: {str(e)}",
            }

    def validate_derivative(self, expression_str: str, variable: str = "x") -> dict:
        """Compute derivative and return result."""
        try:
            var = symbols(variable)
            expr = parse_expr(expression_str, transformations=self.TRANSFORMATIONS)
            result = diff(expr, var)
            return {
                "attempted": True,
                "verified": True,
                "sympy_answer": str(result),
                "match": None,
                "details": "Derivative computed",
                "latex": sympy.latex(result),
            }
        except Exception as e:
            return {
                "attempted": True,
                "verified": False,
                "details": f"Derivative error: {str(e)}",
            }

    def validate_integral(self, expression_str: str, variable: str = "x") -> dict:
        """Compute integral and return result."""
        try:
            var = symbols(variable)
            expr = parse_expr(expression_str, transformations=self.TRANSFORMATIONS)
            result = integrate(expr, var)
            return {
                "attempted": True,
                "verified": True,
                "sympy_answer": str(result),
                "match": None,
                "details": "Integral computed",
                "latex": sympy.latex(result),
            }
        except Exception as e:
            return {
                "attempted": True,
                "verified": False,
                "details": f"Integration error: {str(e)}",
            }

    def validate_limit(self, query: str, expression_str: str) -> dict:
        """Compute a limit. Tries to detect the variable and point from the query."""
        try:
            var = symbols("x")
            expr = parse_expr(expression_str, transformations=self.TRANSFORMATIONS)

            # Try to extract "as x -> value" from query
            point = 0  # default
            query_lower = query.lower()
            limit_match = re.search(
                r"(?:as|when|→|->)\s*x\s*(?:→|->|approaches|tends to)\s*([^\s,]+)",
                query_lower,
            )
            if limit_match:
                pt_str = limit_match.group(1).strip()
                if pt_str in ("infinity", "inf", "∞"):
                    point = oo
                elif pt_str in ("-infinity", "-inf", "-∞"):
                    point = -oo
                else:
                    try:
                        point = parse_expr(pt_str, transformations=self.TRANSFORMATIONS)
                    except Exception:
                        pass

            result = limit(expr, var, point)
            return {
                "attempted": True,
                "verified": True,
                "sympy_answer": str(result),
                "match": None,
                "details": f"Limit computed (x → {point})",
                "latex": sympy.latex(result),
            }
        except Exception as e:
            return {
                "attempted": True,
                "verified": False,
                "details": f"Limit error: {str(e)}",
            }

    def validate_trig_expression(self, query: str, llm_answer: str) -> dict:
        """Validate trigonometric expressions/identities using SymPy."""
        try:
            x = symbols("x")
            # Try to parse LLM answer and simplify
            clean_answer = self._clean_expression(llm_answer)
            if not clean_answer:
                return {"attempted": False, "reason": "Could not parse trig answer"}

            llm_expr = parse_expr(clean_answer, transformations=self.TRANSFORMATIONS)

            # Check if this is an equation to solve
            query_lower = query.lower()
            if any(kw in query_lower for kw in ["solve", "find x", "find the value"]):
                # Try to extract and solve trig equation
                main_expr = self._extract_trig_equation(query)
                if main_expr is not None:
                    solutions = solve(main_expr, x)
                    if solutions:
                        return {
                            "attempted": True,
                            "verified": True,
                            "sympy_answer": str(solutions),
                            "match": None,
                            "details": "Trig equation solved",
                        }

            # Try simplifying LLM answer to verify it's valid
            simplified = trigsimp(llm_expr)
            return {
                "attempted": True,
                "verified": True,
                "sympy_answer": str(simplified),
                "match": None,
                "details": "Trig expression validated",
                "latex": sympy.latex(simplified),
            }
        except Exception:
            return {"attempted": False, "reason": "Could not validate trig expression"}

    def validate_numeric_result(self, query: str, llm_answer: str) -> dict:
        """Validate a numeric result by trying to evaluate the LLM answer."""
        try:
            clean = self._clean_expression(llm_answer)
            if not clean:
                return {"attempted": False, "reason": "Could not parse numeric answer"}

            expr = parse_expr(clean, transformations=self.TRANSFORMATIONS)
            result = expr.evalf()

            # Check if the result is a valid number
            if result.is_number:
                return {
                    "attempted": True,
                    "verified": True,
                    "sympy_answer": str(result),
                    "match": None,
                    "details": "Numeric result validated",
                }
            return {
                "attempted": True,
                "verified": True,
                "sympy_answer": str(simplify(expr)),
                "match": None,
                "details": "Expression simplified",
            }
        except Exception:
            return {"attempted": False, "reason": "Could not validate numeric result"}

    def evaluate_expression(self, expression_str: str) -> dict:
        """Evaluate a numeric mathematical expression."""
        try:
            expr = parse_expr(expression_str, transformations=self.TRANSFORMATIONS)
            result = simplify(expr)
            return {
                "attempted": True,
                "verified": True,
                "sympy_answer": str(result),
                "latex": sympy.latex(result),
            }
        except Exception as e:
            return {"attempted": True, "verified": False, "details": str(e)}

    def _clean_expression(self, expr_str: str) -> str | None:
        """Clean a math expression string for parsing."""
        if not expr_str:
            return None
        expr_str = re.sub(r"\\frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", expr_str)
        expr_str = expr_str.replace("\\cdot", "*").replace("\\times", "*")
        expr_str = expr_str.replace("\\pi", "pi").replace("\\sqrt", "sqrt")
        expr_str = expr_str.replace("\\sin", "sin").replace("\\cos", "cos")
        expr_str = expr_str.replace("\\tan", "tan").replace("\\log", "log")
        expr_str = expr_str.replace("\\ln", "log")
        expr_str = expr_str.replace("^", "**")
        expr_str = re.sub(r"[$$\\]", "", expr_str)
        expr_str = expr_str.strip()
        return expr_str if expr_str else None

    def _extract_trig_equation(self, query: str):
        """Try to extract a trig equation from a query."""
        try:
            # Remove question phrasing
            query_clean = re.sub(
                r"^(solve|find|what is|evaluate)\s+", "", query.lower()
            ).strip()
            # Clean LaTeX and parse
            cleaned = self._clean_expression(query_clean)
            if cleaned and "=" in cleaned:
                parts = cleaned.split("=")
                if len(parts) == 2:
                    left = parse_expr(
                        parts[0].strip(), transformations=self.TRANSFORMATIONS
                    )
                    right = parse_expr(
                        parts[1].strip(), transformations=self.TRANSFORMATIONS
                    )
                    return left - right
            return None
        except Exception:
            return None

    def _parse_math_expression(self, expr_str: str):
        """Clean and parse a math expression string."""
        # Remove LaTeX formatting
        expr_str = re.sub(r"\\frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", expr_str)
        expr_str = expr_str.replace("\\cdot", "*").replace("\\times", "*")
        expr_str = expr_str.replace("^", "**")
        expr_str = re.sub(r"[$$\\]", "", expr_str)
        expr_str = expr_str.strip()

        # Handle equation format: "expression = 0" -> "expression"
        if "=" in expr_str:
            parts = expr_str.split("=")
            if len(parts) == 2:
                left, right = parts
                try:
                    left_expr = parse_expr(
                        left.strip(), transformations=self.TRANSFORMATIONS
                    )
                    right_expr = parse_expr(
                        right.strip(), transformations=self.TRANSFORMATIONS
                    )
                    return left_expr - right_expr
                except Exception:
                    pass

        try:
            return parse_expr(expr_str, transformations=self.TRANSFORMATIONS)
        except Exception:
            return None

    def _compare_results(self, sympy_answer: str, llm_answer: str) -> dict:
        """Compare SymPy result with LLM answer."""
        try:
            sympy_expr = parse_expr(
                sympy_answer, transformations=self.TRANSFORMATIONS
            )
            # Clean LLM answer
            clean_llm = re.sub(r"[$$\\]", "", llm_answer).strip()
            clean_llm = clean_llm.replace("^", "**")
            llm_expr = parse_expr(clean_llm, transformations=self.TRANSFORMATIONS)
            match = simplify(sympy_expr - llm_expr) == 0
        except Exception:
            # String comparison fallback
            match = sympy_answer.strip() == llm_answer.strip()

        return {
            "attempted": True,
            "verified": True,
            "sympy_answer": sympy_answer,
            "match": match,
            "details": "Answers match" if match else "Answers differ",
        }


sympy_validator = SympyValidator()
